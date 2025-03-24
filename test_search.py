import asyncio
from app.tool.web_search import WebSearch

async def test():
    # Initialize the web search tool
    engine = WebSearch()

    # Test a basic search
    result = await engine.search('test query')
    print(result)

    # Clean up
    await engine.cleanup()

if __name__ == "__main__":
    asyncio.run(test())
