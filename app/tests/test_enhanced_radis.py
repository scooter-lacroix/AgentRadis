import pytest
import asyncio
from app.agent.enhanced_radis import EnhancedRadis
from app.schema import AgentState, Role, Message

@pytest.mark.asyncio
async def test_planning_mode_initialization():
    """Test that planning mode is properly initialized"""
    agent = EnhancedRadis(mode="plan")
    assert agent.mode == "plan"
    assert "PlanningTool" in [tool.__class__.__name__ for tool in agent.tools]
    assert "Terminate" in [tool.__class__.__name__ for tool in agent.tools]
    assert agent.active_plan_id is None
    assert agent.step_execution_tracker == {}

@pytest.mark.asyncio
async def test_plan_creation():
    """Test plan creation and tracking"""
    agent = EnhancedRadis(mode="plan")
    plan_result = await agent.create_plan("Test task")
    assert agent.active_plan_id is not None
    assert isinstance(plan_result, str)
    assert "plan_" in agent.active_plan_id

@pytest.mark.asyncio
async def test_plan_execution_tracking():
    """Test that plan execution is properly tracked"""
    agent = EnhancedRadis(mode="plan")
    await agent.create_plan("Test task")
    
    # Simulate a step execution
    agent.state = AgentState.EXECUTING
    agent.current_step_index = 0
    await agent.step()
    
    assert 0 in agent.step_execution_tracker
    assert agent.step_execution_tracker[0]["status"] == "completed"

@pytest.mark.asyncio
async def test_plan_status_updates():
    """Test plan status updates"""
    agent = EnhancedRadis(mode="plan")
    await agent.create_plan("Test task")
    await agent.update_plan_status(0, "completed")
    plan_status = await agent.get_plan()
    assert isinstance(plan_status, str)

@pytest.mark.asyncio
async def test_plan_reset():
    """Test that planning state is properly reset"""
    agent = EnhancedRadis(mode="plan")
    await agent.create_plan("Test task")
    assert agent.active_plan_id is not None
    
    await agent.reset()
    assert agent.active_plan_id is None
    assert agent.current_step_index is None
    assert agent.step_execution_tracker == {}

@pytest.fixture
async def agent():
    """Create a test agent instance"""
    agent = EnhancedRadis(mode="act")
    await agent.reset()
    return agent

@pytest.mark.asyncio
async def test_add_artifact():
    """Test adding artifacts"""
    agent = EnhancedRadis(mode="act")
    
    # Test code artifact
    agent.add_artifact("code", "print('test')", language="python")
    assert len(agent.artifacts) == 1
    assert agent.artifacts[0]["type"] == "code"
    assert agent.artifacts[0]["content"] == "print('test')"
    assert agent.artifacts[0]["language"] == "python"
    
    # Test web artifact
    agent.add_artifact("web", "<html>test</html>")
    assert len(agent.artifacts) == 2
    assert agent.artifacts[1]["type"] == "web"
    assert agent.artifacts[1]["content"] == "<html>test</html>"
    
    # Test project artifact
    project_structure = {"src": {"main.py": None}}
    agent.add_artifact("project", project_structure)
    assert len(agent.artifacts) == 3
    assert agent.artifacts[2]["type"] == "project"
    assert agent.artifacts[2]["content"] == project_structure

@pytest.mark.asyncio
async def test_add_tool_call():
    """Test adding tool calls"""
    agent = EnhancedRadis(mode="act")
    
    # Test successful tool call
    agent.add_tool_call(
        "TestTool",
        {"param": "value"},
        "success result",
        True
    )
    assert len(agent.tool_calls) == 1
    assert agent.tool_calls[0]["name"] == "TestTool"
    assert agent.tool_calls[0]["args"] == {"param": "value"}
    assert agent.tool_calls[0]["result"] == "success result"
    assert agent.tool_calls[0]["success"] is True
    
    # Test failed tool call
    agent.add_tool_call(
        "ErrorTool",
        {"param": "bad_value"},
        "error message",
        False
    )
    assert len(agent.tool_calls) == 2
    assert agent.tool_calls[1]["name"] == "ErrorTool"
    assert agent.tool_calls[1]["success"] is False

@pytest.mark.asyncio
async def test_run_with_artifacts():
    """Test running agent with artifact generation"""
    agent = EnhancedRadis(mode="act")
    
    # Mock the _handle_tool_call method to simulate tool execution
    async def mock_handle_tool_call(tool_call):
        if "code" in tool_call.get("name", "").lower():
            return "print('Hello')"
        elif "web" in tool_call.get("name", "").lower():
            return "<html>test</html>"
        return "default result"
    
    agent._handle_tool_call = mock_handle_tool_call
    
    # Run agent with a prompt that would trigger tool calls
    result = await agent.run("Test prompt")
    
    assert "artifacts" in result
    assert "tool_calls" in result
    assert isinstance(result["artifacts"], list)
    assert isinstance(result["tool_calls"], list)

@pytest.mark.asyncio
async def test_error_handling_with_artifacts():
    """Test error handling with artifacts"""
    agent = EnhancedRadis(mode="act")
    
    # Mock tool call to raise an error
    async def mock_error_tool_call(tool_call):
        # Add a failed tool call to the agent
        agent.tool_calls.append({
            "tool": tool_call.name,
            "args": tool_call.arguments,
            "success": False,
            "error": "Test error"
        })
        # Set max error attempts to 0 to ensure immediate error propagation
        agent.error_recovery_attempts = agent.max_consecutive_errors
        # Add error message to memory
        agent.memory.messages.append(Message(
            role=Role.TOOL,
            name=tool_call.name,
            tool_call_id=tool_call.id,
            content="Error: Test error"
        ))
        e = Exception("Test error")
        e.tool_call = tool_call
        raise e
    
    agent._execute_tool_call = mock_error_tool_call
    
    # Run agent with error-inducing prompt
    result = await agent.run("Test error prompt")
    
    assert "error" in result["status"].lower()
    assert isinstance(result["artifacts"], list)
    assert isinstance(result["tool_calls"], list)
    assert any(not call.get("success", True) for call in result["tool_calls"])

@pytest.mark.asyncio
async def test_artifact_cleanup_between_runs():
    """Test that artifacts are cleaned up between runs"""
    agent = EnhancedRadis(mode="act")
    
    # First run
    agent.add_artifact("code", "test1")
    result1 = await agent.run("First test")
    assert len(result1["artifacts"]) == 1
    
    # Second run should start fresh
    result2 = await agent.run("Second test")
    assert len(result2["artifacts"]) == 0

@pytest.mark.asyncio
async def test_tool_call_tracking():
    """Test that tool calls are properly tracked"""
    agent = EnhancedRadis(mode="act")
    
    # Mock successful and failed tool calls
    async def mock_mixed_tool_calls(tool_call):
        if "error" in tool_call.get("name", "").lower():
            raise Exception("Test error")
        return "success"
    
    agent._handle_tool_call = mock_mixed_tool_calls
    
    # Run agent with multiple tool calls
    result = await agent.run("Test multiple tools")
    
    assert isinstance(result["tool_calls"], list)
    assert "status" in result
    
    # Verify tool call tracking is reset between runs
    assert len(agent.tool_calls) == 0  # Should be reset after run 