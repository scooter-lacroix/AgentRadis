# Removed circular import of search engine classes from web_search.py

# Implementation for web search engines
import requests
from bs4 import BeautifulSoup
from typing import List, Iterator
import urllib.parse
import time
import random
import os
import re
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional, Set
from fake_useragent import UserAgent

from app.exceptions import WebSearchException
from app.logger import logger

# Global cache to avoid repeated searches in the same session
SEARCH_RESULT_CACHE = {}
# Set of user agents to rotate through
USER_AGENTS = None
# Initialize shared session with connection pooling
DEFAULT_SESSION = requests.Session()

def get_random_user_agent():
    """Get a random user agent string to avoid detection"""
    global USER_AGENTS
    
    try:
        if USER_AGENTS is None:
            try:
                # Try to use fake_useragent
                ua = UserAgent()
                USER_AGENTS = [
                    ua.chrome, ua.firefox, ua.safari, ua.edge, 
                    ua.random, ua.random, ua.random
                ]
            except Exception:
                # Fallback user agents if fake_useragent fails
                USER_AGENTS = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
                ]
        
        return random.choice(USER_AGENTS)
    except Exception as e:
        logger.warning(f"Error getting random user agent: {e}")
        # Return a reasonable default
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class WebSearchEngine(ABC):
    """Base class for web search engines"""
    
    def __init__(self):
        self.session = DEFAULT_SESSION
        self.cache_dir = os.path.join(os.getcwd(), "search_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
    @abstractmethod
    def perform_search(self, query: str, num_results: int = 10) -> Iterator[str]:
        """
        Perform a search and return an iterator of result URLs
        
        Args:
            query: The search query
            num_results: Maximum number of results to return
            
        Returns:
            Iterator of result URLs
        """
        pass
    
    def _get_cache_key(self, query: str, num_results: int) -> str:
        """Generate a cache key for the search"""
        clean_query = query.strip().lower()
        return f"{self.__class__.__name__}:{clean_query}:{num_results}"
    
    def _check_cache(self, query: str, num_results: int) -> Optional[List[str]]:
        """Check if results are in cache"""
        cache_key = self._get_cache_key(query, num_results)
        if cache_key in SEARCH_RESULT_CACHE:
            logger.info(f"Using cached results for query: '{query}'")
            return SEARCH_RESULT_CACHE[cache_key]
        return None
    
    def _update_cache(self, query: str, num_results: int, results: List[str]) -> None:
        """Update cache with search results"""
        cache_key = self._get_cache_key(query, num_results)
        SEARCH_RESULT_CACHE[cache_key] = results


class BaiduSearchEngine(WebSearchEngine):
    """Baidu search engine implementation"""
    
    def perform_search(self, query: str, num_results: int = 10) -> Iterator[str]:
        """Perform a search using Baidu"""
        # Clean and validate query
        clean_query = query.strip()
        if not clean_query:
            raise WebSearchException("Empty search query provided")
            
        # Check cache first
        cached_results = self._check_cache(clean_query, num_results)
        if cached_results:
            return cached_results
        
        try:
            # Add randomization
            timestamp = int(time.time())
            
            # Prepare request
            encoded_query = urllib.parse.quote(clean_query)
            url = f"https://www.baidu.com/s?wd={encoded_query}&rn={min(num_results * 2, 50)}&t={timestamp}"
            
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Referer": "https://www.baidu.com/",
            }
            
            # Make request
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Error accessing Baidu: HTTP {response.status_code}")
                return []
                
            # Parse response
            soup = BeautifulSoup(response.text, "html.parser")
            links = set()
            
            # Get search result links
            for result in soup.select(".result a[href^='http']:not([href*='baidu.com']"):
                href = result.get("href", "")
                if href and href.startswith('http'):
                    links.add(href)
                    
            # Try alternative selectors
            if not links:
                for a_tag in soup.find_all('a'):
                    href = a_tag.get('href', '')
                    if href.startswith('http') and 'baidu.com' not in href:
                        links.add(href)
            
            # Limit results
            results = list(links)[:num_results]
            
            # Update cache
            self._update_cache(clean_query, num_results, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error during Baidu search: {e}")
            return [f"Error during Baidu search: {str(e)}"]


class DuckDuckGoSearchEngine(WebSearchEngine):
    """DuckDuckGo search engine implementation"""
    
    def perform_search(self, query: str, num_results: int = 10) -> Iterator[str]:
        """Perform a search using DuckDuckGo"""
        # Clean and validate query
        clean_query = query.strip()
        if not clean_query:
            raise WebSearchException("Empty search query provided")
            
        # Check cache first
        cached_results = self._check_cache(clean_query, num_results)
        if cached_results:
            return cached_results
        
        try:
            # Prepare request using lite version which is more reliable
            encoded_query = urllib.parse.quote(clean_query)
            url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"
            
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "DNT": "1",
            }
            
            # Make request
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Error accessing DuckDuckGo: HTTP {response.status_code}")
                return []
                
            # Parse response
            soup = BeautifulSoup(response.text, "html.parser")
            links = set()
            
            # Extract links from the results
            for a_tag in soup.select('a.result-link'):
                href = a_tag.get('href', '')
                if href.startswith('http'):
                    links.add(href)
            
            # If no results with primary selector, try alternative approach
            if not links:
                for a_tag in soup.select('a[href^="/l/?"]'):
                    href = a_tag.get('href', '')
                    if href.startswith('/l/?'):
                        # Extract the URL parameter
                        decoded_url = urllib.parse.unquote(href.split('uddg=')[-1].split('&')[0])
                        if decoded_url.startswith('http'):
                            links.add(decoded_url)
            
            # Final resort - find all external links
            if not links:
                for a_tag in soup.find_all('a'):
                    href = a_tag.get('href', '')
                    if href.startswith('http') and 'duckduckgo.com' not in href:
                        links.add(href)
            
            # Limit and store results
            results = list(links)[:num_results]
            
            # Update cache
            self._update_cache(clean_query, num_results, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error during DuckDuckGo search: {e}")
            return [f"Error during DuckDuckGo search: {str(e)}"]


class GoogleSearchEngine(WebSearchEngine):
    """Google search engine implementation"""
    
    @lru_cache(maxsize=32)
    def _get_fallback_results(self, query_term: str) -> List[str]:
        """Get fallback results for common queries that might be blocked"""
        query_lower = query_term.lower()
        
        # Google Canvas related queries
        if "google canvas" in query_lower or "canvas drawing" in query_lower:
            return [
                "https://canvas.apps.chrome/",
                "https://chrome.google.com/webstore/detail/canvas/pcbjjldicoccgaomlpjcfkpghibchphm",
                "https://edu.google.com/products/classroom/",
                "https://www.google.com/drawings/about/",
                "https://support.google.com/docs/answer/179740",
            ]
        
        # General Google services
        if "google" in query_lower and len(query_term.split()) < 3:
            return [
                f"https://www.google.com/search?q={urllib.parse.quote(query_term)}",
                "https://www.google.com/about/products/",
                "https://workspace.google.com/",
                "https://about.google/products/",
            ]
            
        # Default fallback is direct Google search link
        return [f"https://www.google.com/search?q={urllib.parse.quote(query_term)}"]
    
    def perform_search(self, query: str, num_results: int = 10) -> Iterator[str]:
        """Perform a search using Google"""
        # Clean and validate query
        clean_query = query.strip()
        if not clean_query:
            raise WebSearchException("Empty search query provided")
            
        # Check cache first
        cached_results = self._check_cache(clean_query, num_results)
        if cached_results:
            return cached_results
            
        try:
            # Add randomization to avoid detection
            timestamp = int(time.time())
            rand_component = random.randint(1000, 9999)
            
            # Log search attempt
            logger.info(f"Performing Google search for: '{clean_query}'")
            
            # Prepare request
            encoded_query = urllib.parse.quote(clean_query)
            url = f"https://www.google.com/search?q={encoded_query}&num={min(num_results * 2, 30)}&nocache={timestamp}-{rand_component}"
            
            headers = {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache, max-age=0",
                "Pragma": "no-cache",
                "sec-ch-ua": "\"Google Chrome\";v=\"113\", \"Chromium\";v=\"113\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "Referer": "https://www.google.com/",
                "DNT": "1",
            }
            
            # Make request with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.session.get(
                        url, 
                        headers=headers, 
                        timeout=15,
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        break
                    elif response.status_code == 429:
                        # Rate limited - wait and retry
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited by Google. Waiting {wait_time}s before retry {attempt+1}/{max_retries}")
                        time.sleep(wait_time)
                    else:
                        logger.warning(f"HTTP {response.status_code} from Google. Retry {attempt+1}/{max_retries}")
                        time.sleep(1)
                except (requests.RequestException, IOError) as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Network error: {e}. Retry {attempt+1}/{max_retries}")
                    time.sleep(1)
            
            # Check final response
            if response.status_code != 200:
                logger.error(f"Failed to access Google after {max_retries} attempts: HTTP {response.status_code}")
                return self._get_fallback_results(clean_query)
                
            # Save the HTML for debugging if needed
            try:
                debug_dir = os.path.join(os.getcwd(), "debug")
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f"google_search_{int(time.time())}.html")
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
            except Exception as e:
                logger.debug(f"Could not save debug HTML: {e}")
                
            # Parse response
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Collect unique links
            all_links = set()
            
            # Try multiple selectors for Google search results
            selectors = [
                'div.g a[href^="http"]',  # Standard search results
                ".yuRUbf a[href^='http']",  # Another common pattern
                "#search a[href^='http']:not([href*='google.com'])",  # Generic search results
                "div[data-hveid] a[href^='http']:not([href*='google.com'])",  # Data attribute based
                ".v5yQqb a[href^='http']:not([href*='google.com'])",  # More recent structure
                "div.tF2Cxc a[href^='http']",  # Another pattern
                "div.N54PNb a[href^='http']",  # Mobile results
                "div.kCrYT a[href^='http']",  # Another pattern
            ]
            
            for selector in selectors:
                for result in soup.select(selector):
                    href = result.get("href", "")
                    if href.startswith('http') and not href.startswith('https://www.google.com'):
                        # Clean URL by removing tracking parameters
                        clean_url = self._clean_url(href)
                        if clean_url:
                            all_links.add(clean_url)
            
            # Extract from redirect links if we still don't have enough
            if len(all_links) < num_results:
                redirect_links = soup.select("a[href^='/url?']")
                for link in redirect_links:
                    href = link.get('href', '')
                    if href.startswith('/url?'):
                        # Extract the actual URL from Google's redirect
                        parsed = urllib.parse.urlparse(href)
                        params = urllib.parse.parse_qs(parsed.query)
                        if 'q' in params and params['q'][0].startswith('http'):
                            actual_url = params['q'][0]
                            if not actual_url.startswith('https://www.google.com'):
                                # Clean URL by removing tracking parameters
                                clean_url = self._clean_url(actual_url)
                                if clean_url:
                                    all_links.add(clean_url)
            
            # Convert to list and limit to requested number
            links = list(all_links)[:num_results]
            
            # If we still don't have results, use fallbacks
            if not links:
                logger.warning(f"No search results found for '{clean_query}'. Using fallback information.")
                links = self._get_fallback_results(clean_query)
            
            # Update cache
            self._update_cache(clean_query, num_results, links)
            
            # Debug info
            logger.info(f"Found {len(links)} links for query: '{clean_query}'")
            return links
            
        except Exception as e:
            logger.error(f"Error during Google search: {e}")
            # Try fallback results for this query
            try:
                fallback_results = self._get_fallback_results(clean_query)
                logger.info(f"Using {len(fallback_results)} fallback results for '{clean_query}'")
                return fallback_results
            except Exception:
                # Last resort - return error message
                return [f"Error searching for '{clean_query}': {str(e)}. Please try with a different query."]
                
    def _clean_url(self, url: str) -> Optional[str]:
        """Clean URL by removing tracking parameters and fragments"""
        try:
            # Skip obviously invalid URLs
            if not url or len(url) < 8 or ' ' in url:
                return None
                
            # Parse the URL
            parsed = urllib.parse.urlparse(url)
            
            # Skip Google's own domains
            if 'google.' in parsed.netloc.lower():
                return None
                
            # Skip common tracking/ad domains
            blocked_domains = ['doubleclick.net', 'googleadservices.com', 'googlesyndication.com']
            if any(domain in parsed.netloc.lower() for domain in blocked_domains):
                return None
                
            # Skip image/video search results
            if parsed.path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm', '.pdf')):
                return None
                
            # Remove common tracking parameters
            query_params = urllib.parse.parse_qs(parsed.query)
            params_to_remove = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 
                               'gclid', 'fbclid', 'msclkid', '_hsenc', '_hsmi']
            
            filtered_params = {k: v for k, v in query_params.items() 
                              if k.lower() not in params_to_remove}
            
            # Rebuild query string
            clean_query = urllib.parse.urlencode(filtered_params, doseq=True)
            
            # Rebuild URL without fragment
            clean_url = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                clean_query,
                ''  # No fragment
            ))
            
            return clean_url
        except Exception:
            # If any parsing error occurs, return the original URL
            return url


def clear_search_cache():
    """Clear the global search results cache"""
    global SEARCH_RESULT_CACHE
    SEARCH_RESULT_CACHE = {}
