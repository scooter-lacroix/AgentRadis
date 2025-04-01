import json
import time
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import hashlib

from app.tool.base import BaseTool


class WebTool(BaseTool):
    """Tool for interacting with web pages.

    This tool provides functionality for fetching web pages and extracting content.
    It supports different HTTP methods, parsing HTML content, and includes caching
    to avoid redundant requests.
    """

    def __init__(self, cache_ttl: int = 3600):
        """Initialize the WebTool.

        Args:
            cache_ttl: Time-to-live for cached results in seconds (default: 1 hour)
        """
        self._cache = {}  # {url+params_hash: (timestamp, content)}
        self._cache_ttl = cache_ttl

    @property
    def name(self) -> str:
        """The name of the tool."""
        return "web_browser"

    @property
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        return (
            "Fetch web pages and extract content. "
            "Can execute GET and POST requests, process HTML content, "
            "and extract specific information from web pages."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST"],
                    "default": "GET",
                    "description": "HTTP method to use",
                },
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "HTTP headers to include in the request",
                },
                "params": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Query parameters for GET or form data for POST",
                },
                "json_data": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "JSON data to send in the request body (for POST)",
                },
                "timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "Request timeout in seconds",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to extract specific content from HTML",
                },
                "extract_text": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to extract text from HTML (True) or return raw HTML (False)",
                },
                "use_cache": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to use cached results if available",
                },
            },
            "required": ["url"],
        }

    def _get_cache_key(
        self,
        url: str,
        method: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> str:
        """Generate a cache key for a request.

        Args:
            url: The URL to fetch
            method: The HTTP method
            params: Query parameters or form data
            json_data: JSON data for the request body

        Returns:
            A string hash to use as the cache key
        """
        # Create a unique identifier for this request
        key_parts = [url, method]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        if json_data:
            key_parts.append(json.dumps(json_data, sort_keys=True))

        # Create a hash of the key parts
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid.

        Args:
            url: The URL to validate

        Returns:
            True if the URL is valid, False otherwise
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in [
                "http",
                "https",
            ]
        except:
            return False

    async def _fetch_url(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: int = 30,
        use_cache: bool = True,
    ) -> Tuple[int, Dict, str]:
        """Fetch content from a URL.

        Args:
            url: The URL to fetch
            method: HTTP method to use
            headers: HTTP headers to include
            params: Query parameters for GET or form data for POST
            json_data: JSON data for the request body (for POST)
            timeout: Request timeout in seconds
            use_cache: Whether to use cached results

        Returns:
            Tuple of (status_code, response_headers, content)

        Raises:
            ValueError: If the URL is invalid
            aiohttp.ClientError: On network errors
        """
        if not self._is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        cache_key = self._get_cache_key(url, method, params, json_data)

        # Check cache if enabled
        if use_cache and cache_key in self._cache:
            timestamp, (status, resp_headers, content) = self._cache[cache_key]
            if time.time() - timestamp <= self._cache_ttl:
                return status, resp_headers, content

        # Set default headers
        request_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Update with user-provided headers
        if headers:
            request_headers.update(headers)

        async with aiohttp.ClientSession() as session:
            request_kwargs = {
                "headers": request_headers,
                "timeout": aiohttp.ClientTimeout(total=timeout),
            }

            if method == "GET" and params:
                request_kwargs["params"] = params
            elif method == "POST":
                if json_data:
                    request_kwargs["json"] = json_data
                elif params:
                    request_kwargs["data"] = params

            # Make the request
            async with getattr(session, method.lower())(
                url, **request_kwargs
            ) as response:
                content = await response.text()
                status = response.status
                resp_headers = dict(response.headers)

                # Cache the result
                self._cache[cache_key] = (time.time(), (status, resp_headers, content))

                return status, resp_headers, content

    def _parse_html(
        self, html: str, selector: Optional[str] = None, extract_text: bool = True
    ) -> str:
        """Parse HTML content and extract relevant information.

        Args:
            html: The HTML content to parse
            selector: CSS selector to extract specific content
            extract_text: Whether to extract text or return HTML

        Returns:
            Extracted content as string
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()

        # Apply selector if provided
        if selector:
            elements = soup.select(selector)
            if not elements:
                return ""

            # Create a new soup with only the selected elements
            selected_soup = BeautifulSoup("", "html.parser")
            for el in elements:
                selected_soup.append(el)
            soup = selected_soup

        if extract_text:
            # Get all text
            text = soup.get_text(separator="\n")

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            return text
        else:
            return str(soup)

    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the web browsing tool.

        Args:
            url: The URL to fetch
            method: HTTP method to use (default: "GET")
            headers: HTTP headers to include (optional)
            params: Query parameters for GET or form data for POST (optional)
            json_data: JSON data for POST requests (optional)
            timeout: Request timeout in seconds (default: 30)
            selector: CSS selector to extract specific content (optional)
            extract_text: Whether to extract text (default: True)
            use_cache: Whether to use cached results (default: True)

        Returns:
            Dictionary containing:
            - status_code: HTTP status code
            - headers: Response headers
            - content: Extracted content or raw HTML
            - url: The URL that was fetched

        Raises:
            ValueError: If parameters are invalid
            aiohttp.ClientError: On network errors
        """
        validated_params = self.validate_parameters(kwargs)

        url = validated_params["url"]
        method = validated_params.get("method", "GET")
        headers = validated_params.get("headers", {})
        params = validated_params.get("params", {})
        json_data = validated_params.get("json_data", None)
        timeout = validated_params.get("timeout", 30)
        selector = validated_params.get("selector", None)
        extract_text = validated_params.get("extract_text", True)
        use_cache = validated_params.get("use_cache", True)

        try:
            status, resp_headers, html = await self._fetch_url(
                url=url,
                method=method,
                headers=headers,
                params=params,
                json_data=json_data,
                timeout=timeout,
                use_cache=use_cache,
            )

            content = self._parse_html(html, selector, extract_text)

            return {
                "status_code": status,
                "headers": resp_headers,
                "content": content,
                "url": url,
            }
        except ValueError as e:
            # Handle validation errors
            return {"error": "validation_error", "message": str(e), "url": url}
        except aiohttp.ClientError as e:
            # Handle network errors
            return {"error": "network_error", "message": str(e), "url": url}
        except Exception as e:
            # Handle unexpected errors
            return {"error": "unexpected_error", "message": str(e), "url": url}

    async def cleanup(self) -> None:
        """Clean up any resources used by the tool."""
        # Nothing to clean up for this tool
        pass

    async def reset(self) -> None:
        """Reset the tool to its initial state."""
        # Clear the cache
        self._cache = {}
