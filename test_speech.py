#!/usr/bin/env python3
"""
Test script for the RealtimeSTT and RealtimeTTS integration
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import Radis
from app.logger import logger

async def test_speech_tool():
    """Test the speech tool functionality"""
    # Initialize Radis
    radis = Radis()
    
    # Get available tools
    tools = await radis.get_available_tools()
    print("Available tools:")
    for tool in tools:
        installed = tool.get("installed", False)
        print(f"  - {tool.get('name')} ({'Installed' if installed else 'Not installed'})")
        
    # Check if speech tool is available
    speech_info = await radis.get_tool_info("speech")
    
    # Install RealtimeSTT and RealtimeTTS if needed
    if speech_info.get("status") == "error" or not speech_info.get("installed", False):
        print("\nInstalling speech capabilities...")
        result = await radis.install_mcp_tool("realtimestt")
        print(f"  - RealtimeSTT: {result.get('message')}")
        
        result = await radis.install_mcp_tool("realtimetts")
        print(f"  - RealtimeTTS: {result.get('message')}")
        
    # Test text-to-speech
    print("\nTesting text-to-speech...")
    result = await radis.execute_tool_with_context("speech", {
        "action": "speak",
        "text": "Hello, I am Radis, your AI assistant. I can now speak using RealtimeTTS!",
        "options": {
            "voice": "default",
            "speed": 1.0
        }
    })
    
    print(f"  Result: {result.get('status')}")
    if result.get("status") == "error":
        print(f"  Error: {result.get('error')}")
    
    # Test speech-to-text
    print("\nTesting speech-to-text...")
    print("  Please speak after the prompt...")
    result = await radis.execute_tool_with_context("speech", {
        "action": "listen",
        "options": {
            "timeout": 5.0
        }
    })
    
    print(f"  Result: {result.get('status')}")
    if result.get("status") == "success":
        print(f"  Recognized text: {result.get('text')}")
    else:
        print(f"  Error: {result.get('error')}")
    
    # Test multi-step execution
    print("\nTesting multi-step execution...")
    steps = [
        {
            "tool_name": "speech",
            "params": {
                "action": "speak",
                "text": "I will now listen for your response. Please say something."
            }
        },
        {
            "tool_name": "speech",
            "params": {
                "action": "listen",
                "options": {
                    "timeout": 5.0
                }
            }
        },
        {
            "tool_name": "speech",
            "params": {
                "action": "speak",
                "text": "I heard you! Thank you for testing the speech capabilities."
            }
        }
    ]
    
    results = await radis.execute_multi_step(steps)
    
    print("\nMulti-step results:")
    for i, result in enumerate(results):
        print(f"  Step {i+1}: {result.get('status')}")
        if result.get("status") == "success" and result.get("text"):
            print(f"    Recognized: {result.get('text')}")
        
    print("\nTest completed!")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_speech_tool()) 