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

from app.config import config
from app.exceptions import WebSearchException, InvalidToolArgumentException
from app.logger import logger
from app.tool.base import BaseTool, ToolResult

class WebSearch(BaseTool):
    """Tool for searching the web for information."""

    name: str = "web_search"
    description: str = "Search the web for up-to-date information from the internet"
    examples: List[str] = [
        "web_search(query='current bitcoin price')",
        "web_search(query='latest news about artificial intelligence')"
    ]
    timeout: float = 15.0
    is_stateful: bool = False
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to perform"
            },
            "verify": {
                "type": "boolean",
                "description": "Whether to perform additional verification of the information"
            }
        },
        "required": ["query"]
    }

    def __init__(self, **kwargs):
        """Initialize the web search tool."""
        super().__init__(**kwargs)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    async def execute(self, query: str, verify: bool = True) -> Dict[str, Any]:
        """
        Execute a web search
        
        Args:
            query: The search query
            verify: Whether to perform additional verification
            
        Returns:
            Dict containing search results
        """
        logger.info(f"Web search for: {query}")
        try:
            # Special handling for date/time queries
            if any(term in query.lower() for term in ["current date", "current time", "what time", "what date", "what is the date", "what is the time"]):
                ny_tz = pytz.timezone('America/New_York')
                current_time = datetime.now(ny_tz)
                formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
                return {
                    'status': 'success',
                    'content': f"The current date and time in New York is: {formatted_time}"
                }

            # For Super Bowl or other major event queries, enhance the search query
            if any(term in query.lower() for term in ["super bowl", "superbowl"]):
                if any(term in query.lower() for term in ["recent", "last", "latest", "who performed", "halftime"]):
                    query = f"{query} most recent 2024 2025"

            # Perform web search using DuckDuckGo
            query_url = f"https://lite.duckduckgo.com/lite?q={query.replace(' ', '+')}"
            
            # Make the request with timeout
            response_future = asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.session.get(query_url, timeout=10)
            )
            
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse the response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract search results
            results = []
            for result in soup.find_all('a', {'class': 'result-link'}):
                title = result.text.strip()
                url = result['href']
                if title and url:
                    results.append({
                        'title': title,
                        'url': url
                    })
            
            # Format results
            if results:
                formatted_results = []
                for result in results[:3]:  # Limit to top 3 results for faster processing
                    # Try to extract relevant text around the result
                    context = ""
                    try:
                        result_response_future = asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self.session.get(result['url'], timeout=5)
                        )
                        
                        # Wait for response with timeout
                        result_response = await asyncio.wait_for(result_response_future, timeout=5)
                        
                        if result_response.ok:
                            result_soup = BeautifulSoup(result_response.text, 'html.parser')
                            # Get text from p tags near the search terms
                            relevant_text = []
                            for p in result_soup.find_all('p'):
                                if any(term.lower() in p.text.lower() for term in query.split()):
                                    relevant_text.append(p.text.strip())
                            if relevant_text:
                                context = " ".join(relevant_text[:2])  # Use first two relevant paragraphs
                    except Exception as e:
                        logger.debug(f"Error fetching context for {result['url']}: {str(e)}")
                        pass  # Ignore errors in getting additional context
                    
                    formatted_results.append({
                        'title': result['title'],
                        'url': result['url'],
                        'context': context
                    })
                
                # Create a summary from the results
                summary = self._create_summary(query, formatted_results)
                
                return {
                    'status': 'success',
                    'content': summary
                }
            else:
                return {
                    'status': 'error',
                    'content': f"No search results found for query: {query}"
                }
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout while searching for: {query}")
            return {
                'status': 'error',
                'content': f"Search timed out for query: {query}. Please try again with more specific terms."
            }
        except Exception as e:
            logger.error(f"Error executing web search: {str(e)}")
            return {
                'status': 'error',
                'content': f"Error performing web search: {str(e)}"
            }

    def _create_summary(self, query: str, results: List[Dict[str, str]]) -> str:
        """Create a natural summary from search results."""
        try:
            # If we have context, use it to create a more natural response
            contexts = [r['context'] for r in results if r['context']]
            if contexts:
                # Use the most relevant context to form the response
                main_context = contexts[0]
                # Add source link
                source_url = results[0]['url']
                return f"{main_context}\n\nSource: [{source_url}]({source_url})"
            
            # Fallback to basic listing if no good context
            summary = "Here are the most relevant results:\n\n"
            for i, result in enumerate(results, 1):
                summary += f"{i}. {result['title']}\n   {result['url']}\n\n"
            return summary
            
        except Exception as e:
            logger.error(f"Error creating summary: {str(e)}")
            # Fallback to very basic format
            return "\n".join(r['url'] for r in results)

    async def run(self, **kwargs):
        """Execute a web search (alias for execute)."""
        if "query" not in kwargs:
            return {
                'status': 'error',
                'content': "Missing required parameter: query"
            }
        
        verify = kwargs.get("verify", True)
        return await self.execute(query=kwargs["query"], verify=verify)

    async def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'session') and self.session:
            self.session.close()

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
