import asyncio
from app.tool.str_replace import StrReplaceEditor

async def test():
    # Initialize the string replacement tool
    editor = StrReplaceEditor()

    # Test basic string replacement
    result = await editor.run(
        file_path="test_replace.txt",
        search="old_text",
        replace="new_text"
    )
    print(result)

    # Test regex replacement
    result = await editor.run(
        file_path="test_replace.txt",
        search=r"old_text",
        replace="new_text",
        regex=True
    )
    print(result)

    # Clean up
    await editor.cleanup()

if __name__ == "__main__":
    asyncio.run(test())
