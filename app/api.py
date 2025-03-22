"""
API server module for AgentRadis.
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any
from aiohttp import web
from datetime import datetime

from app.agent.radis import create_radis_agent
from app.logger import logger

# Global agent instance
agent = None

async def process_prompt(prompt: str) -> Dict[str, Any]:
    """
    Process a prompt with the agent.
    
    Args:
        prompt: The prompt to process
        
    Returns:
        Dictionary containing the response and metadata
    """
    try:
        # Process with agent
        result = await agent.run(prompt)
        
        if isinstance(result, dict):
            response = result.get('response', 'No response generated')
            status = result.get('status', 'success')
        else:
            response = str(result)
            status = 'success'
            
        return {
            'status': status,
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing prompt: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

async def chat_handler(request):
    """Handle chat requests"""
    try:
        data = await request.json()
        prompt = data.get('prompt')
        
        if not prompt:
            return web.json_response({
                'status': 'error',
                'error': 'No prompt provided'
            }, status=400)
            
        result = await process_prompt(prompt)
        return web.json_response(result)
        
    except json.JSONDecodeError:
        return web.json_response({
            'status': 'error',
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in chat handler: {e}")
        return web.json_response({
            'status': 'error',
            'error': str(e)
        }, status=500)

async def health_handler(request):
    """Health check endpoint"""
    return web.json_response({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

def setup_routes(app):
    """Set up application routes"""
    app.router.add_post('/chat', chat_handler)
    app.router.add_get('/health', health_handler)

def create_app(api_base: Optional[str] = None):
    """Create and configure the API application"""
    global agent
    
    # Create the agent
    agent = create_radis_agent(api_base)
    
    # Create the app
    app = web.Application()
    
    # Set up CORS
    app.router.add_options('/{tail:.*}', lambda r: web.Response(status=200))
    
    @web.middleware
    async def cors_middleware(request, handler):
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
        
    app.middlewares.append(cors_middleware)
    
    # Set up routes
    setup_routes(app)
    
    return app

def start_api_server(port: int = 5000, api_base: Optional[str] = None):
    """Start the API server"""
    app = create_app(api_base)
    web.run_app(app, port=port) 