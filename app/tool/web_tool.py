"""
Web tools for AgentRadis agent.
"""
import asyncio
import json
import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse

from app.logger import logger
from app.tool.base import BaseTool

class WebTool(BaseTool):
    """
    Web tool for fetching content, searching, and extracting data from websites.
    """
    
    name = "web_tool"
    description = """
    Perform operations on the web such as fetching pages, searching, and extracting content.
    This tool is useful for retrieving information from specific URLs, performing searches,
    and extracting structured data from web pages using CSS selectors.
    """
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["fetch", "search", "extract"],
                "description": "The action to perform: fetch a URL, search the web, or extract content"
            },
            "url": {
                "type": "string",
                "description": "The URL to fetch or extract from (required for fetch and extract actions)"
            },
            "query": {
                "type": "string",
                "description": "The search query (required for search action)"
            },
            "selector": {
                "type": "string",
                "description": "CSS selector for extracting content (required for extract action)"
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds (default: 10)"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self, **kwargs):
        """Initialize the web tool."""
        super().__init__(**kwargs)
        self.session = None
    
    async def _ensure_session(self):
        """Ensure we have an active aiohttp session."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": "Mozilla/5.0 AgentRadis/1.0"}
            )
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute a web operation.
        
        Args:
            action: The action to perform (fetch, search, extract)
            url: URL to fetch or extract from
            query: Search query
            selector: CSS selector for extraction
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with operation results
        """
        action = kwargs.get("action", "")
        
        if not action:
            return {
                "status": "error",
                "error": "No action specified. Must be one of: fetch, search, extract"
            }
        
        await self._ensure_session()
        
        try:
            if action == "fetch":
                return await self._fetch_url(kwargs)
            elif action == "search":
                return await self._search_web(kwargs)
            elif action == "extract":
                return await self._extract_content(kwargs)
            else:
                return {
                    "status": "error",
                    "error": f"Invalid action: {action}. Must be one of: fetch, search, extract"
                }
        except Exception as e:
            logger.error(f"WebTool error: {str(e)}")
            return {
                "status": "error",
                "error": f"Web operation failed: {str(e)}"
            }
    
    async def _fetch_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch content from a URL."""
        url = params.get("url")
        timeout = params.get("timeout", 10)
        
        if not url:
            return {
                "status": "error",
                "error": "URL is required for fetch action"
            }
        
        try:
            async with self.session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"Failed to fetch URL: HTTP {response.status}"
                    }
                
                content = await response.text()
                return {
                    "status": "success",
                    "url": url,
                    "http_status": response.status,
                    "content_type": response.headers.get("Content-Type", ""),
                    "content_length": len(content),
                    "title": self._extract_title(content),
                    "content_sample": content[:1000] + ("..." if len(content) > 1000 else "")
                }
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "error": f"Request timed out after {timeout} seconds"
            }
    
    async def _search_web(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a basic web search."""
        query = params.get("query")
        
        if not query:
            return {
                "status": "error",
                "error": "Query is required for search action"
            }
        
        # Use a simple search engine API for demonstration
        # In a real implementation, this would use a proper search API
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        
        try:
            async with self.session.get(search_url, timeout=10) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"Search failed: HTTP {response.status}"
                    }
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                results = []
                
                # Extract search results
                for result in soup.select('.result'):
                    title_elem = result.select_one('.result__title')
                    snippet_elem = result.select_one('.result__snippet')
                    url_elem = result.select_one('.result__url')
                    
                    if title_elem and snippet_elem:
                        results.append({
                            "title": title_elem.get_text(strip=True),
                            "snippet": snippet_elem.get_text(strip=True),
                            "url": url_elem.get_text(strip=True) if url_elem else ""
                        })
                    
                    if len(results) >= 5:
                        break
                
                return {
                    "status": "success",
                    "query": query,
                    "results": results
                }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Search failed: {str(e)}"
            }
    
    async def _extract_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content from a web page using a CSS selector."""
        url = params.get("url")
        selector = params.get("selector")
        timeout = params.get("timeout", 10)
        
        if not url:
            return {
                "status": "error",
                "error": "URL is required for extract action"
            }
        
        if not selector:
            return {
                "status": "error",
                "error": "CSS selector is required for extract action"
            }
        
        try:
            async with self.session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "error": f"Failed to fetch URL: HTTP {response.status}"
                    }
                
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                elements = soup.select(selector)
                
                extracted = []
                for element in elements:
                    extracted.append({
                        "text": element.get_text(strip=True),
                        "html": str(element),
                        "attributes": {k: v for k, v in element.attrs.items()}
                    })
                
                return {
                    "status": "success",
                    "url": url,
                    "selector": selector,
                    "matches": len(extracted),
                    "extracted": extracted
                }
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "error": f"Request timed out after {timeout} seconds"
            }
    
    def _extract_title(self, content: str) -> str:
        """Extract the title from HTML content."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            title = soup.title.string if soup.title else ""
            return title.strip()
        except:
            return ""
    
    async def cleanup(self):
        """Clean up resources when tool is no longer needed."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            
    async def reset(self):
        """Reset the tool state."""
        await self.cleanup() 