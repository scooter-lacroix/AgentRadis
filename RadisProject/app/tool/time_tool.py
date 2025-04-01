"""Time tool for accurate time measurement using NTP."""

import asyncio
import socket
import time
import datetime
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

from app.tool.base import BaseTool

# Import ntplib with error handling in case it's not available
try:
    import ntplib
    NTPLIB_AVAILABLE = True
except ImportError:
    NTPLIB_AVAILABLE = False

import logging
logger = logging.getLogger(__name__)

class TimeTool(BaseTool):
    """Tool for getting accurate time from NTP servers and web sources.
    
    This tool provides functionality for:
    1. Getting accurate time from NTP servers
    2. Comparing NTP time with web-based time sources
    3. Calibrating time between different sources
    """
    
    DEFAULT_NTP_SERVERS = [
        "pool.ntp.org",
        "time.google.com",
        "time.windows.com",
        "time.apple.com",
        "time.cloudflare.com"
    ]
    
    WEB_TIME_SOURCES = [
        {"url": "https://www.time.gov/", "selector": "div#time_display"},
        {"url": "https://www.timeanddate.com/worldclock/", "selector": "span#ct"},
        {"url": "https://time.is/", "selector": "#clock"},
    ]
    
    def __init__(self):
        """Initialize the time tool."""
        self._last_ntp_time = None
        self._last_web_time = None
        self._time_offset = 0  # Offset between system time and NTP time
        self._web_session = None
        self._precision = None  # Calculated precision/error margin
    
    @property
    def name(self) -> str:
        """The name of the tool."""
        return "time"
    
    @property
    def description(self) -> str:
        """A human-readable description of what the tool does."""
        # Simplified description focused on the primary use case for the LLM
        return "Gets the current time, potentially corrected using NTP for accuracy. Use this for any request asking for the current time."

    
    @property
    def parameters(self) -> Dict[str, Any]:
        """JSON schema describing the tool's parameters."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["time", "date", "day"],
                    "description": "The type of time query to perform"
                }
            },
            "required": ["action"]
        }
        
    def as_function(self) -> Dict[str, Any]:
        """Return the function schema for the tool."""
        return {
            "name": self.name,
            "description": "Get the current time, date, or day information",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["time", "date", "day"],
                        "description": "The type of time query to perform"
                    }
                },
                "required": ["action"]
            }
        }
    
    async def _get_ntp_time(self, server: str = "pool.ntp.org", timeout: int = 5) -> Dict[str, Any]:
        """Get time from an NTP server.
        
        Args:
            server: NTP server to query
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with time information and status

        """
        if not NTPLIB_AVAILABLE:
            return {
                "status": "error",
                "error": "ntplib is not available. Install with 'pip install ntplib'."
            }
        logger.debug(f"Attempting NTP query to server: {server} with timeout: {timeout}")

        try:
            # Use loop.run_in_executor for the blocking NTP client
            loop = asyncio.get_event_loop()
            client = ntplib.NTPClient()
            
            # Run the blocking NTP request in a thread pool
            response = await loop.run_in_executor(
                None, lambda: client.request(server, timeout=timeout)
            )
            logger.debug(f"NTP response received from {server}: Offset={response.offset}, Delay={response.delay}")

            # Calculate the offset between system time and NTP time
            system_time = time.time()
            ntp_time = response.tx_time
            offset = ntp_time - system_time
            
            # Save the offset if needed
            self._time_offset = offset
            self._last_ntp_time = ntp_time
            
            # Format times as ISO 8601 strings
            ntp_datetime = datetime.datetime.fromtimestamp(ntp_time).isoformat()
            system_datetime = datetime.datetime.fromtimestamp(system_time).isoformat()
            
            return {
                "status": "success",
                "ntp_time": ntp_datetime,
                "system_time": system_datetime,
                "offset_seconds": offset,
                "delay_ms": response.delay * 1000,  # Convert to milliseconds
                "server": server,
                "stratum": response.stratum,
                "precision": 2 ** response.precision  # Convert from log2 to seconds
            }
        except socket.gaierror:
            logger.error(f"NTP server {server} not found (gaierror).")
            return {
                "status": "error",
                "error": f"NTP server {server} not found.",
                "server": server
            }
        except ntplib.NTPException as e:
            logger.error(f"NTPException querying {server}: {e}", exc_info=True)
            return {
                "status": "error",
                "error": f"NTP error: {str(e)}",
                "server": server
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "server": server
            }
    
    async def _get_web_time(self, timeout: int = 10) -> Dict[str, Any]:
        """Get time from web-based time sources.
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with time information from web sources
        """
        if not self._web_session:
            self._web_session = aiohttp.ClientSession(
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            )
        
        results = []
        for source in self.WEB_TIME_SOURCES:
            try:
                # Request the page
                before_request = time.time()
                async with self._web_session.get(source["url"], timeout=timeout) as response:
                    if response.status != 200:
                        results.append({
                            "source": source["url"],
                            "status": "error",
                            "error": f"HTTP error {response.status}"
                        })
                        continue
                    
                    html = await response.text()
                    after_request = time.time()
                    request_time = (before_request + after_request) / 2  # Use midpoint
                    
                    # Parse HTML and extract time
                    soup = BeautifulSoup(html, 'html.parser')
                    time_element = soup.select_one(source["selector"])
                    
                    if not time_element:
                        results.append({
                            "source": source["url"],
                            "status": "error",
                            "error": f"Time element not found with selector: {source['selector']}"
                        })
                        continue
                    
                    # Extract and clean the time text
                    time_text = time_element.get_text().strip()
                    
                    results.append({
                        "source": source["url"],
                        "status": "success",
                        "time_text": time_text,
                        "timestamp": request_time,
                        "request_duration_ms": (after_request - before_request) * 1000
                    })
                    
            except aiohttp.ClientError as e:
                results.append({
                    "source": source["url"],
                    "status": "error",
                    "error": f"Connection error: {str(e)}"
                })
            except Exception as e:
                results.append({
                    "source": source["url"],
                    "status": "error",
                    "error": f"Unexpected error: {str(e)}"
                })
        
        # Calculate aggregated results
        successful_sources = [r for r in results if r["status"] == "success"]
        if successful_sources:
            self._last_web_time = time.time()  # Use current time as reference
        
        return {
            "status": "success" if successful_sources else "error",
            "sources_queried": len(self.WEB_TIME_SOURCES),
            "sources_succeeded": len(successful_sources),
            "source_results": results,
            "system_time": datetime.datetime.now().isoformat()
        }
    
    async def _calibrate_time(self, use_multiple_sources: bool = True, timeout: int = 10) -> Dict[str, Any]:
        """Calibrate time using both NTP and web sources.
        
        Args:
            use_multiple_sources: Whether to use multiple NTP servers for better accuracy
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with calibration information
        """
        ntp_results = []
        
        # Get time from multiple NTP servers if requested
        if use_multiple_sources:
            for server in self.DEFAULT_NTP_SERVERS:
                result = await self._get_ntp_time(server=server, timeout=timeout)
                if result["status"] == "success":
                    ntp_results.append(result)
                if len(ntp_results) >= 3:  # Stop after getting 3 successful results
                    break
        else:
            # Just use the default server
            result = await self._get_ntp_time(timeout=timeout)
            if result["status"] == "success":
                ntp_results.append(result)
        
        # Get web time
        web_result = await self._get_web_time(timeout=timeout)
        
        # Calculate average NTP offset if we have results
        avg_offset = 0
        if ntp_results:
            offsets = [r["offset_seconds"] for r in ntp_results]
            avg_offset = sum(offsets) / len(offsets)
            
            # Calculate precision (standard deviation of offsets)
            if len(offsets) > 1:
                variance = sum((x - avg_offset) ** 2 for x in offsets) / len(offsets)
                self._precision = variance ** 0.5  # standard deviation
            else:
                self._precision = ntp_results[0].get("precision", 0.1)  # default to 100ms if not available
            
            # Save the offset
            self._time_offset = avg_offset
        
        # Determine if system clock is accurate
        accurate = False
        if ntp_results:
            # Consider the clock accurate if the offset is less than 1 second
            accurate = abs(avg_offset) < 1.0
        
        # Get current system and NTP-corrected time
        system_time = time.time()
        corrected_time = system_time + (self._time_offset or 0)
        
        return {
            "status": "success" if ntp_results else "error",
            "ntp_sources_queried": len(self.DEFAULT_NTP_SERVERS if use_multiple_sources else 1),
            "ntp_sources_succeeded": len(ntp_results),
            "ntp_results": ntp_results,
            "web_result": web_result,
            "system_time": datetime.datetime.fromtimestamp(system_time).isoformat(),
            "ntp_corrected_time": datetime.datetime.fromtimestamp(corrected_time).isoformat(),
            "avg_offset_seconds": avg_offset,
            "precision_seconds": self._precision,
            "system_clock_accurate": accurate
        }
    
    async def run(self, **kwargs) -> str:
        """Run the tool with the specified parameters.
        
        Args:
            action: The type of time query to perform (time, date, or day)
            format: Optional format for the time/date output (default: standard)
            
        Returns:
            A string containing the requested time information
        """
        try:
            # Validate parameters against schema
            params = self.validate_parameters(kwargs)
            logger.debug(f"TimeTool run called with params: {params}")
            
            # Extract validated parameters with defaults
            action = params.get("action", "time")
            
            # Get current time using system clock
            current_time = datetime.datetime.now()
            
            if action == "time":
                return f"Current time is {current_time.strftime('%H:%M:%S')}"
            elif action == "date":
                return f"Current date is {current_time.strftime('%Y-%m-%d')}"
            elif action == "day":
                return f"Today is {current_time.strftime('%A')}"
            else:
                return f"Invalid action: {action}"
                
        except Exception as e:
            logger.error(f"Error during TimeTool action '{params.get('action', 'unknown')}': {e}", exc_info=True)
            return f"Error executing time tool: {str(e)}"
            
    async def cleanup(self) -> None:
        """Clean up resources used by the tool."""
        if self._web_session and not self._web_session.closed:
            await self._web_session.close()
            self._web_session = None
            
    async def reset(self) -> None:
        """Reset the internal state of the tool to initial values."""
        # Clean up any existing web session
        if self._web_session and not self._web_session.closed:
            await self._web_session.close()
            
        # Reset all internal state variables to initial values
        self._last_ntp_time = None
        self._last_web_time = None
        self._time_offset = 0
        self._web_session = None
        self._precision = None
