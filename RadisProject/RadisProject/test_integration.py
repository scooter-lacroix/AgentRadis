import pytest
import pytest_asyncio
from typing import Any, Dict, Optional
from app.tool.base import BaseTool
from app.agent.enhanced_radis import EnhancedRadis
from app.schema.models import Message
from app.schema.types import Role

class MockTool(BaseTool):
    def __init__(self, name: str = "mock_tool"):
        self._name = name
        self.was_called = False
        self.was_cleaned = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"}
            }
        }

    async def run(self, **kwargs) -> Any:
        self.was_called = True
        return {"status": "success", "result": "mock_result"}

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        self.was_called = True
        return {"status": "success", "result": "mock_result"}

    def reset(self) -> None:
        self.was_called = False
        self.was_cleaned = True

class TestEnhancedRadis:
    @pytest_asyncio.fixture
    def mock_tool(self) -> MockTool:
        return MockTool()

    def test_tool_registration_and_validation(self, agent: EnhancedRadis, mock_tool: MockTool):
        # Test tool registration
        agent.tool_registry.register_tool(mock_tool.name, mock_tool)
        assert mock_tool.name in agent.tool_registry.list_tools()

        # Test invalid tool registration
        with pytest.raises(ValueError):
            agent.tool_registry.register_tool("invalid_tool", None)

    def test_context_management(self, agent: EnhancedRadis):
        session_id = "test_session"
        
        # Initialize context
        context = agent.context_manager.get_or_create_context(session_id)
        assert context == {}
        
        # Test context updates
        test_context = {"user": "test_user", "session": "123"}
        agent.context_manager.update_context(session_id, test_context)
        assert agent.context_manager.get_context(session_id) == test_context

        # Test context overwrite
        new_context = {"updated": True}
        agent.context_manager.update_context(session_id, new_context)
        assert agent.context_manager.get_context(session_id) == new_context

    def test_memory_integration(self, agent: EnhancedRadis):
        # Test initial state
        assert len(agent.memory.messages) == 0

        # Test message addition
        test_message = Message(role=Role.USER, content="test message")
        agent.memory.add_message(test_message)
        assert len(agent.memory.messages) == 1
        assert agent.memory.messages[0] == test_message

        # Test multiple messages
        second_message = Message(role=Role.ASSISTANT, content="response")
        agent.memory.add_message(second_message)
        assert len(agent.memory.messages) == 2
        assert agent.memory.messages[1] == second_message

    @pytest.mark.asyncio
    async def test_tool_execution(self, agent: EnhancedRadis, mock_tool: MockTool):
        # Register tool
        agent.tool_registry.register_tool(mock_tool.name, mock_tool)
        
        # Test valid execution
        result = await agent.execute_tool(
            tool_name=mock_tool.name,
            parameters={"param1": "test", "param2": 42}
        )
        assert result["status"] == "success"
        assert mock_tool.was_called

        # Test invalid tool
        with pytest.raises(ValueError):
            await agent.execute_tool(
                tool_name="non_existent_tool",
                parameters={}
            )

    @pytest.mark.asyncio
    async def test_cleanup_resources(self, agent: EnhancedRadis, mock_tool: MockTool):
        session_id = "test_session"
        
        # Setup test state
        agent.tool_registry.register_tool(mock_tool.name, mock_tool)
        context = agent.context_manager.get_or_create_context(session_id)
        
        test_context = {"test": "value"}
        test_message = Message(role=Role.USER, content="test message")
        
        agent.context_manager.update_context(session_id, test_context)
        agent.memory.add_message(test_message)
        
        # Execute cleanup
        await agent.cleanup()
        
        # Verify cleanup
        assert len(agent.memory.messages) == 0
        assert agent.context_manager.get_context(session_id) == {}
        assert mock_tool.was_cleaned

