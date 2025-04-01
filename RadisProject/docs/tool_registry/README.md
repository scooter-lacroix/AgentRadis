# Tool Registry

The Tool Registry is a core component of the RadisProject that manages the registration, discovery, validation, and execution of tools used by the system. It provides a centralized way to track all available tools, validate their implementations, and collect usage metrics.

## Purpose

The Tool Registry serves several critical functions:

1. **Tool Registration**: Provides a centralized mechanism for registering tools that can be used by the agent.
2. **Tool Discovery**: Allows the system to discover available tools and their capabilities.
3. **Tool Validation**: Ensures that all registered tools meet the required interface specifications.
4. **Metrics Collection**: Tracks tool usage metrics such as call counts and execution times.
5. **Error Handling**: Provides standardized error handling for tool execution.
6. **Concurrency Management**: Supports thread-safe tool access and execution.

## Key Classes

### ToolRegistry

`ToolRegistry` is the central class responsible for managing tools. It implements the Singleton pattern to ensure there's only one registry instance throughout the application.

```python
class ToolRegistry:
    _instance = None
    
    @staticmethod
    def get_instance():
        if ToolRegistry._instance is None:
            ToolRegistry._instance = ToolRegistry()
        return ToolRegistry._instance
```

#### Attributes

- `_tools`: Dictionary mapping tool names to tool instances
- `_tool_counts`: Dictionary tracking the number of calls for each tool
- `_validator`: Optional validator function for tool verification
- `_lock`: RLock for thread-safe operations

### BaseTool

`BaseTool` is the abstract base class that all tools must inherit from. It defines the required interface for all tools and provides common functionality.

```python
class BaseTool(metaclass=abc.ABCMeta):
    def __init__(self, name, description, require_args=False):
        self.name = name
        self.description = description
        self.require_args = require_args
        
    @abc.abstractmethod
    def __call__(self, args=None, session_context=None, **kwargs):
        pass
```

#### Attributes

- `name`: The name of the tool (used for registration and invocation)
- `description`: A description of what the tool does
- `require_args`: Flag indicating whether the tool requires arguments

## Methods

### ToolRegistry Methods

#### `register_tool(tool, replace=False)`

Registers a tool with the registry.

- **Parameters**:
  - `tool`: The tool instance to register (must inherit from BaseTool)
  - `replace`: Whether to replace an existing tool with the same name (default: False)
- **Returns**: None
- **Raises**: 
  - `ValueError`: If a tool with the same name already exists and replace=False
  - `ValueError`: If the tool fails validation

#### `register_tools(tools, replace=False)`

Registers multiple tools with the registry.

- **Parameters**:
  - `tools`: List of tool instances to register
  - `replace`: Whether to replace existing tools (default: False)
- **Returns**: None

#### `validate_tool(tool)`

Validates that a tool meets the required interface.

- **Parameters**:
  - `tool`: The tool instance to validate
- **Returns**: True if valid, otherwise raises an exception
- **Raises**: ValueError if the tool fails validation

#### `set_validator(validator)`

Sets a custom validator function for tool validation.

- **Parameters**:
  - `validator`: Function that accepts a tool and returns True or raises an exception
- **Returns**: None

#### `reset()`

Clears all registered tools and resets usage metrics.

- **Returns**: None

#### `has_tool(tool_name)`

Checks if a tool is registered.

- **Parameters**:
  - `tool_name`: Name of the tool to check
- **Returns**: Boolean indicating whether the tool exists

#### `get_tool(tool_name)`

Retrieves a tool by name.

- **Parameters**:
  - `tool_name`: Name of the tool to retrieve
- **Returns**: The tool instance
- **Raises**: KeyError if the tool doesn't exist

#### `get_tool_names()`

Gets the names of all registered tools.

- **Returns**: List of tool names

#### `get_tools()`

Gets all registered tools.

- **Returns**: Dictionary mapping tool names to tool instances

#### `call_tool(tool_name, args=None, session_context=None, **kwargs)`

Calls a registered tool with the given arguments.

- **Parameters**:
  - `tool_name`: Name of the tool to call
  - `args`: Arguments to pass to the tool
  - `session_context`: Current session context
  - `**kwargs`: Additional keyword arguments
- **Returns**: Result of the tool execution
- **Raises**: 
  - `KeyError`: If the tool doesn't exist
  - Passes through any exceptions raised by the tool

#### `get_tool_counts()`

Gets the usage counts for all tools.

- **Returns**: Dictionary mapping tool names to call counts

### BaseTool Methods

#### `__call__(args=None, session_context=None, **kwargs)`

Abstract method that must be implemented by all tools.

- **Parameters**:
  - `args`: Arguments for the tool
  - `session_context`: Current session context
  - `**kwargs`: Additional keyword arguments
- **Returns**: Result of the tool execution

## Usage Examples

### Registering a Tool

```python
from app.tool.base import BaseTool
from app.core.tool_registry import ToolRegistry

class HelloWorldTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="hello_world",
            description="Returns a hello world message",
            require_args=False
        )
    
    def __call__(self, args=None, session_context=None, **kwargs):
        return "Hello, World!"

# Get the tool registry instance
registry = ToolRegistry.get_instance()

# Register the tool
registry.register_tool(HelloWorldTool())
```

### Creating a Tool with Arguments

```python
class GreetingTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="greet",
            description="Greets a person by name",
            require_args=True
        )
    
    def __call__(self, args=None, session_context=None, **kwargs):
        if not args or "name" not in args:
            raise ValueError("This tool requires a 'name' argument")
        return f"Hello, {args['name']}!"

# Register the tool
registry.register_tool(GreetingTool())
```

### Using a Tool

```python
# Call a tool that doesn't require arguments
result = registry.call_tool("hello_world")
print(result)  # Output: Hello, World!

# Call a tool that requires arguments
result = registry.call_tool("greet", args={"name": "Alice"})
print(result)  # Output: Hello, Alice!
```

### Checking Tool Usage Metrics

```python
# Get tool usage counts
counts = registry.get_tool_counts()
print(counts)  # Output: {'hello_world': 1, 'greet': 1}
```

## Concurrency Considerations

The ToolRegistry is designed to be thread-safe:

1. **Singleton Pattern**: The registry implements the Singleton pattern to ensure a single global registry.
2. **Thread Safety**: All methods that modify the registry's state use an RLock to prevent race conditions.
3. **Tool Registration**: Tools should be registered at application startup to avoid concurrency issues.
4. **Metrics Tracking**: The tool call count tracking is thread-safe thanks to the lock mechanism.

```python
def _increment_tool_count(self, tool_name):
    """Increment the call count for a tool in a thread-safe manner."""
    with self._lock:
        if tool_name not in self._tool_counts:
            self._tool_counts[tool_name] = 0
        self._tool_counts[tool_name] += 1
```

## Tool Registration and Validation

### Registration Process

1. Tools must inherit from the `BaseTool` abstract base class.
2. Tools must implement the `__call__` method with the correct signature.
3. Tools are registered with the registry using `register_tool()` or `register_tools()`.
4. The registry validates each tool during registration.
5. By default, tools with duplicate names are rejected unless `replace=True` is specified.

### Validation Mechanism

The default validation verifies:

1. The tool inherits from `BaseTool`
2. The tool has the required attributes (`name`, `description`, etc.)
3. The tool implements the required methods

Custom validators can be set using `set_validator()` to enforce additional requirements.

## Metrics Tracking

The Tool Registry automatically tracks:

1. **Call Counts**: The number of times each tool is called
2. **Tools Used**: Which tools have been registered and are available

These metrics can be accessed via:
- `get_tool_counts()`: Returns a dictionary of tool names and call counts
- `get_tools()`: Returns all registered tools

## Best Practices

1. **Tool Development**:
   - Keep tools small and focused on a single responsibility
   - Document the expected input and output clearly
   - Handle exceptions gracefully
   - Return structured data when possible

2. **Tool Registration**:
   - Register tools during application initialization
   - Use descriptive names and detailed descriptions
   - Consider using tool categories or namespaces for organization

3. **Thread Safety**:
   - Avoid modifying the registry after initialization
   - Ensure tools themselves are thread-safe
   - Consider using immutable data structures in tool implementations

4. **Error Handling**:
   - Tools should raise specific exceptions when appropriate
   - The calling code should handle tool exceptions gracefully
   - Log tool errors for monitoring and debugging

