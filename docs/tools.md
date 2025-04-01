# Tool Development Guide

This guide provides information on how to develop and integrate new tools into RadisProject.

## Creating a New Tool

To create a new tool, you need to create a class that inherits from `BaseTool` and implements the `__call__` method.

### Example Tool

```python
from app.tool.base import BaseTool

class MyTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="A description of what the tool does.",
            require_args=False  # Set to True if the tool requires arguments
        )

    def __call__(self, args=None, session_context=None, **kwargs):
        # Implement the tool's logic here
        return "Tool executed successfully!"
```

### Tool Attributes

*   `name`: The name of the tool (used for registration and invocation).
*   `description`: A description of what the tool does.
*   `require_args`: A flag indicating whether the tool requires arguments.

### Tool Methods

*   `__call__(args=None, session_context=None, **kwargs)`: This abstract method must be implemented by all tools. It contains the tool's logic and is called when the tool is executed.

## Integrating a Tool with the Tool Registry

To integrate a new tool with the Tool Registry, you need to register it with the `ToolRegistry` instance.

### Registration

```python
from app.core.tool_registry import ToolRegistry

# Get the tool registry instance
registry = ToolRegistry.get_instance()

# Create an instance of your tool
my_tool = MyTool()

# Register the tool
registry.register_tool(my_tool)
```

## Usage

Once a tool is registered, it can be called using the `call_tool` method on the `ToolRegistry` instance.

### Calling a Tool

```python
# Call a tool that doesn't require arguments
result = registry.call_tool("my_tool")
print(result)  # Output: Tool executed successfully!
```

## Best Practices

*   Keep tools small and focused on a single responsibility.
*   Document the expected input and output clearly.
*   Handle exceptions gracefully.
*   Return structured data when possible.
