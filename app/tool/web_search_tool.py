"""
Web search tool for retrieving information from the internet.
"""
from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import json
from datetime import datetime
from AgentRadis_v2.app.tool.context_manager import GlobalContextManager
from AgentRadis_v2.app.tool.tool_manager import ToolManager
from AgentRadis_v2.app.tool.search_results_formatter import SearchResultsFormatter

logger = logging.getLogger(__name__)

class WebSearchTool(BaseTool):
    """
    Web search tool using search engines for retrieving information.
    """
    
    name = "web_search"
    description = """
    Search for information on the web.
    This tool uses search engines to provide results.
    Useful for finding facts, recent information, and web content.
    """
    
    # Cache to avoid repeated identical searches
    _cache = {}
    _cache_ttl = 300  # 5 minutes
    
    def __init__(self):
        """Initialize the web search tool."""
        # Use langchain's BaseTool initialization
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.context_manager = GlobalContextManager()
    
    async def run(self, user_input: str, engine: str = "google", num_results: int = 5) -> Dict[str, Any]:
        """
        Execute a web search based on user input.

        Args:
            user_input: The input string from the user.
            engine: The search engine to use (default: "google").
            num_results: Number of results to return (default: 5).

        Returns:
            Dictionary with search results or error information.
        """
        query = extract_query(user_input)  # Extract the query from user input
        if not query:
            return {
                "status": "error",
                "error": "No search query provided"
            }

        # Proceed with the search
        response = await self.perform_search(query, engine, num_results)

        # Check if the response contains formatted results
        if response.get("status") == "success":
            return {
                "status": "success",
                "formatted_results": response.get("formatted_results")  # Return only formatted results
            }
        else:
            return response  # Return the error response as is
    
    async def perform_search(self, query: str, engine: str = "google", num_results: int = 5) -> Dict[str, Any]:
        """
        Execute a web search.
        
        Args:
            query: The search query
            engine: The search engine to use (default: "google")
            num_results: Number of results to return (default: 5)
            
        Returns:
            Dictionary with search results or error information
        """
        if not query:
            return {
                "status": "error",
                "error": "No search query provided"
            }
        
        engine = engine.lower() if engine else "google"
        num_results = min(int(num_results) if num_results else 5, 10)
        
        # Retrieve previous context if available
        previous_results = self.context_manager.get_context('previous_results')
        
        # Check cache first
        cache_key = f"{engine}:{query}:{num_results}"
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if (datetime.now().timestamp() - cache_entry["timestamp"]) < self._cache_ttl:
                logger.info(f"Using cached results for query: {query}")
                return {
                    "status": "success",
                    "query": query,
                    "engine": engine,
                    "results": cache_entry["results"],
                    "formatted_results": SearchResultsFormatter.format_results(cache_entry["results"]),
                    "source": "cache"
                }
        
        try:
            logger.info(f"Performing web search for: {query}")
            
            # For now just support Google as the main engine
            if engine == "google" or engine == "all":
                results = self._google_search(query, num_results)
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported search engine: {engine}"
                }
            
            # If we have results, cache them
            if results and len(results) > 0:
                self._cache[cache_key] = {
                    "timestamp": datetime.now().timestamp(),
                    "results": results
                }
                
                # Update context with new results
                self.context_manager.update_context('previous_results', results)
                
                # Format the results using SearchResultsFormatter
                formatted_results = SearchResultsFormatter.format_results({
                    "status": "success",
                    "query": query,
                    "engine": engine,
                    "results": results
                })
                
                # Update global context with new results
                self.context_manager.update_context('last_search', {
                    "status": "success",
                    "query": query,
                    "engine": engine,
                    "results": results,
                    "formatted_results": formatted_results  # Store formatted results
                })
                
                return {
                    "status": "success",
                    "query": query,
                    "engine": engine,
                    "results": results,
                    "formatted_results": formatted_results  # Return formatted results
                }
            else:
                return {
                    "status": "error",
                    "query": query,
                    "engine": engine,
                    "error": "No results found for the query"
                }
            
        except Exception as e:
            logger.error(f"Error during web search: {e}")
            import traceback
            logger.error(f"Search error traceback: {traceback.format_exc()}")
            
            # Update global context with error information
            self.context_manager.update_context('last_search', {
                "status": "error",
                "query": query,
                "engine": engine,
                "error": f"Search failed: {str(e)}"
            })
            
            return {
                "status": "error",
                "query": query,
                "engine": engine,
                "error": f"Search failed: {str(e)}"
            }
    
    def _google_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search Google for results.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            List of search result items
        """
        escaped_query = quote_plus(query)
        url = f"https://www.google.com/search?q={escaped_query}&num={num_results + 5}"  # Request extra results in case some are filtered
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = []
            
            # Extract the main search results
            result_divs = soup.find_all('div', class_='g')
            if not result_divs:  # Try another selector if the first fails
                result_divs = soup.find_all('div', attrs={'data-hveid': True})
            
            for div in result_divs[:num_results]:
                # Extract title and link
                title_element = div.find('h3')
                link_element = div.find('a')
                
                # Skip if we don't have both title and link
                if not title_element or not link_element:
                    continue
                
                title = title_element.get_text()
                url = link_element.get('href')
                
                # Clean up URL if needed
                if url.startswith('/url?'):
                    url = url.split('&sa=')[0].replace('/url?q=', '')
                
                # Extract snippet
                snippet_element = div.find('div', class_='VwiC3b')
                snippet = snippet_element.get_text() if snippet_element else "No description available"
                
                search_results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
                
                if len(search_results) >= num_results:
                    break
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error during Google search: {e}")
            return []
            
    def _arun(self, query: str, engine: str = "google", num_results: int = 5):
        """
        Asynchronous version of the run method.
        LangChain will use this if it's in async context.
        """
        # Simple implementation that calls the sync version
        return self._run(query, engine, num_results)

# Add the tool to the tool manager
tool_manager = ToolManager()
tool_manager.add_tool(WebSearchTool())

class Context:
    def __init__(self):
        self.data = {}

    def update(self, key, value):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key, None)

async def handle_request(user_input: str):
    context = Context()
    
    # Log the incoming request
    logger.info("Received user input: %s", user_input)

    # Check for specific commands or keywords
    if "search" in user_input.lower():
        query = extract_query(user_input)  # Implement this function to extract the query
        response = await tool_manager.execute_tool("web_search", query)
        context.update("last_search", response)

        # Display the formatted results
        if response.get("status") == "success":
            print(response.get("formatted_results"))  # Print or return formatted results
        else:
            print(f"Error: {response.get('error')}")
    else:
        logger.warning("No tools to execute for input: %s", user_input)
        response = {
            "status": "error",
            "message": "No tools available for the given input."
        }

    logger.info("Current context: %s", context.data)

    return response

def some_function():
    context_manager = GlobalContextManager()
    previous_search = context_manager.get_context('last_search')
    if previous_search:
        print("Previous search results:", previous_search)

def extract_query(user_input: str) -> str:
    """
    Extracts the search query from the user input.

    Args:
        user_input (str): The input string from the user.

    Returns:
        str: The extracted query or an empty string if no query is found.
    """
    # Example: If the user input is "search current time", extract "current time"
    if "search" in user_input.lower():
        return user_input.lower().replace("search", "").strip()
    return ""