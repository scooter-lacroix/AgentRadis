# Agent Framework

## Purpose and Overview

The Agent Framework is a core component of the RadisProject that provides a structured system for creating, managing, and orchestrating AI agents. It defines a standardized interface for all agents in the system, ensuring consistent behavior and interaction patterns regardless of the specific agent implementation.

The framework enables:
- Standardized agent lifecycle management (initialization, setup, execution, cleanup)
- Consistent messaging and tool calling interfaces
- Flexible agent composition and extension
- Security boundaries and identity management
- Structured tool execution patterns

## Architecture

The Agent Framework follows a hierarchical design with abstract base classes defining interfaces that concrete implementations must follow:

```
BaseAgent (Abstract)
├── RadisAgent
│   └── EnhancedRadis (Adds security and identity management)
└── ToolCallAgent (Specializes in tool execution)
```

This architecture allows for:
- Common behavior sharing through inheritance
- Specialized agent implementations for different use cases
- Clear separation of concerns between base functionality and extensions

## Key Classes

### BaseAgent

`BaseAgent` is the abstract base class that all agents must inherit from. It defines the core interface and common functionality for all agents in the system.

**Location**: `app/agent/base.py`

**Key Methods**:
- `async_setup()`: Initializes the agent and prepares it for use
- `run(input_text, **kwargs)`: Processes input and returns results
- `step()`: Executes a single processing step
- `reset()`: Returns the agent to its initial state
- `cleanup()`: Releases resources used by the agent
- `prepare_llm_request(messages, functions, **kwargs)`: Formats requests for the LLM

**Properties**:
- `name`: Identifier for the agent
- `is_configured`: Whether the agent has been properly set up
- `tool_choice`: How the agent selects tools (AUTO, REQUIRED, NONE)

**Usage Example**:
```python
class MyCustomAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "my_custom_agent"
        
    async def async_setup(self) -> None:
        # Initialize resources
        self._is_configured = True
        
    async def run(self, input_text: str, **kwargs) -> Dict[str, Any]:
        # Process input and return results
        pass
        
    async def step(self) -> bool:
        # Execute one processing step
        return False  # No more steps needed
        
    async def reset(self) -> None:
        # Reset to initial state
        pass
        
    async def cleanup(self) -> None:
        # Release resources
        pass
```

### RadisAgent

The primary agent implementation that extends BaseAgent with RadisProject-specific functionality.

**Location**: `app/agent/radis.py` (referenced from enhanced_radis.py)

### EnhancedRadis

An extension of RadisAgent that adds security boundaries and identity management.

**Location**: `app/agent/enhanced_radis.py`

**Key Components**:
- `tool_registry`: Registry for accessing and managing tools
- `response_processor`: Processes and sanitizes responses
- `identity_context`: Manages agent identity and context
- `command_history`: Tracks command executions for security
- `security_config`: Configures security boundaries
- `context_manager`: Manages conversation contexts

**Usage Example**:
```python
# Initialize the enhanced agent
agent = EnhancedRadis(
    mode="act",
    tools=["file_reader", "calculator"],
    model="gpt-4-turbo"
)

# Setup and run
await agent.async_setup()
result = await agent.run("Please read the content of config.json")
print(result["response"])
```

### ToolCallAgent

Agent specialized in handling and executing tool calls.

**Location**: `app/agent/toolcall.py`

**Key Features**:
- Dedicated to tool execution and management
- Handles multiple tool calls in sequence
- Manages tool execution state

**Usage Example**:
```python
# Initialize the tool call agent
tool_agent = ToolCallAgent()

# Setup and run
await tool_agent.async_setup()
result = await tool_agent.run("Calculate 15% of 75 and then convert to EUR")
print(result["tool_calls"])  # Shows the executed tool calls
```

## Messaging System

Agents communicate using a structured messaging system:

- `Message`: Represents a single message in a conversation
- `ToolCall`: Represents a request to execute a tool
- `ToolResponse`: Contains the result of a tool execution

Messages flow through the system in a consistent format, allowing agents to maintain conversation history and context.

## Tool Integration

Agents can access and execute tools through the tool registry:

1. Tools are registered with the tool registry
2. Agents retrieve tool definitions from the registry
3. LLM generates tool calls based on these definitions
4. Agents execute the tool calls and process the results

## Concurrency and Thread Safety

The Agent Framework is designed with concurrency in mind:

- Each agent instance maintains its own state
- Stateful operations are handled through atomic updates
- The framework uses async/await patterns throughout for non-blocking operations
- Context managers ensure proper resource acquisition and release

**Thread Safety Notes**:
- Agents are not thread-safe by default - each thread should use its own agent instance
- The tool registry is designed to be thread-safe for concurrent access
- Memory systems (like RollingWindowMemory) implement thread-safe operations

## Security Considerations

The EnhancedRadis agent includes several security features:

- Command history tracking to prevent repeated dangerous commands
- Identity context to ensure consistent agent behavior
- Response processing to sanitize potentially harmful outputs
- Security configuration to define operational boundaries

## Extension Points

The Agent Framework can be extended in several ways:

1. Creating new agent classes that inherit from BaseAgent
2. Adding new tools to be used by existing agents
3. Implementing custom response processors
4. Extending the identity context with new rules

## Related Components

The Agent Framework interacts closely with:

- **Memory System**: Provides persistence of conversation history
- **Tool Registry**: Manages available tools and their schemas
- **Context Manager**: Handles conversation contexts and sessions
- **Identity Framework**: Ensures consistent agent identity and behavior

## Future Directions

Planned enhancements to the Agent Framework include:

- Agent orchestration for multi-agent collaboration
- Enhanced security boundaries and monitoring
- Performance optimizations for large-scale deployments
- Additional agent types for specialized use cases

