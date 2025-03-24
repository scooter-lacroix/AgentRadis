import asyncio
from app.tool.web_search import WebSearch

async def test():
    # Initialize the web search tool
    search_tool = WebSearch()

    # Test a basic search
    result = await search_tool.run(
        query="AgentRadis autonomous agent system",
        engine="google",
        num_results=3
    )

    print("Search result status:", result.get("status"))
    print("Search engine used:", result.get("engine"))
    print(f"Found {len(result.get('results', []))} results for:", result.get("query"))

    # Print the search results
    if result.get("status") == "success":
        for i, item in enumerate(result.get("results", []), 1):
            print(f"\nResult {i}:")
            print(f"Title: {item.get('title', 'No title')}")
            print(f"URL: {item.get('url', 'No URL')}")
            print(f"Snippet: {item.get('snippet', 'No snippet')}")
    else:
        print("Error:", result.get("error"))

    # Clean up
    await search_tool.cleanup()

if __name__ == "__main__":
    asyncio.run(test())
