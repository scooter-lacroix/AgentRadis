import os
import sys
import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tool.mcp_installer import MCPInstaller, MCPServerTool
from app.agent.radis import Radis
from app.schema import ToolResult

@pytest.mark.asyncio
async def test_mcp_installer_initialization():
    """Test that the MCP installer can be initialized correctly."""
    installer = MCPInstaller()
    assert installer.name == "mcp_installer"
    assert "MCP" in installer.description
    assert len(installer.examples) > 0
    assert installer.is_stateful is True
    
@pytest.mark.asyncio
async def test_mcp_server_tool_initialization():
    """Test that an MCP server tool can be initialized correctly."""
    server_info = {
        "id": "test_server",
        "name": "test-server",
        "tool_name": "mcp_test_server",
        "type": "npm",
        "command": "node",
        "args": ["server.js"],
        "env_vars": {"TEST_VAR": "test_value"},
        "path": "/tmp/test_server",
        "installed_at": "12345"
    }
    
    server_tool = MCPServerTool(server_info)
    assert server_tool.name == "mcp_test_server"
    assert "MCP Server" in server_tool.description
    assert server_tool.server_info == server_info
    assert server_tool.is_stateful is True

@pytest.mark.asyncio
@patch('asyncio.create_subprocess_exec')
async def test_register_mcp_server(mock_subprocess):
    """Test that an MCP server can be registered with the agent."""
    # Set up mocks
    mock_process = MagicMock()
    mock_process.communicate = MagicMock(return_value=asyncio.Future())
    mock_process.communicate.return_value.set_result((b"test output", b""))
    mock_subprocess.return_value = asyncio.Future()
    mock_subprocess.return_value.set_result(mock_process)
    
    # Create server info
    server_info = {
        "id": "test_server",
        "name": "test-server",
        "tool_name": "mcp_test_server",
        "type": "npm",
        "command": "node",
        "args": ["server.js"],
        "env_vars": {"TEST_VAR": "test_value"},
        "path": "/tmp/test_server",
        "installed_at": "12345"
    }
    
    # Initialize agent and register server
    agent = Radis()
    result = await agent.register_mcp_server(server_info)
    
    # Check that server was registered
    assert result is True
    assert "mcp_test_server" in agent.tools.get_tools()
    
    # Clean up
    await agent.reset()

@pytest.mark.asyncio
@patch('os.path.exists')
@patch('shutil.which')
@patch('asyncio.create_subprocess_exec')
async def test_mcp_installer_execute(mock_subprocess, mock_which, mock_exists):
    """Test that the MCP installer can execute correctly."""
    # Set up mocks
    mock_exists.return_value = True
    mock_which.return_value = "/usr/bin/npx"
    
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate = MagicMock(return_value=asyncio.Future())
    mock_process.communicate.return_value.set_result((b"test output", b""))
    mock_subprocess.return_value = asyncio.Future()
    mock_subprocess.return_value.set_result(mock_process)
    
    # Initialize installer
    installer = MCPInstaller()
    
    # Mock saving installed servers
    installer._save_installed_servers = MagicMock()
    
    # Execute installer
    result = await installer.execute(
        server_name="test-server",
        args=["--test-arg"],
        env_vars={"TEST_VAR": "test_value"},
        local_path="/test/path"
    )
    
    # Check result
    assert isinstance(result, ToolResult)
    assert result.status == "SUCCESS"
    assert "test-server" in result.result.get("server_name", "")
    
    # Clean up
    await installer.reset()

@pytest.mark.asyncio
@patch('os.path.exists')
@patch('shutil.which')
@patch('asyncio.create_subprocess_exec')
@patch('app.tool.mcp_installer.MCPInstaller._install_from_npm')
async def test_dynamic_timeout(mock_install_npm, mock_subprocess, mock_which, mock_exists):
    """Test that dynamic timeouts are applied correctly."""
    # Set up mocks
    mock_exists.return_value = False
    mock_which.return_value = "/usr/bin/npx"
    
    # Create a delayed installation future
    delayed_future = asyncio.Future()
    mock_install_npm.return_value = delayed_future
    
    # Initialize installer
    installer = MCPInstaller()
    installer._save_installed_servers = MagicMock()
    
    # Start execution but don't await it
    execution_task = asyncio.create_task(installer.execute(
        server_name="puppeteer-mcp-server",  # Should have a 600s timeout from PACKAGE_TIMEOUTS
        args=["--test-arg"]
    ))
    
    # Short delay to let execution start
    await asyncio.sleep(0.1)
    
    # Verify the dynamic timeout was applied
    # We can't directly check the timeout, but we can verify the package name was recognized
    assert "puppeteer-mcp-server" in installer.PACKAGE_TIMEOUTS
    assert installer._get_dynamic_timeout("puppeteer-mcp-server") == 600.0
    
    # Complete the installation after a short delay
    await asyncio.sleep(0.2)
    server_info = {
        "id": "puppeteer-mcp-server",
        "name": "puppeteer-mcp-server",
        "tool_name": "mcp_puppeteer_mcp_server",
        "type": "npm",
        "command": "npx",
        "args": ["puppeteer-mcp-server", "--test-arg"],
        "env_vars": {},
        "path": "/tmp/test",
        "installed_at": str(time.time())
    }
    delayed_future.set_result(server_info)
    
    # Wait for execution to complete
    result = await execution_task
    
    # Check result
    assert result.status == "SUCCESS"
    assert "puppeteer-mcp-server" in result.result.get("server_name", "")
    
    # Verify that installation time was tracked
    assert "installation_time" in result.result
    
    # Clean up
    await installer.reset()

@pytest.mark.asyncio
@patch('os.path.exists')
@patch('shutil.which')
@patch('asyncio.create_subprocess_exec')
@patch('app.tool.mcp_installer.MCPInstaller._install_from_npm')
@patch('app.tool.mcp_installer.asyncio.wait_for')  # Patch at module level instead of global asyncio
async def test_background_installation(mock_wait_for, mock_install_npm, mock_subprocess, mock_which, mock_exists):
    """Test that installations move to background when they timeout."""
    # Set up mocks
    mock_exists.return_value = False
    mock_which.return_value = "/usr/bin/npx"
    
    # Configure the wait_for mock to raise TimeoutError
    mock_wait_for.side_effect = asyncio.TimeoutError()
    
    # Create a never-resolving future to simulate a long installation
    installation_future = asyncio.Future()
    mock_install_npm.return_value = installation_future
    
    # Initialize installer
    installer = MCPInstaller()
    installer._save_installed_servers = MagicMock()
    
    # Properly mock the progress reporting to avoid task destruction issues
    installer._report_progress = AsyncMock()
    
    # Execute installer (this should timeout and move to background)
    result = await installer.execute(
        server_name="slow-server",
        args=["--test-arg"]
    )
    
    # Check that result indicates pending status
    assert result.status == "PENDING"
    assert "background" in result.result
    assert result.result["background"] is True
    
    # Verify the server is tracked in background installs
    assert "slow-server" in installer.background_installs
    
    # Now check the status
    status_result = await installer.check_installation_status("slow-server")
    assert status_result.status == "PENDING"
    
    # Complete the installation in the background
    server_info = {
        "id": "slow_server",
        "name": "slow-server",
        "tool_name": "mcp_slow_server",
        "type": "npm",
        "command": "npx",
        "args": ["slow-server", "--test-arg"],
        "env_vars": {},
        "path": "/tmp/test",
        "installed_at": str(time.time())
    }
    installation_future.set_result(server_info)
    
    # Wait a bit for background processing
    await asyncio.sleep(0.1)
    
    # Check status again - should be SUCCESS now
    final_status = await installer.check_installation_status("slow-server")
    assert final_status.status == "SUCCESS"
    
    # Verify installation is no longer in background
    assert "slow-server" not in installer.background_installs
    
    # Make sure to properly clean up all futures
    if not installation_future.done():
        installation_future.set_result(None)
    
    # Clean up
    await installer.reset()

@pytest.mark.asyncio
async def test_dynamic_timeout_simple():
    """Test that dynamic timeouts are correctly determined based on package name."""
    installer = MCPInstaller()
    
    # Test exact matches
    assert installer._get_dynamic_timeout("puppeteer-mcp-server") == 600.0
    assert installer._get_dynamic_timeout("playwright-mcp-server") == 600.0
    assert installer._get_dynamic_timeout("@modelcontextprotocol/server-browser") == 480.0
    
    # Test partial matches
    assert installer._get_dynamic_timeout("custom-puppeteer-package") == 600.0
    
    # Test browser-related packages
    assert installer._get_dynamic_timeout("chrome-automation") == 600.0
    
    # Test default timeout
    assert installer._get_dynamic_timeout("simple-package") == 300.0

@pytest.mark.asyncio
@patch('app.tool.mcp_installer.MCPInstaller._save_installed_servers')
async def test_background_installation_management(mock_save):
    """Test that background installations are properly tracked and managed."""
    installer = MCPInstaller()
    
    # Setup a mock background installation
    server_name = "test-server"
    server_id = "test_server"
    
    # Create an actual Future instead of AsyncMock
    mock_task = asyncio.Future()
    
    # Manually set up a background installation
    start_time = time.time()
    installer.background_installs[server_name] = {
        "task": mock_task,
        "start_time": start_time,
        "server_id": server_id,
        "args": ["--test"],
        "env_vars": {}
    }
    
    # Mock the agent reference to avoid None errors
    installer.agent = MagicMock()
    installer.agent.register_mcp_server = AsyncMock(return_value=True)
    
    # Check status before completion - should be pending
    status_result = await installer.check_installation_status(server_name)
    assert status_result.status == "PENDING"
    assert "background" in status_result.result
    assert status_result.result["background"] is True
    
    # Now simulate completion by setting the result on the Future
    server_info = {
        "id": server_id,
        "name": server_name,
        "tool_name": f"mcp_{server_id}",
        "type": "npm",
        "command": "npx",
        "args": [server_name, "--test"],
        "env_vars": {},
        "path": "/tmp/test",
        "installed_at": str(time.time())
    }
    mock_task.set_result(server_info)
    
    # Verify that the task is done before checking status
    assert mock_task.done()
    
    # Check status again - should now be SUCCESS
    final_status = await installer.check_installation_status(server_name)
    
    # Check the actual contents of the final status
    print(f"Final status: {final_status.status}, Result: {final_status.result}")
    
    assert final_status.status == "SUCCESS"
    assert server_name not in installer.background_installs
    assert server_id in installer.installed_servers
    
    # Clean up
    await installer.reset()

if __name__ == "__main__":
    asyncio.run(test_mcp_installer_initialization())
    asyncio.run(test_mcp_server_tool_initialization())
    # Other tests require mocking and would be run with pytest 