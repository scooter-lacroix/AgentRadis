import asyncio
import os
import json
from typing import List, ClassVar, Dict, Any
from app.agent.base import BaseAgent
from app.agent.toolcall import ToolCallAgent
from app.tool import StrReplaceEditor, Terminate, BaseTool, ToolCollection
from app.schema import AgentMemory, Message, Role, AgentState
from app.config import config

class TestToolCallAgent(ToolCallAgent):
    """Test agent class for testing ToolCallAgent functionality"""
    
    name: ClassVar[str] = "TestToolCallAgent"
    description: ClassVar[str] = "A test agent for verifying ToolCallAgent functionality"
    available_tools: ClassVar[ToolCollection] = ToolCollection(
        StrReplaceEditor(), 
        Terminate()
    )

    async def run(self, prompt: str) -> Dict[str, Any]:
        """
        Run the agent with a prompt.
        
        Args:
            prompt: The input prompt to process
            
        Returns:
            Dict containing the response
        """
        # Add the user prompt to memory
        self.memory.add_message(Role.USER, prompt)
        
        # Set the initial state
        self.state = AgentState.THINKING
        
        try:
            # Process the prompt (simplified for testing)
            thinking_result = await self.think()
            
            results = []
            if thinking_result and self.tool_calls:
                # Execute the tool calls
                for tool_call in self.tool_calls:
                    try:
                        tool_name = tool_call.function.name
                        # Parse arguments from tool call
                        args = {}
                        if isinstance(tool_call.function.arguments, str):
                            try:
                                args = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                print(f"Invalid JSON in arguments: {tool_call.function.arguments}")
                        elif isinstance(tool_call.function.arguments, dict):
                            args = tool_call.function.arguments
                        
                        # Get the tool from the collection
                        tool = self.available_tools.get(tool_name)
                        if tool:
                            # Execute the tool
                            result = await tool.run(**args)
                            results.append(result)
                            print(f"Tool execution result: {result}")
                    except Exception as e:
                        print(f"Error executing tool: {e}")
            
            # Prepare the response
            final_response = {
                "status": "success",
                "result": "Task completed successfully",
                "tool_results": results,
                "message": "The agent completed the file editing task."
            }
            
            return final_response
            
        except Exception as e:
            # Handle errors
            error_msg = f"Error during execution: {str(e)}"
            return {
                "status": "error",
                "error": error_msg,
                "message": "The agent encountered an error during execution."
            }
    
async def test():
    # Create a test file
    with open("agent_test_file.txt", "w") as f:
        f.write("This is a test file for the agent to modify.\nIt contains text that can be replaced.")
    
    # Set up memory
    memory = AgentMemory()
    memory.add_message(Role.SYSTEM, "You are a helpful assistant that follows instructions.")
    
    # Define the prompt
    prompt = "Replace the word 'test' with 'demo' in the file 'agent_test_file.txt'."
    
    # Create and run the agent
    agent = TestToolCallAgent(memory=memory)
    result = await agent.run(prompt)
    
    print("Agent run result:", result)
    
    # Read the modified file
    try:
        with open("agent_test_file.txt", "r") as f:
            content = f.read()
            print("\nModified file content:")
            print(content)
    except Exception as e:
        print(f"Error reading file: {e}")
    
    # Clean up
    try:
        os.remove("agent_test_file.txt")
        print("\nTest file removed.")
    except Exception as e:
        print(f"Error removing test file: {e}")

if __name__ == "__main__":
    asyncio.run(test()) 