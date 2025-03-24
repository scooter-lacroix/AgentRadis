"""
Client module for handling LLM API connections and requests.
"""

import httpx
import json
from typing import Dict, Any, Optional

from app.logger import logger
from app import config

async def test_llm_connection(api_base: Optional[str] = None) -> Dict[str, Any]:
    """
    Test the connection to the LLM API.
    
    Args:
        api_base: Optional API base URL override
        
    Returns:
        Dict containing success status and error message if any
    """
    try:
        # Use provided API base or get from config
        api_base = api_base or config.get_llm_config().api_base
        
        # Make a test request to the models endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_base}/models")
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "models": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status code {response.status_code}: {response.text}"
                }
                
    except httpx.ConnectError:
        return {
            "success": False,
            "error": f"Could not connect to LLM API at {api_base}"
        }
    except Exception as e:
        logger.error(f"Error testing LLM connection: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def make_llm_request(endpoint: str, data: Dict[str, Any], api_base: Optional[str] = None) -> Dict[str, Any]:
    """
    Make a request to the LLM API.
    
    Args:
        endpoint: API endpoint (e.g. '/chat/completions')
        data: Request data
        api_base: Optional API base URL override
        
    Returns:
        API response as dictionary
    """
    try:
        # Use provided API base or get from config
        api_base = api_base or config.get_llm_config().api_base
        
        # Make the request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}{endpoint}",
                json=data,
                timeout=60.0  # Increased timeout to 60 seconds
            )
            
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        logger.error(f"Error making LLM request: {e}")
        raise 