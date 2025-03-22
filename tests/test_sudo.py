import pytest
import asyncio
from app.agent.enhanced_radis import EnhancedRadis
from app.tool.terminal import Terminal
from app.tool.sudo_tool import SudoTool
from app.utils.sudo import run_sudo_command

@pytest.mark.asyncio
async def test_sudo_integration():
    """Test the integration between Terminal and SudoTool"""
    
    # Create tools
    terminal = Terminal()
    sudo_tool = SudoTool()
    
    # Create agent with both tools
    agent = EnhancedRadis(tools=[terminal, sudo_tool])
    
    # Test a simple sudo command
    response = await agent.run("Show me the sudo version using sudo -V")
    
    # Check response
    assert response["status"] == "success"
    assert "tool_calls" in response
    
    # Test a command that should be restricted in terminal but work with sudo
    response = await agent.run("Update the package list using apt update")
    
    # Check response
    assert response["status"] == "success"
    assert "tool_calls" in response

@pytest.mark.asyncio
async def test_terminal_restrictions():
    """Test that dangerous commands are properly restricted in Terminal"""
    
    terminal = Terminal()
    
    # Test that rm is still restricted
    with pytest.raises(ValueError, match="Use of dangerous commands is restricted"):
        await terminal.execute("rm -rf /")
        
    # Test that shutdown is still restricted
    with pytest.raises(ValueError, match="Use of dangerous commands is restricted"):
        await terminal.execute("shutdown now")
        
    # Test that reboot is still restricted
    with pytest.raises(ValueError, match="Use of dangerous commands is restricted"):
        await terminal.execute("reboot")
        
    # Test that sudo is allowed (since we removed it from restrictions)
    result = await terminal.execute("sudo -V")
    assert isinstance(result.output, str)
    assert isinstance(result.error, str) 