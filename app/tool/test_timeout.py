#!/usr/bin/env python
import asyncio
import os
import sys

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.tool.mcp_installer import MCPInstaller

async def main():
    """Test the dynamic timeout functionality of the MCP installer."""
    installer = MCPInstaller()
    
    # Get dynamic timeouts for different packages
    packages = [
        "puppeteer-mcp-server",
        "playwright-mcp-server",
        "@modelcontextprotocol/server-browser",
        "browser-automation",
        "chrome-extension",
        "simple-package"
    ]
    
    print("Testing dynamic timeout functionality:")
    print("=====================================")
    
    for package in packages:
        timeout = installer._get_dynamic_timeout(package)
        print(f"Package: {package:40} Timeout: {timeout} seconds")
    
    print("\nVerifying that background installation works:")
    print("==========================================")
    
    # Create a simple background installation tracking
    server_name = "test-background-server"
    server_id = "test_background_server"
    
    # Create a Future that will be completed after a delay
    async def delayed_completion():
        await asyncio.sleep(2)  # Simulate a 2-second installation
        
        # Create mock server info
        server_info = {
            "id": server_id,
            "name": server_name,
            "tool_name": f"mcp_{server_id}",
            "type": "npm",
            "command": "npx",
            "args": [server_name],
            "env_vars": {},
            "path": "/tmp/test",
            "installed_at": "12345678"
        }
        
        return server_info
    
    # Create the task and track it
    installation_task = asyncio.create_task(delayed_completion())
    installer.background_installs[server_name] = {
        "task": installation_task,
        "start_time": asyncio.get_event_loop().time(),
        "server_id": server_id,
        "args": [],
        "env_vars": {}
    }
    
    # Check status before completion
    print(f"Initial status check for {server_name}...")
    status = await installer.check_installation_status(server_name)
    print(f"Status: {status.status}")
    print(f"Is in background: {status.result.get('background', False)}")
    
    # Wait for completion
    print(f"Waiting for background installation to complete...")
    await asyncio.sleep(3)
    
    # Check status after completion
    print(f"Final status check for {server_name}...")
    final_status = await installer.check_installation_status(server_name)
    print(f"Status: {final_status.status}")
    print(f"Is server installed: {server_id in installer.installed_servers}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 