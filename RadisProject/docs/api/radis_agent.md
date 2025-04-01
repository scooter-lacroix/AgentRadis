# RadisAgent

`RadisAgent` is the central class in the RadisProject framework that coordinates all system operations.

## Overview

The RadisAgent class provides the main interface for creating and using AI agents. It manages conversation flow, coordinates with LLM providers, executes tools, and maintains context.

## Class Definition

```python
class RadisAgent:
    """
    Central agent class for the RadisProject framework.
    
    RadisAgent orchestrates the interaction between various components including
    LLM providers, tools, context management, and response processing.
    
    Attributes:
        config: The agent configuration
        conversation_manager: Manages conversation history
        context_manager: Manages agent context and state
        tool_registry: Registry of available tools
        identity_context: Controls agent identity
        response_processor: Processes and sanitizes responses
        llm_provider: Interface to the language model
    """
```

## Constructor

```python
def __init__(
    self, 
    config=None, 
    llm_config=None, 
    agent_config=None, 
    tools_config=None, 
    memory_config=None, 
    hardware_config=None, 
    logging_config=None, 
    advanced_config=None,
    session_id=None
):
    """
    Initialize a new RadisAgent.
    
    Args:
        config: Complete configuration object (alternative to individual configs)
        llm_config: Configuration for the LLM provider
        agent_config: Configuration for agent identity and behavior
        tools_config: Configuration for the tool system
        memory_config: Configuration for memory and context management
        hardware_config: Configuration for hardware acceleration
        logging_config: Configuration for logging and observability
        advanced_config: Advanced configuration options
        session_id: Optional session ID for context persistence
        
    Raises:
        ConfigurationError: If the configuration is invalid
        InitializationError: If component initialization fails
    """
```

## Key Methods

### Running the Agent

```python
def run(self, input_text, session_id=None):
    """
    Run the agent with the given input text.
    
    This is the main method for interacting with the agent. It processes
    the input, generates a response, and returns the result.
    
    Args:
        input_text: The user input text
        session_id: Optional session ID to use (overrides the session_id set at initialization)
        
    Returns:
        AgentResponse: The agent's response including content and metadata
        
    Raises:
        AgentError: If an error occurs during processing
    """
```

### Tool Management

```python
def register_tool(self, tool):
    """
    Register a tool with the agent.
    
    Args:
        tool: The tool instance to register
        
    Returns:
        bool: True if registration was successful
        
    Raises:
        ToolRegistrationError: If the tool cannot be registered
    """
    
def register_default_tools(self):
    """
    Register all default tools with the agent.
    
    Returns:
        list: Names of registered tools
    """
    
def has_tool(self, tool_name):
    """
    Check if a tool is registered with the agent.
    
    Args:
        tool_name: The name of the tool to check
        
    Returns:
        bool: True if the tool is registered
    """
    
def list_tools(self):
    """
    List all tools registered with the agent.
    
    Returns:
        list: Names of all registered tools
    """
```

### Session Management

```python
def save_session(self, session_id=None):
    """
    Save the current session state.
    
    Args:
        session_id: Optional session ID to use (overrides the current session)
        
    Returns:
        str: The session ID used
    """
    
def load_session(self, session_id):
    """
    Load a saved session state.
    
    Args:
        session_id: The session ID to load
        
    Returns:
        bool: True if session was loaded successfully
        
    Raises:
        SessionNotFoundError: If the session cannot be found
    """
    
def reset(self):
    """
    Reset the agent state.
    
    Returns:
        bool: True if reset was successful
    """
```

### Configuration

```python
def update_config(self, config_updates):
    """
    Update the agent configuration.
    
    Args:
        config_updates: Dictionary of configuration updates
        
    Returns:
        bool: True if update was successful
        
    Raises:
        ConfigurationError: If the updated configuration is invalid
    """
```

## Examples

### Basic Usage

```python
from radis import RadisAgent

# Initialize the agent
agent = RadisAgent(
    llm_config={
        "provider": "openai",
        "model_name": "gpt-4-turbo",
        "api_key": "your-api-key" 
    }
)

# Run the agent with a prompt
response = agent.run("Hello! Can you help me with a Python question?")
print(response.content)
```

### Using Tools

```python
from radis import RadisAgent
from radis.tools import FileSystemTool, CalculatorTool

agent = RadisAgent(llm_config={...})

# Register tools
agent.register_tool(FileSystemTool())
agent.register_tool(CalculatorTool())

# Use tools in a query
response = agent.run("List files in the current directory and calculate their total size.")
print(response.content)
```

### Session Management

```python
from radis import RadisAgent

agent = RadisAgent(llm_config={...})

# First interaction
response1 = agent.run("What's the capital of France?")

# Save the session
session_id = agent.save_session()

# Create a new agent instance and load the session
new_agent = RadisAgent(llm_config={...})
new_agent.load_session(session_id)

# Continue the conversation
response2 = new_agent.run("What's the population of that city?")
```

## See Also

- [Configuration](configuration.md)
- [Tool System](tool_system.md)
- [Context Management](context_management.md)
