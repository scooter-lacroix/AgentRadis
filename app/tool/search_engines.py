"""
Search engine implementations for WebSearch tool.
"""
import asyncio
import json
import random
import time
from typing import Any, Dict, List, Optional
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

from app.logger import logger

class SearchEngine:
    """Base class for search engine implementations."""
    
    name = "base"
    
    def __init__(self):
        """Initialize the search engine."""
        self.session = None
    
    async def _ensure_session(self):
        """Ensure we have an active aiohttp session."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": "Mozilla/5.0 AgentRadis/1.0"}
            )
    
    async def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Execute a search query.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            Dictionary with search results
        """
        raise NotImplementedError("Subclasses must implement search method")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

class GoogleWebSearch(SearchEngine):
    """Google search engine implementation."""
    
    name = "google"
    
    async def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Execute a Google search query.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            Dictionary with search results
        """
        await self._ensure_session()
        
        # This is a simplified implementation without actual API usage
        # In a production environment, you'd use Google's Custom Search API
        
        # Use a mobile user agent to get simpler results
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results*2}"
        
        try:
            async with self.session.get(search_url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "engine": self.name,
                        "error": f"Search failed: HTTP {response.status}"
                    }
                
                content = await response.text()
                
                # Save the HTML for debugging
                with open("last_google_search.html", "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Parse results (using more robust selectors)
                results = []
                soup = BeautifulSoup(content, 'html.parser')
                
                # Try multiple selector patterns that Google might use
                search_results = []
                
                # Try different selector patterns from newest to oldest
                selectors = [
                    "div.Gx5Zad", # Modern mobile results
                    "div.xpd", # Another mobile pattern
                    "div.mnr-c", # Older mobile format
                    "div.g", # Classic format
                    "div.tF2Cxc", # Another common pattern
                    "div[jscontroller]", # Very generic fallback
                ]
                
                # Try each selector until we find results
                for selector in selectors:
                    search_results = soup.select(selector)
                    if search_results:
                        break
                
                # Process results
                for result in search_results:
                    # Try multiple patterns for title elements
                    title_elem = None
                    for title_selector in ["h3", ".DKV0Md", ".vvjwJb", ".BNeawe"]:
                        title_elem = result.select_one(title_selector)
                        if title_elem:
                            break
                    
                    # Try multiple patterns for link elements
                    link_elem = None
                    for link_selector in ["a[href^='http']", "a[href^='/url']", "a[ping]", "a[jsname]"]:
                        link_elem = result.select_one(link_selector)
                        if link_elem:
                            break
                    
                    # If no link element found but we have a data-href attribute
                    if not link_elem:
                        for elem in result.select("[data-href]"):
                            if elem.get("data-href", "").startswith("http"):
                                link_elem = elem
                                break
                    
                    # Try multiple patterns for snippet elements
                    snippet = ""
                    for snippet_selector in ["div.VwiC3b", ".s3v9rd", ".lEBKkf", ".BNeawe.s3v9rd", ".BNeawe"]:
                        snippet_elems = result.select(snippet_selector)
                        if snippet_elems:
                            snippet = snippet_elems[0].get_text(strip=True)
                            break
                    
                    # If we have a title and link, create a result
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        link = link_elem.get("href", "") or link_elem.get("data-href", "")
                        
                        if link.startswith("/url?"):
                            # Extract the actual URL from Google's redirect
                            start_idx = link.find("q=")
                            if start_idx != -1:
                                end_idx = link.find("&", start_idx)
                                if end_idx != -1:
                                    link = link[start_idx+2:end_idx]
                                else:
                                    link = link[start_idx+2:]
                                    
                                # URL decode
                                from urllib.parse import unquote
                                link = unquote(link)
                        
                        # Only add if both title and link are non-empty and link is http(s)
                        if title and link and (link.startswith("http://") or link.startswith("https://")):
                            # Skip Google's own links and common irrelevant results
                            if "google.com/search" not in link and "accounts.google.com" not in link:
                                results.append({
                                    "title": title,
                                    "url": link,
                                    "snippet": snippet
                                })
                
                # Strong fallback - try to find any links with titles if no structured results
                if not results:
                    logger.warning(f"No structured results found for query: {query}, trying fallback")
                    
                    # Try to find any links with text
                    for link in soup.select("a[href^='http']"):
                        title = link.get_text(strip=True)
                        url = link.get("href", "")
                        
                        # Only add if the link isn't a Google internal link and has text
                        if (title and url and 
                            "google" not in url.lower() and 
                            len(title) > 5 and
                            not url.startswith("/url") and
                            not title.isdigit()):
                            
                            results.append({
                                "title": title,
                                "url": url,
                                "snippet": ""
                            })
                            
                            # Break once we have enough results
                            if len(results) >= num_results:
                                break
                
                # Deduplicate results by URL
                seen_urls = set()
                unique_results = []
                
                for result in results:
                    url = result.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_results.append(result)
                        
                        if len(unique_results) >= num_results:
                            break
                
                # Log the number of results found
                logger.info(f"Found {len(unique_results)} results for query: {query}")
                
                # Limit to requested number
                results = unique_results[:num_results]
                
                return {
                    "status": "success",
                    "engine": self.name,
                    "results": results
                }
                
        except Exception as e:
            logger.error(f"Google search failed: {str(e)}")
            return {
                "status": "error",
                "engine": self.name,
                "error": f"Search failed: {str(e)}"
            }

class DuckDuckGoSearch(SearchEngine):
    """DuckDuckGo search engine implementation."""
    
    name = "duckduckgo"
    
    async def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Execute a DuckDuckGo search query.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            Dictionary with search results
        """
        await self._ensure_session()
        
        # Use the lite version, which is more reliable and has a simpler structure
        search_url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
        
        try:
            # Use a typical browser user-agent to avoid blocks
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            
            async with self.session.get(search_url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "engine": self.name,
                        "error": f"Search failed: HTTP {response.status}"
                    }
                
                content = await response.text()
                
                # Save the HTML for debugging
                with open("last_duckduckgo_search.html", "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Parse results (using more robust selectors)
                results = []
                soup = BeautifulSoup(content, 'html.parser')
                
                # DDG Lite uses tables for layout
                # Look for the results - each result is in a table row with links
                
                # First pattern: Find all tables and look for result rows
                all_tables = soup.find_all('table')
                for table in all_tables:
                    rows = table.find_all('tr')
                    for i, row in enumerate(rows):
                        links = row.find_all('a')
                        if not links:
                            continue
                            
                        for link in links:
                            href = link.get('href', '')
                            # Skip internal links
                            if not href.startswith('http'):
                                continue
                                
                            title = link.get_text(strip=True)
                            
                            # Skip empty or navigation links
                            if not title or len(title) < 3 or title.isdigit():
                                continue
                                
                            # Try to find snippet in nearby rows
                            snippet = ""
                            if i+1 < len(rows):
                                next_row = rows[i+1]
                                if not next_row.find('a'):  # If next row doesn't have links, it might be a snippet
                                    snippet = next_row.get_text(strip=True)
                                    
                            results.append({
                                "title": title,
                                "url": href,
                                "snippet": snippet
                            })
                
                # Second method: Try finding results by looking for specific patterns
                if not results:
                    result_sections = []
                    for element in soup.find_all(['td', 'div']):
                        # If we see certain patterns that indicate a result section
                        if (element.find('a', href=lambda x: x and x.startswith('http')) and 
                            not element.find('form')):
                            result_sections.append(element)
                            
                    for section in result_sections:
                        links = section.find_all('a', href=lambda x: x and x.startswith('http'))
                        for link in links:
                            href = link.get('href', '')
                            title = link.get_text(strip=True)
                            
                            # Skip empty or navigation links
                            if not title or len(title) < 3 or title.isdigit():
                                continue
                                
                            # Get snippet from nearby text
                            snippet = ""
                            if link.parent and link.parent.get_text(strip=True) != title:
                                full_text = link.parent.get_text(strip=True)
                                # Extract the text after the title as the snippet
                                try:
                                    snippet = full_text[full_text.index(title) + len(title):].strip()
                                except ValueError:
                                    pass
                                    
                            results.append({
                                "title": title,
                                "url": href,
                                "snippet": snippet
                            })
                
                # Fallback: try to find any links if structured results not found
                if not results:
                    logger.warning(f"No structured results found for query: {query}, trying fallback")
                    
                    # Find all links in the document
                    for link in soup.find_all('a', href=lambda x: x and x.startswith('http')):
                        title = link.get_text(strip=True)
                        url = link.get("href", "")
                        
                        # Skip navigation links and other non-result links
                        if (title and url and 
                            "duckduckgo" not in url.lower() and 
                            len(title) > 5 and
                            not title.isdigit()):
                            
                            results.append({
                                "title": title,
                                "url": url,
                                "snippet": ""
                            })
                
                # Deduplicate results by URL
                seen_urls = set()
                unique_results = []
                
                for result in results:
                    url = result.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_results.append(result)
                        
                        if len(unique_results) >= num_results:
                            break
                
                # Log the number of results found
                logger.info(f"Found {len(unique_results)} results for query: {query}")
                
                return {
                    "status": "success",
                    "engine": self.name,
                    "results": unique_results[:num_results]
                }
                
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            return {
                "status": "error",
                "engine": self.name,
                "error": f"Search failed: {str(e)}"
            }

class BingSearch(SearchEngine):
    """Bing search engine implementation."""
    
    name = "bing"
    
    async def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Execute a Bing search query.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            Dictionary with search results
        """
        # Simplified implementation - in a real scenario, we'd use the Bing API
        await self._ensure_session()
        
        search_url = f"https://www.bing.com/search?q={quote_plus(query)}&count={num_results}"
        
        try:
            async with self.session.get(search_url, timeout=10) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "engine": self.name,
                        "error": f"Search failed: HTTP {response.status}"
                    }
                
                content = await response.text()
                
                # Parse results (simplified)
                results = []
                soup = BeautifulSoup(content, 'html.parser')
                
                for result in soup.select(".b_algo"):
                    title_elem = result.select_one("h2")
                    snippet_elem = result.select_one(".b_caption p")
                    
                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True)
                        url = ""
                        
                        if title_elem.a:
                            url = title_elem.a.get("href", "")
                        
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
                        
                        if len(results) >= num_results:
                            break
                
                return {
                    "status": "success",
                    "engine": self.name,
                    "results": results
                }
                
        except Exception as e:
            logger.error(f"Bing search failed: {str(e)}")
            return {
                "status": "error",
                "engine": self.name,
                "error": f"Search failed: {str(e)}"
            }

class BraveSearch(SearchEngine):
    """Brave search engine implementation."""
    
    name = "brave"
    
    async def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Execute a Brave search query.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            Dictionary with search results
        """
        # Simplified implementation - in a real scenario, we'd use the Brave API if available
        await self._ensure_session()
        
        search_url = f"https://search.brave.com/search?q={quote_plus(query)}"
        
        try:
            async with self.session.get(search_url, timeout=10) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "engine": self.name,
                        "error": f"Search failed: HTTP {response.status}"
                    }
                
                content = await response.text()
                
                # Parse results (simplified)
                results = []
                soup = BeautifulSoup(content, 'html.parser')
                
                for result in soup.select(".snippet"):
                    title_elem = result.select_one(".snippet-title")
                    url_elem = result.select_one(".snippet-url")
                    description_elem = result.select_one(".snippet-description")
                    
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        url = ""
                        snippet = ""
                        
                        if url_elem:
                            url = url_elem.get_text(strip=True)
                        elif title_elem.a:
                            url = title_elem.a.get("href", "")
                            
                        if description_elem:
                            snippet = description_elem.get_text(strip=True)
                        
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet
                        })
                        
                        if len(results) >= num_results:
                            break
                
                return {
                    "status": "success",
                    "engine": self.name,
                    "results": results
                }
                
        except Exception as e:
            logger.error(f"Brave search failed: {str(e)}")
            return {
                "status": "error",
                "engine": self.name,
                "error": f"Search failed: {str(e)}"
            } 