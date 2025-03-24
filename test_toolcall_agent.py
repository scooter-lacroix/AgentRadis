import asyncio
from app.agent.toolcall import ToolCallAgent

async def test():
    # Initialize the tool call agent
    agent = ToolCallAgent()

    # Test a basic tool call
    result = await agent.run("Test prompt")
    print(result)

    # Clean up
    await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(test())
