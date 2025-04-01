import aiohttp
import logging
from typing import Dict, List, Optional
from bs4 import BeautifulSoup

from .base import BaseTool
from ..core.exceptions import ToolExecutionError

logger = logging.getLogger(__name__)


class WebSearch(BaseTool):
    """
Searches the web (currently Google) for information based on a query. Use this when asked to find information online that you don't already know."""

    @property
    def name(self) -> str:
        """The name of the tool."""
        return "web_search"

    @property
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        return "Searches the web (currently Google) for information based on a query. Use this when asked to find information online that you don't already know."

    @property
    def parameters(self) -> Dict[str, any]:
        """JSON schema describing the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query to execute"},
                "num_results": {"type": "integer", "description": "Number of results to return", "default": 5, "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
        }

    def __init__(self):
        self.session = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def _ensure_session(self):
        """Ensures an aiohttp session exists."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def _google_search(
        self, query: str, num_results: int
    ) -> List[Dict[str, str]]:
        """
        Performs a Google search and returns parsed results.

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            List of dictionaries containing title and snippet for each result
        """
        results = []
        search_url = f"https://www.google.com/search?q={query}&num={num_results}"

        try:
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    raise ToolExecutionError(
                        f"Search request failed with status {response.status}"
                    )

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                for div in soup.find_all("div", {"class": "g"}):
                    title_elem = div.find("h3")
                    snippet_elem = div.find("div", {"class": "VwiC3b"})

                    if title_elem and snippet_elem:
                        results.append(
                            {
                                "title": title_elem.get_text(),
                                "snippet": snippet_elem.get_text(),
                            }
                        )

                        if len(results) >= num_results:
                            break

                return results[:num_results]

        except aiohttp.ClientError as net_err:
            logger.error(f"Network error during Google search for '{query}': {net_err}", exc_info=True)
            raise ToolExecutionError(f"Network error during search: {str(e)}")
        except Exception as parse_err:
            logger.error(f"Error parsing Google search results for '{query}': {parse_err}", exc_info=True)
            raise ToolExecutionError(f"Error parsing search results: {str(e)}")

    async def run(
        self, query: str, engine: str = "google", num_results: int = 5
    ) -> List[Dict[str, str]]:
        """
        Executes a web search using the specified search engine.

        Args:
            query: The search query string
            engine: Search engine to use (currently only "google" is supported)
            num_results: Maximum number of results to return

        Returns:
            List of search results as dictionaries

        Raises:
            ToolExecutionError: If the search operation fails
        """
        await self._ensure_session()

        if not query:
            raise ToolExecutionError("Search query cannot be empty")

        if engine.lower() != "google":
            raise ToolExecutionError(f"Unsupported search engine: {engine}")

        try:
            return await self._google_search(query, num_results)
        except Exception as e:
            raise ToolExecutionError(f"Search operation failed: {str(e)}")

    async def cleanup(self):
        """Closes the aiohttp session if it exists."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def reset(self):
        """Reset tool state by cleaning up the session."""
        await self.cleanup()
