"""
Web search tools for AgentRadis agent.
"""
import asyncio
import json
import os
import random
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import aiohttp
import re
from urllib.parse import quote_plus

from app.config import config
from app.exceptions import WebSearchException, InvalidToolArgumentException
from app.logger import logger
from app.tool.base import BaseTool
from app.tool.search_engines import (
    GoogleWebSearch, DuckDuckGoSearch, BingSearch, BraveSearch
)

class WebSearch(BaseTool):
    """
    Web search tool using multiple search engines for enhanced results.
    """
    
    name = "web_search"
    description = """
    Search for information on the web.
    This tool leverages multiple search engines to provide comprehensive results.
    Useful for finding facts, recent information, and web content.
    """
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up information for"
            },
            "engine": {
                "type": "string",
                "enum": ["google", "duckduckgo", "bing", "brave", "all"],
                "description": "The search engine to use (defaults to google if not specified)"
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 5, max: 10)"
            }
        },
        "required": ["query"]
    }
    
    # Cache to avoid repeated identical searches
    _cache = {}
    _cache_ttl = 300  # 5 minutes
    
    def __init__(self, **kwargs):
        """Initialize the web search tool."""
        super().__init__(**kwargs)
        
        # Configure search engines
        self.search_engines = {
            "google": GoogleWebSearch(),
            "duckduckgo": DuckDuckGoSearch(),
            "bing": BingSearch(),
            "brave": BraveSearch()
        }
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute a web search.
        
        Args:
            query: The search query
            engine: The search engine to use (default: "google")
            num_results: Number of results to return (default: 5)
            
        Returns:
            Dictionary with search results
        """
        query = kwargs.get("query", "")
        engine = kwargs.get("engine", "google").lower()
        num_results = min(int(kwargs.get("num_results", 5)), 10)
        
        if not query:
            return {
                "status": "error",
                "error": "No search query provided"
            }
        
        # Check cache first
        cache_key = f"{engine}:{query}:{num_results}"
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if time.time() - cache_entry["timestamp"] < self._cache_ttl:
                logger.info(f"Using cached results for query: {query}")
                return {
                    "status": "success",
                    "query": query,
                    "engine": engine,
                    "results": cache_entry["results"],
                    "source": "cache"
                }
        
        try:
            logger.info(f"Performing web search for: {query}")
            
            if engine == "all":
                # Use multiple engines and combine results
                all_results = []
                engines_to_try = ["google", "duckduckgo", "bing"]
                
                for search_engine in engines_to_try:
                    try:
                        results = await self._search_with_engine(search_engine, query, num_results)
                        if results.get("status") == "success":
                            all_results.extend(results.get("results", []))
                    except Exception as e:
                        logger.warning(f"Error with {search_engine} search: {e}")
                
                # Deduplicate results by URL
                seen_urls = set()
                unique_results = []
                
                for result in all_results:
                    url = result.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_results.append(result)
                
                # Take top results
                unique_results = unique_results[:num_results]
                
                response = {
                    "status": "success",
                    "query": query,
                    "engine": "multiple",
                    "results": unique_results
                }
            else:
                # Use a single engine
                response = await self._search_with_engine(engine, query, num_results)
            
            # Cache the results
            if response.get("status") == "success":
                self._cache[cache_key] = {
                    "timestamp": time.time(),
                    "results": response.get("results", [])
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error during web search: {e}")
            return {
                "status": "error",
                "error": f"Failed to perform search: {str(e)}",
                "query": query
            }
    
    async def _search_with_engine(self, engine: str, query: str, num_results: int) -> Dict[str, Any]:
        """
        Search with a specific engine.
        
        Args:
            engine: The search engine to use
            query: The search query
            num_results: Number of results to return
            
        Returns:
            Dictionary with search results
        """
        # Use the default if engine is not supported
        if engine not in self.search_engines:
            logger.warning(f"Unsupported search engine: {engine}, falling back to Google")
            engine = "google"
        
        try:
            search_engine = self.search_engines[engine]
            results = await search_engine.search(query, num_results=num_results)
            
            # Debug the raw results to understand issues
            logger.info(f"Raw search results: {json.dumps(results)}")
            
            # Clean and format results
            clean_results = self._clean_results(results)
            
            # Debug the cleaned results
            logger.info(f"Cleaned results count: {len(clean_results)}")
            
            return {
                "status": "success",
                "query": query,
                "engine": engine,
                "results": clean_results
            }
        except Exception as e:
            logger.error(f"Error with {engine} search: {e}")
            import traceback
            logger.error(f"Search error traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "error": f"Search engine error: {str(e)}",
                "engine": engine,
                "query": query
            }
    
    def _clean_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Clean and format search results.
        
        Args:
            results: Raw search results from engine
            
        Returns:
            List of cleaned search result items
        """
        # If results is just a dictionary and not a list of results
        if isinstance(results, dict):
            # Get the results array from the dictionary
            result_items = results.get("results", [])
            # If there are no results, return an empty list
            if not result_items:
                return []
            return result_items
        
        # If results is already a list, return it directly
        if isinstance(results, list):
            return results
            
        # If we got here, we don't know how to handle the results
        logger.warning(f"Unknown search results format: {type(results)}")
        return []
    
    def _format_search_result(self, item: Dict[str, Any]) -> str:
        """
        Format a single search result as a string.
        
        Args:
            item: Search result item
            
        Returns:
            Formatted string
        """
        title = item.get("title", "No title")
        url = item.get("url", "")
        snippet = item.get("snippet", "")
        
        result = f"Title: {title}\n"
        if url:
            result += f"URL: {url}\n"
        if snippet:
            result += f"Snippet: {snippet}\n"
        
        return result
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Format all search results as a string.
        
        Args:
            results: List of search result items
            
        Returns:
            Formatted string with all results
        """
        if not results:
            return "No search results found."
        
        formatted = ""
        for i, item in enumerate(results, 1):
            formatted += f"\n--- Result {i} ---\n"
            formatted += self._format_search_result(item)
        
        return formatted
        
    async def cleanup(self):
        """Clean up resources."""
        # Close any open sessions
        if hasattr(self, 'session') and self.session:
            try:
                self.session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
        
        # Close any aiohttp sessions
        for engine_name, engine in self.search_engines.items():
            if hasattr(engine, 'session') and engine.session:
                try:
                    await engine.session.close()
                except Exception as e:
                    logger.error(f"Error closing {engine_name} session: {e}")
        
        # Clear the cache
        self._cache.clear()

    async def reset(self):
        """Reset the tool's state."""
        if hasattr(self, 'session') and self.session:
            self.session.close()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def to_param(self) -> Dict:
        """Convert tool to OpenAI function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
