# Core Components

This document provides detailed information about the core components of the RadisProject, which are responsible for managing context, session state, and memory.

## Table of Contents
- [Overview](#overview)
- [Context Manager](#context-manager)
- [Session Context](#session-context)
- [Rolling Window Memory](#rolling-window-memory)
- [Concurrency Considerations](#concurrency-considerations)
- [Integration Patterns](#integration-patterns)

## Overview

The Core Components form the foundation of RadisProject's context and memory management system. These components work together to maintain the state of conversations, manage the flow of information between different parts of the system, and ensure that agents have access to relevant historical data while remaining performant.

```
┌─────────────────┐     ┌─────────────────┐      ┌─────────────────┐
│  Context Manager│◄────┤ Session Context  │◄────┤Rolling Window   │
│                 │     │                  │     │Memory           │
└────────┬────────┘     └────────┬─────────┘     └─────────────────┘
         │                       │                       ▲
         ▼                       ▼                       │
┌─────────────────┐     ┌─────────────────┐              │
│ Agent Framework │◄────┤  Tool Registry  │──────────────┘
└─────────────────┘     └─────────────────┘
```

## Context Manager

### Purpose

The Context Manager is responsible for creating, retrieving, and managing session contexts across the application. It serves as the central registry for all active contexts and provides thread-safe access to these contexts.

### Key Classes

#### `ContextManager`

The primary class responsible for managing context instances.

```python
class ContextManager:
    def __init__(self, expiry_time=3600):
        self._contexts = {}
        self._lock = threading.RLock()
        self._expiry_time = expiry_time
```

### Methods

#### `get_context(session_id)`

Retrieves an existing context or creates a new one if not found.

**Parameters:**
- `session_id`: Unique identifier for the session

**Returns:**
- `SessionContext`: The context associated with the session

**Usage Example:**
```python
context_manager = ContextManager()
session_context = context_manager.get_context("user_session_123")
```

#### `create_context(session_id, metadata=None)`

Creates a new context for a session.

**Parameters:**
- `session_id`: Unique identifier for the session
- `metadata`: Optional dictionary of metadata to associate with the context

**Returns:**
- `SessionContext`: The newly created context

**Usage Example:**
```python
context_manager = ContextManager()
metadata = {"user_id": "user_123", "start_time": time.time()}
session_context = context_manager.create_context("user_session_123", metadata)
```

#### `remove_context(session_id)`

Removes a context from the manager.

**Parameters:**
- `session_id`: Unique identifier for the session

**Returns:**
- `bool`: True if the context was successfully removed, False otherwise

**Usage Example:**
```python
context_manager = ContextManager()
success = context_manager.remove_context("user_session_123")
```

#### `clean_expired_contexts()`

Removes all contexts that have expired based on the expiry time.

**Usage Example:**
```python
context_manager = ContextManager(expiry_time=1800)  # 30 minutes
context_manager.clean_expired_contexts()
```

## Session Context

### Purpose

The Session Context represents the state of a single user session and maintains the conversation history, user preferences, and other session-specific information.

### Key Classes

#### `SessionContext`

The primary class that holds the state for a specific user session.

```python
class SessionContext:
    def __init__(self, session_id, metadata=None):
        self.session_id = session_id
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.metadata = metadata or {}
        self.memory = RollingWindowMemory(max_size=100)
        self._lock = threading.RLock()
```

### Methods

#### `add_message(role, content)`

Adds a message to the session context memory.

**Parameters:**
- `role`: The role of the message sender (e.g., "user", "assistant")
- `content`: The content of the message

**Returns:**
- None

**Usage Example:**
```python
session_context = SessionContext("user_session_123")
session_context.add_message("user", "Hello, how can I help you today?")
session_context.add_message("assistant", "I'm here to assist you with any questions you have about the RadisProject.")
```

#### `get_history(max_messages=None)`

Retrieves the conversation history from the session.

**Parameters:**
- `max_messages`: Maximum number of messages to retrieve (default: all messages)

**Returns:**
- `list`: A list of message dictionaries containing role and content

**Usage Example:**
```python
session_context = SessionContext("user_session_123")
# Add some messages
history = session_context.get_history(max_messages=10)
```

#### `update_metadata(key, value)`

Updates the metadata associated with the session.

**Parameters:**
- `key`: The metadata key to update
- `value`: The new value for the metadata key

**Returns:**
- None

**Usage Example:**
```python
session_context = SessionContext("user_session_123")
session_context.update_metadata("last_topic", "documentation")
```

#### `is_expired(expiry_time)`

Checks if the session has expired based on the given expiry time.

**Parameters:**
- `expiry_time`: The maximum time in seconds since the last access

**Returns:**
- `bool`: True if the session has expired, False otherwise

**Usage Example:**
```python
session_context = SessionContext("user_session_123")
if session_context.is_expired(3600):
    # Handle expired session
```

## Rolling Window Memory

### Purpose

The Rolling Window Memory provides an efficient way to store and retrieve conversation history while maintaining a fixed size window. It automatically removes older messages when the maximum size is reached.

### Key Classes

#### `RollingWindowMemory`

The primary class that implements a thread-safe, fixed-size memory structure.

```python
class RollingWindowMemory:
    def __init__(self, max_size=100):
        self._messages = collections.deque(maxlen=max_size)
        self._lock = threading.RLock()
```

### Methods

#### `add(message)`

Adds a message to the memory.

**Parameters:**
- `message`: The message to add (typically a dictionary with role and content)

**Returns:**
- None

**Usage Example:**
```python
memory = RollingWindowMemory(max_size=50)
memory.add({"role": "user", "content": "How does the Context Manager work?"})
```

#### `get_all()`

Retrieves all messages from the memory.

**Returns:**
- `list`: A list of all messages in the memory

**Usage Example:**
```python
memory = RollingWindowMemory()
all_messages = memory.get_all()
```

#### `get_last(n)`

Retrieves the last n messages from the memory.

**Parameters:**
- `n`: The number of messages to retrieve

**Returns:**
- `list`: A list of the last n messages

**Usage Example:**
```python
memory = RollingWindowMemory()
recent_messages = memory.get_last(5)
```

#### `clear()`

Clears all messages from the memory.

**Returns:**
- None

**Usage Example:**
```python
memory = RollingWindowMemory()
memory.clear()
```

## Concurrency Considerations

The Core Components of RadisProject are designed to be thread-safe and support concurrent access. Here are the key concurrency mechanisms used:

### Thread Safety

- All core components use `threading.RLock` to ensure thread-safe access to shared resources.
- The Context Manager uses a lock to protect the contexts dictionary from concurrent modification.
- Session Context uses a lock to protect its state during updates.
- Rolling Window Memory uses a lock to protect the message deque during additions and retrievals.

### Example of Thread-Safe Operation

```python
def process_user_message(user_id, message_content):
    # Safely get context even if multiple threads access this function
    with context_manager._lock:
        context = context_manager.get_context(user_id)
    
    # Safely update the context
    with context._lock:
        context.add_message("user", message_content)
        context.update_metadata("last_message_time", time.time())
    
    # Process the message and generate a response
    response = generate_response(context)
    
    # Safely update the context again
    with context._lock:
        context.add_message("assistant", response)
    
    return response
```

### Preventing Deadlocks

- The Core Components are designed to minimize the potential for deadlocks by:
  - Using RLock instead of Lock to allow re-entrant locking
  - Keeping critical sections small
  - Maintaining a consistent lock acquisition order

## Integration Patterns

### Integrating with the Agent Framework

```python
def handle_request(session_id, user_input):
    # Get or create the session context
    context = context_manager.get_context(session_id)
    
    # Add the user message to context
    context.add_message("user", user_input)
    
    # Create an agent with this context
    agent = RadisAgent(session_context=context)
    
    # Process the request
    response = agent.process(user_input)
    
    # Add the agent response to context
    context.add_message("assistant", response)
    
    return response
```

### Integrating with the Tool Registry

```python
def execute_tool(session_id, tool_name, tool_params):
    # Get the session context
    context = context_manager.get_context(session_id)
    
    # Get the tool from the registry
    tool = tool_registry.get_tool(tool_name)
    
    # Execute the tool with context awareness
    result = tool.execute(params=tool_params, context=context)
    
    # Update context with the tool execution result
    context.add_message("system", f"Executed tool {tool_name} with result: {result}")
    
    return result
```

### Periodic Maintenance

```python
def maintenance_job():
    """Run periodically to clean up expired contexts"""
    while True:
        context_manager.clean_expired_contexts()
        time.sleep(300)  # Run every 5 minutes

# Start the maintenance job in a separate thread
maintenance_thread = threading.Thread(target=maintenance_job, daemon=True)
maintenance_thread.start()
```

