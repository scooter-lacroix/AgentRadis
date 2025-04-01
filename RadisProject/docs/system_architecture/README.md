# RadisProject System Architecture

This document provides a comprehensive overview of RadisProject's architecture, detailing each high-level component and explaining the data flow between modules.

## Overview

RadisProject is designed as a modular system that enables intelligent agent interactions through a flexible framework. The architecture emphasizes:

- **Modularity**: Components can be developed and enhanced independently
- **Extensibility**: New tools and capabilities can be added with minimal changes
- **Security**: Identity management and security controls are embedded throughout
- **Context Management**: Advanced memory and context handling for coherent interactions

## System Components

```
┌───────────────────────────────────────────────────────────────┐
│                      RadisProject System                      │
├───────────────┬───────────────┬───────────────┬───────────────┤
│  Agent        │   Core        │  Identity &   │   Tool        │
│  Framework    │   Components  │  Security     │   Registry    │
├───────────────┼───────────────┼───────────────┼───────────────┤
│ ┌───────────┐ │ ┌───────────┐ │ ┌───────────┐ │ ┌───────────┐ │
│ │RadisAgent │ │ │Context    │ │ │Identity   │ │ │Tool       │ │
│ │           │ │ │Manager    │ │ │Context    │ │ │Registry   │ │
│ └───────────┘ │ └───────────┘ │ └───────────┘ │ └───────────┘ │
│ ┌───────────┐ │ ┌───────────┐ │ ┌───────────┐ │ ┌───────────┐ │
│ │Agent      │ │ │Session    │ │ │Response   │ │ │Base       │ │
│ │Interface  │ │ │Context    │ │ │Processor  │ │ │Tool       │ │
│ └───────────┘ │ └───────────┘ │ └───────────┘ │ └───────────┘ │
│               │ ┌───────────┐ │               │ ┌───────────┐ │
│               │ │Rolling    │ │               │ │Tool       │ │
│               │ │Window     │ │               │ │Metrics    │ │
│               │ │Memory     │ │               │ │           │ │
│               │ └───────────┘ │               │ └───────────┘ │
└───────────────┴───────────────┴───────────────┴───────────────┘
```

## Agent Framework

The Agent Framework is the core of RadisProject, orchestrating interactions between users, tools, and LLM backends.

### Key Components

- **RadisAgent**: The primary agent class that coordinates all interactions, manages context, and executes the reasoning-action loop.
  
- **Agent Interface**: Defines the contract that all agent implementations must follow, providing methods for processing requests, managing state, and generating responses.

### Data Flow

1. User input enters the system through the RadisAgent
2. The agent enriches the input with context from memory systems
3. The enhanced prompt is sent to the LLM backend for reasoning
4. The agent interprets the response and executes appropriate actions
5. Results are processed and returned to the user, with context updated

## Core Components

These components provide essential functionality that supports agent operations.

### Key Components

- **ContextManager**: Maintains and manages different context objects throughout the system, ensuring appropriate context is available to the agent at the right time.

- **SessionContext**: Represents the current state of a user session, including history, preferences, and active tools.

- **RollingWindowMemory**: Implements a thread-safe, size-limited memory system that maintains a sliding window of recent interactions.

### Data Flow

1. User interactions are captured and stored in SessionContext
2. RollingWindowMemory maintains conversations within defined constraints
3. ContextManager ensures the appropriate context is injected into each prompt
4. As new interactions occur, older context is gradually rotated out based on relevance and limits

## Identity & Security

The Identity & Security framework ensures appropriate boundaries, consistent identity, and secure operation.

### Key Components

- **Identity Context**: Manages the agent's identity, personality, and behavioral constraints.

- **Response Processor**: Filters and processes LLM outputs to ensure compliance with identity rules and security policies.

### Data Flow

1. Identity rules are established and maintained in the Identity Context
2. All outputs from the LLM are checked against identity constraints
3. Response Processor applies regex checks and replacements to ensure consistent identity
4. Command execution is tracked and validated against security policies
5. Model names and references are sanitized before being presented to users

## Tool Registry

The Tool Registry enables extensible functionality through a plugin architecture.

### Key Components

- **ToolRegistry**: Central registry that maintains available tools, their metadata, and access control.

- **BaseTool**: Abstract base class that defines the interface for all tools in the system.

- **Tool Metrics**: Monitors and records tool usage, performance, and errors.

### Data Flow

1. Tools are registered with the ToolRegistry during initialization
2. The Agent requests available tools from the registry based on the current context
3. When tool execution is needed, the agent requests the tool from the registry
4. Tool execution is monitored and metrics are collected
5. Results are returned to the agent for incorporation into the context

## Cross-Component Data Flow

The system operates through several key data flows that span multiple components:

### Context Flow

```
User Input → RadisAgent → ContextManager → SessionContext → LLM Prompt
```

The context flow ensures that conversational history, system state, and user-specific information are properly maintained and available.

### Tool Execution Cycle

```
Agent → ToolRegistry → Tool Instance → Execution → Metrics Collection → Results → Agent
```

The tool execution cycle enables the agent to perform actions in the environment by locating, invoking, and processing results from appropriate tools.

### LLM Interaction

```
Enriched Prompt → LLM Backend → Raw Response → Response Processor → Filtered Response → Agent → User
```

The LLM interaction flow manages the communication with language model backends, ensuring appropriate context is provided and responses are properly processed before being delivered to users.

### Memory Management

```
Interactions → RollingWindowMemory → Context Selection → Prompt Construction
```

The memory management flow governs how information is retained, prioritized, and incorporated into future interactions.

## Concurrency and Thread Safety

RadisProject implements several strategies to ensure thread-safe operation:

- **Locks**: Carefully placed locks ensure that critical sections are accessed by only one thread at a time
- **Thread-Safe Collections**: Components like RollingWindowMemory use thread-safe collections (deques) to prevent concurrency issues
- **Immutable Patterns**: Where possible, immutable data structures are used to prevent unintended modifications

## Extension and Customization

RadisProject is designed for extension through:

- **Custom Tools**: New functionality can be added by creating classes that inherit from BaseTool
- **Identity Rules**: The identity framework can be extended with new rules and constraints
- **Memory Strategies**: Custom memory implementations can be created to support specific use cases
- **LLM Backends**: The system supports multiple LLM providers through a consistent interface

## Next Steps

This architecture overview provides a high-level understanding of the RadisProject system. For more detailed information on each component, please refer to the component-specific documentation:

- [Agent Framework](../agent_framework/README.md)
- [Core Components](../core_components/README.md)
- [Identity & Security Framework](../identity_framework/README.md)
- [Tool Registry](../tool_registry/README.md)

