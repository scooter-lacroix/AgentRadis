# RadisProject Documentation

```
 ____           _ _     ____            _           _   
|  _ \ __ _  __| (_)___|  _ \ _ __ ___ (_) ___  ___| |_ 
| |_) / _` |/ _` | / __| |_) | '__/ _ \| |/ _ \/ __| __|
|  _ < (_| | (_| | \__ \  __/| | | (_) | |  __/ (__| |_ 
|_| \_\__,_|\__,_|_|___/_|   |_|  \___// |\___|\___|\__|
                                      |__/               
 ____                                        _        _   _             
|  _ \  ___   ___ _   _ _ __ ___   ___ _ __ | |_ __ _| |_(_) ___  _ __  
| | | |/ _ \ / __| | | | '_ ` _ \ / _ \ '_ \| __/ _` | __| |/ _ \| '_ \ 
| |_| | (_) | (__| |_| | | | | | |  __/ | | | || (_| | |_| | (_) | | | |
|____/ \___/ \___|\__,_|_| |_| |_|\___|_| |_|\__\__,_|\__|_|\___/|_| |_|
```

Welcome to the RadisProject documentation. This guide provides comprehensive information about the design, architecture, and implementation of the RadisProject.

## Documentation Overview

This documentation is organized into several sections, each covering specific aspects of the RadisProject system:

### [System Architecture](./system_architecture/README.md)

```
+------------------------------------------+
|             RadisProject                 |
+------------------------------------------+
|                                          |
|  +-------------+      +--------------+   |
|  |    Agent    |<---->|     Core     |   |
|  | Framework   |      | Components   |   |
|  +-------------+      +--------------+   |
|         ^                    ^           |
|         |                    |           |
|         v                    v           |
|  +-------------+      +--------------+   |
|  |  Identity   |<---->|    Tool      |   |
|  | Framework   |      |   Registry   |   |
|  +-------------+      +--------------+   |
|                                          |
+------------------------------------------+
```

The System Architecture documentation provides a high-level overview of the entire RadisProject system, including:

- Component organization and interactions
- Data flow between modules
- Core architectural principles
- System-wide patterns and conventions

This section serves as a foundation for understanding how all the components work together to provide the RadisProject's functionality.

### [Agent Framework](./agent_framework/README.md)

```
    +----------------+
    |    User Input  |
    +-------+--------+
            |
            v
  +---------+----------+
  |  Agent Framework   |
  |                    |
  |  +-------------+   |     +-------------+
  |  |   Agent     |<--+---->|    LLM      |
  |  | Controller  |   |     | Integration |
  |  +-------------+   |     +-------------+
  |        ^           |
  |        |           |
  |        v           |
  |  +-------------+   |
  |  |  Response   |   |
  |  | Processor   |   |
  |  +-------------+   |
  |        ^           |
  +--------|----------+
           |
           v
    +------+---------+
    |  User Output   |
    +----------------+
```

The Agent Framework documentation details the intelligent agent system that powers RadisProject's capabilities:

- Agent design and implementation
- Conversation management
- LLM integration and interaction patterns
- Agent state management
- Response generation and processing

This section is essential for understanding how RadisProject processes user inputs and generates intelligent responses.

### [Core Components](./core_components/README.md)

```
                +----------------------+
                |   Core Components    |
                +-----------+----------+
                            |
          +----------------+ +-----------------+
          |                | |                 |
          v                v v                 v
+------------------+ +------------+ +--------------------+
| Context Manager  | |  Session   | | Rolling Window     |
|                  | |  Context   | | Memory             |
| +--------------+ | |            | |                    |
| | Context Map  | | | +--------+ | | +--------------+  |
| | thread-safe  |<--+>| State  | | | | Deque-based  |  |
| +--------------+ | | +--------+ | | | History      |  |
|                  | |            | | +--------------+  |
+------------------+ +------------+ +--------------------+
```

The Core Components documentation covers the fundamental building blocks of the RadisProject system:

- Context Manager: How conversation and session context is managed
- Session Context: Session lifecycle and state management
- Rolling Window Memory: How conversation history is maintained efficiently
- Memory management strategies and optimizations
- Concurrency handling and thread safety

This section provides insights into the critical infrastructure components that enable RadisProject to maintain state and context.

### [Tool Registry](./tool_registry/README.md)

```
          +---------------------+
          |    Tool Registry    |
          +---------+-----------+
                    |
        +-----------+-----------+
        |                       |
        v                       v
+---------------+      +------------------+
| Tool Registry |      |    Base Tool     |
|               |      |                  |
| +----------+  |      | +--------------+ |
| | register |  |      | | execute()    | |
| +----------+  |      | +--------------+ |
|               |      |                  |
| +----------+  |      | +--------------+ |
| | discover |  |      | | validate()   | |
| +----------+  |      | +--------------+ |
|               |      |                  |
| +----------+  |      | +--------------+ |
| | metrics  |  |      | | metrics()    | |
| +----------+  |      | +--------------+ |
+---------------+      +------------------+
        ^                       ^
        |                       |
        +-----------+-----------+
                    |
          +---------+---------+
          |  Custom Tools     |
          +-------------------+
```

The Tool Registry documentation explains the extensible tool system that allows RadisProject to perform actions:

- Tool registration and discovery mechanisms
- BaseTool implementation and extension patterns
- Tool execution flow
- Tool validation and security considerations
- Metrics tracking and performance monitoring
- Creating custom tools

This section is crucial for understanding how to extend RadisProject with new capabilities.

### [Identity Framework](./identity_framework/README.md)

```
              +-------------------+
              | Identity Framework |
              +--------+----------+
                       |
         +-------------+-------------+
         |                           |
         v                           v
+------------------+      +----------------------+
| Identity Context |      | Response Processor   |
|                  |      |                      |
| +------------+   |      | +------------------+ |
| | Rules      |<--+----->| | Regex Patterns   | |
| +------------+   |      | +------------------+ |
|                  |      |                      |
| +------------+   |      | +------------------+ |
| | Validation |   |      | | Sanitization     | |
| +------------+   |      | +------------------+ |
|                  |      |                      |
| +------------+   |      | +------------------+ |
| | Persistence|   |      | | Command History  | |
| +------------+   |      | +------------------+ |
+------------------+      +----------------------+
```

The Identity Framework documentation describes the security and identity management systems:

- [LLM Configuration](./llm_configuration.md)

- Identity context and principles
- Response processing and sanitization
- Identity rules and enforcement mechanisms
- Model name sanitization
- Command execution tracking
- Security considerations and best practices

This section covers how RadisProject maintains consistent identity and implements security guardrails.

## Getting Started

```
   START
     |
     v
+----+----+
| System  |
| Arch    +-----+
+---------+     |
                |
     +----------+
     |
     v
+----+----+    +----+----+    +----+----+
| Agent   |    | Core    |    | Tool    |
| Framework+--->Components+--->Registry |
+---------+    +---------+    +---------+
                                  |
     +----------------------------+
     |
     v
+----+----+    +----+----+
| Identity |    | Extend  |
| Framework+--->& Develop |
+---------+    +---------+
                    |
                    v
                   END
```

To get started with RadisProject, we recommend first reading the [System Architecture](./system_architecture/README.md) overview to understand the big picture, then diving into specific components based on your areas of interest.

For developers looking to extend or modify RadisProject, the [Tool Registry](./tool_registry/README.md) documentation is an excellent starting point for understanding how to add new capabilities.

## Additional Resources

- The main [README.md](../README.md) at the project root provides setup and configuration information
- Each documentation section includes references to the relevant source code
- Code examples are provided throughout to illustrate key concepts
