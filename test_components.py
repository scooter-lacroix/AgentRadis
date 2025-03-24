import asyncio
from app.tool.str_replace import StrReplaceEditor
from app.tool.web_search import WebSearch

async def test():
    # Initialize tools
    editor = StrReplaceEditor()
    search = WebSearch()

    # Test basic string replacement
    result = await editor.run(
        file_path="test_replace.txt",
        search="old_text",
        replace="new_text"
    )
    print(result)

    # Clean up
    await editor.cleanup()

    # Perform a simple search
    result = await search.run(
        query="python programming",
        engine="google",
        num_results=3
    )
    print(result)

    # Test cleanup method to ensure sessions are properly closed
    await search.cleanup()

if __name__ == "__main__":
    asyncio.run(test())
