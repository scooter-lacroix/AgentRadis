import asyncio
from app.tool.str_replace_editor import StrReplaceEditor

async def test():
    # Create a test file
    with open("test_replace.txt", "w") as f:
        f.write("This is a test file\nwith multiple lines\nto test the string replace editor.")
    
    # Initialize the tool
    editor = StrReplaceEditor()
    
    # Test basic string replacement
    result = await editor.run(
        file_path="test_replace.txt",
        search="test",
        replace="sample"
    )
    
    print("Basic replacement result:", result)
    
    # Read the modified file
    with open("test_replace.txt", "r") as f:
        content = f.read()
    
    print("\nModified file content:")
    print(content)
    
    # Test regex replacement
    result = await editor.run(
        file_path="test_replace.txt",
        search="with.*lines",
        replace="containing text",
        use_regex=True
    )
    
    print("\nRegex replacement result:", result)
    
    # Read the modified file again
    with open("test_replace.txt", "r") as f:
        content = f.read()
    
    print("\nFinal file content:")
    print(content)
    
    await editor.cleanup()

if __name__ == "__main__":
    asyncio.run(test()) 