"""
Simple web search tool using direct HTML scraping without external APIs.
"""
import aiohttp
import asyncio
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus, unquote
from bs4 import BeautifulSoup
from datetime import datetime
import re
import html

from app.tool.search_results_formatter import SearchResultsFormatter
from app.tool.base import BaseTool

logger = logging.getLogger(__name__)

class WebSearch(BaseTool):
    """
    Web search tool using direct HTML scraping without external APIs.
    """

    name = "web_search"
    description = """
    Search for information on the web.
    This tool directly scrapes search engine results pages.
    Useful for finding facts, recent information, and web content.
    """
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up information for"
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
        self.session = None
        self.search_results_formatter = SearchResultsFormatter()
        self.search_results_formatter = SearchResultsFormatter()

    async def _ensure_session(self):
        """Ensure we have an active aiohttp session."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5"
                }
            )

    async def run(self, query: str, engine: str = "google", num_results: int = 5) -> Dict[str, Any]:
        """
        Execute a web search using DuckDuckGo HTML scraping.

        Args:
            query: The search query
            num_results: Number of results to return (default: 5)

        Returns:
            Dictionary with search results or error information
        """
        if not query:
            return {
                "status": "error",
                "error": "No search query provided"
            }

        # Check cache first
        # cache_key = f"{query}:{num_results}"
        # if cache_key in self._cache:
        #     cache_entry = self._cache[cache_key]
        #     if datetime.now().timestamp() - cache_entry["timestamp"] < self._cache_ttl:
        #         logger.info(f"Using cached results for query: {query}")
        #         return {
        #             "status": "success",
        #             "query": query,
        #             "results": cache_entry["results"],
        #             "formatted_results": cache_entry["formatted_results"],
        #             "source": "cache"
        #         }

        await self._ensure_session()

        try:
            logger.info(f"Performing web search for: {query}")

            # Try DuckDuckGo scraping first
            results = await self._scrape_duckduckgo(query, num_results)

            # If DuckDuckGo fails, try a fallback scraper
            if not results:
                logger.warning(f"DuckDuckGo search failed for: {query}, trying alternative source")
                results = await self._scrape_search_alternative(query, num_results)

            if results and len(results) > 0:
                # Deep clean the results to remove problematic characters
                cleaned_results = self._deep_clean_results(results)

                # Filter out ads and low-quality results
                filtered_results = self._filter_results(cleaned_results)

                # Log input to formatter
                logger.debug(f"Formatter input - query: {query}, results: {filtered_results}")

                # Format the results for better readability
                logger.info("WebSearch: calling SearchResultsFormatter.format_results") # Add log here
                logger.info("WebSearch: calling SearchResultsFormatter.format_results")
                formatted_results = SearchResultsFormatter.format_results(filtered_results, query=query)

                # Log output from formatter
                logger.debug(f"Formatter output: {formatted_results}")

                # Cache successful results
                # self._cache[cache_key] = {
                #     "timestamp": datetime.now().timestamp(),
                #     "results": filtered_results,
                #     "formatted_results": formatted_results
                # }

                return {
                    "status": "success",
                    "query": query,
                    "results": filtered_results,
                    "formatted_results": formatted_results
                }
            else:
                # All scrapers failed
                error_msg = f"No results found for query: {query}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "query": query,
                    "error": error_msg
                }

        except Exception as e:
            logger.error(f"Error during web search: {e}")
            import traceback
            logger.error(f"Search error traceback: {traceback.format_exc()}")

            return {
                "status": "error",
                "query": query,
                "error": f"Search failed: {str(e)}"
            }

    def _deep_clean_results(self, results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Deep clean the search results by removing all unwanted characters and formatting.

        Args:
            results: List of search result dictionaries

        Returns:
            List of cleaned search result dictionaries
        """
        cleaned_results = []

        for result in results:
            # Clean title - aggressive removal of special characters and ads
            title = result.get("title", "")

            # Decode HTML entities
            title = html.unescape(title)

            # Remove ad indicators
            title = re.sub(r'Ad\s*\|', '', title, flags=re.IGNORECASE)

            # Remove all special characters and vertical bars
            title = re.sub(r'[│|]+', ' ', title)

            # Remove any text about ads being privacy protected
            title = re.sub(r'Viewing ads is privacy protected by DuckDuckGo.*', '', title, flags=re.IGNORECASE)

            # Clean up multiple spaces
            title = re.sub(r'\s+', ' ', title).strip()

            # Clean URL
            url = result.get("url", "")

            # Handle URL encoding if needed
            if '%' in url:
                try:
                    url = unquote(url)
                except:
                    pass

            # Remove special characters from URL
            url = re.sub(r'[│|]+', '', url)

            # Remove spaces from URL
            url = re.sub(r'\s+', '', url).strip()

            # Ensure proper URL format
            if url and not (url.startswith('http://') or url.startswith('https://')):
                url = 'https://' + url

            # Clean snippet
            snippet = result.get("snippet", "")

            # Decode HTML entities
            snippet = html.unescape(snippet)

            # Remove special characters
            snippet = re.sub(r'[│|]+', ' ', snippet)

            # Clean up multiple spaces
            snippet = re.sub(r'\s+', ' ', snippet).strip()

            # Add cleaned result
            cleaned_results.append({
                "title": title,
                "url": url,
                "snippet": snippet
            })

        return cleaned_results

    def _filter_results(self, results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Filter out ads and low-quality results.

        Args:
            results: List of search result dictionaries

        Returns:
            List of filtered search result dictionaries
        """
        filtered_results = []

        for result in results:
            title = result.get("title", "").lower()
            url = result.get("url", "").lower()
            snippet = result.get("snippet", "").lower()

            # Skip obvious ads
            if "ad" in title[:3] or "sponsored" in title[:15]:
                continue

            # Skip results with empty or very short titles
            if len(title) < 5:
                continue

            # Skip results with empty URLs
            if not url:
                continue

            # Skip results with "more info" or similar in the snippet
            if snippet.endswith("more info") or snippet.endswith("..."):
                continue

            # Add to filtered results
            filtered_results.append(result)

        return filtered_results


    async def _scrape_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        Search by scraping DuckDuckGo results.

        Args:
            query: The search query
            num_results: Number of results to return

        Returns:
            List of search result items
        """
        escaped_query = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={escaped_query}"

        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"DuckDuckGo search failed with status {response.status}")
                    return []

                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                results = []

                # Extract search results
                for result in soup.select('.result'):
                    try:
                        # Skip ads
                        if result.select_one('.result__type') and 'ad' in result.select_one('.result__type').get_text().lower():
                            continue

                        title_elem = result.select_one('.result__title')
                        snippet_elem = result.select_one('.result__snippet')
                        link_elem = result.select_one('.result__a')

                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)

                        # Get URL from link
                        url = ""
                        if link_elem and link_elem.has_attr('href'):
                            href = link_elem['href']
                            # Extract the actual URL from DuckDuckGo's redirect URL
                            if 'uddg=' in href:
                                try:
                                    url = re.search(r'uddg=([^&]+)', href).group(1)
                                    url = unquote(url)
                                except:
                                    url = href
                            else:
                                url = href

                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing DuckDuckGo search result: {e}")

                    if len(results) >= num_results:
                        break

                logger.info(f"Found {len(results)} results from DuckDuckGo")
                return results

        except Exception as e:
            logger.error(f"Error during DuckDuckGo scraping: {e}")
            return []

    async def _scrape_search_alternative(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        Alternative search scraping method - uses a different source as backup.

        Args:
            query: The search query
            num_results: Number of results to return

        Returns:
            List of search result items
        """
        escaped_query = quote_plus(query)
        url = f"https://search.brave.com/search?q={escaped_query}"

        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    logger.warning(f"Brave search failed with status {response.status}")
                    return []

                html_content = await response.text()
                soup = BeautifulSoup(html_content, 'html.parser')
                results = []

                # Extract search results from Brave Search
                for result in soup.select('.snippet'):
                    try:
                        # Skip ads if they have specific markers
                        if result.select_one('.ad-badge'):
                            continue

                        title_elem = result.select_one('.snippet-title')
                        description_elem = result.select_one('.snippet-description')

                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)

                        # Get URL from title's anchor
                        url = ""
                        link = title_elem.find('a')
                        if link and link.has_attr('href'):
                            url = link['href']

                        snippet = description_elem.get_text(strip=True) if description_elem else ""

                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })

                    except Exception as e:
                        logger.warning(f"Error parsing Brave search result: {e}")

                    if len(results) >= num_results:
                        break

                logger.info(f"Found {len(results)} results from Brave Search")
                return results

                formatted_results = SearchResultsFormatter.format_results(results)
            return formatted_results
        except Exception as e:
            logger.error(f"Error during Brave Search scraping: {e}")
            return []

    async def cleanup(self):
        """Clean up resources when tool is no longer needed."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
        self.search_results_formatter = SearchResultsFormatter()

    async def reset(self):
        """Reset the tool state."""
        await self.cleanup()
        self._cache.clear()

    def _google_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        escaped_query = quote_plus(query)
        url = f"https://www.google.com/search?q={escaped_query}&num={num_results + 5}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            search_results = []

            result_divs = soup.find_all('div', class_='g')
            if not result_divs:
                result_divs = soup.find_all('div', attrs={'data-hveid': True})

            for div in result_divs[:num_results]:
                title_element = div.find('h3')
                link_element = div.find('a')

                if not title_element or not link_element:
                    continue

                title = title_element.get_text()
                url = link_element.get('href')

                if url.startswith('/url?'):
                    url = url.split('&sa=')[0].replace('/url?q=', '')

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
            return []  # Return an empty list instead of None
