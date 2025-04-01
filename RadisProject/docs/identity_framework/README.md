# Identity & Security Framework

The Identity & Security Framework is a crucial component of the RadisProject that ensures consistent identity presentation, proper security handling, and prevents information leakage through responses. This framework manages how the agent represents itself and processes responses to maintain security boundaries.

## Overview

The Identity & Security Framework consists of two main components:

1. **RadisIdentityContext** - Manages the identity and persona of the agent
2. **ResponseProcessor** - Processes and sanitizes responses before they are returned to users

Together, these components create a robust security layer that maintains consistent agent identity while preventing disclosure of sensitive information.

## Architecture

```
┌───────────────────────────────┐
│                               │
│    RadisIdentityContext       │
│                               │
│  ┌─────────────────────────┐  │
│  │ Identity Rules          │  │
│  │ - Tool names            │  │
│  │ - Agent name            │─────────┐
│  │ - Model references      │  │      │
│  └─────────────────────────┘  │      │
│                               │      │
└───────────────────────────────┘      │
                                       │
                                       ▼
┌───────────────────────────────┐      
│                               │      
│    ResponseProcessor          │◄─────┐
│                               │      │
│  ┌─────────────────────────┐  │      │
│  │ Sanitization Rules      │  │      │
│  │ - Regex replacements    │  │      │
│  │ - Identity enforcement  │  │      │
│  │ - Security filters      │  │      │
│  └─────────────────────────┘  │      │
│                               │      │
└───────────┬───────────────────┘      │
            │                          │
            ▼                          │
┌───────────────────────────────┐      │
│                               │      │
│    Sanitized Response         │      │
│    to User                    │      │
│                               │      │
└───────────────────────────────┘      
```

## Key Components

### RadisIdentityContext

#### Purpose

The RadisIdentityContext class establishes and maintains the identity rules for the Radis Agent. It ensures consistent presentation of the agent's identity and prevents model hallucinations or incorrect self-references.

#### Key Classes and Methods

**RadisIdentityContext**

```python
class RadisIdentityContext:
    def __init__(self, model_name: str = None, sanitize_model_names=True):
        # Initializes the identity context with model name and sanitization settings
```

Key Methods:
- `get_identity_rules()`: Returns the current set of identity rules
- `get_agent_name()`: Returns the standardized agent name
- `format_model_name(model_name)`: Sanitizes and formats model names to prevent sensitive information disclosure
- `identity_matches(text)`: Checks if the given text matches the agent's identity
- `apply_identity_rules(content)`: Applies all identity rules to the content

#### Usage Example

```python
# Create an identity context
identity_context = RadisIdentityContext(model_name="gpt-4")

# Get identity rules
rules = identity_context.get_identity_rules()

# Get the agent name
agent_name = identity_context.get_agent_name()

# Apply identity rules to content
sanitized_content = identity_context.apply_identity_rules(raw_content)
```

### ResponseProcessor

#### Purpose

The ResponseProcessor handles the sanitization and processing of responses from the LLM before they are presented to users. It ensures that responses maintain identity consistency, removes sensitive information, and applies security filters.

#### Key Classes and Methods

**ResponseProcessor**

```python
class ResponseProcessor:
    def __init__(self, identity_context: RadisIdentityContext):
        # Initializes the processor with an identity context
```

Key Methods:
- `process_response(response)`: Processes and sanitizes a response
- `apply_regex_replacements(text)`: Applies configured regex replacements to the text
- `filter_sensitive_content(text)`: Removes sensitive information from the text
- `sanitize_command_references(text)`: Sanitizes references to commands in the text
- `enforce_identity(text)`: Ensures the text adheres to the agent's identity

#### Usage Example

```python
# Create an identity context
identity_context = RadisIdentityContext(model_name="gpt-4")

# Create a response processor
processor = ResponseProcessor(identity_context)

# Process a response
raw_response = "I am a language model built by OpenAI. I can execute tools like execute_command."
processed_response = processor.process_response(raw_response)
# Result: "I am an AI assistant. I can help you with your tasks."
```

## Security Considerations

### Identity Protection

The Identity & Security Framework implements several security measures:

1. **Model Name Sanitization**: Prevents disclosure of specific model names, versions, or internal identifiers.
2. **Tool Reference Sanitization**: Ensures tool names are consistently referenced and prevents disclosure of implementation details.
3. **Agent Identity Enforcement**: Maintains a consistent identity for the agent, preventing confusing or contradictory self-references.

### Regex-Based Sanitization

The ResponseProcessor uses regex patterns to identify and replace sensitive information:

```python
# Example regex pattern (simplified)
TOOL_NAME_PATTERN = r'(execute_command|read_file|write_to_file)'
MODEL_NAME_PATTERN = r'(GPT-\d|LLaMA|Claude)'
```

These patterns help identify problematic content that needs to be sanitized.

### Command History Tracking

The framework tracks command execution history to ensure proper references to previous commands and prevent disclosure of sensitive command parameters. This includes:

1. Storage of safe command representations
2. Reference management for multi-command sequences
3. Sanitization of directory paths and user identifiers

## Integration with Other Components

The Identity & Security Framework integrates with other RadisProject components:

- **Agent Framework**: Provides identity context for agent responses
- **Tool Registry**: Sanitizes tool references and enforces proper tool usage
- **Context Management**: Ensures identity consistency across multiple interactions

## Best Practices

When working with the Identity & Security Framework:

1. Always initialize a RadisIdentityContext before processing responses
2. Use the ResponseProcessor for all user-facing output
3. Regularly review and update regex patterns to catch new forms of sensitive information
4. Implement comprehensive testing for sanitization rules
5. Consider the trade-off between security and transparency in your configurations

## Extending the Framework

The Identity & Security Framework can be extended to add new security features:

```python
# Example of extending the ResponseProcessor
class EnhancedResponseProcessor(ResponseProcessor):
    def __init__(self, identity_context, additional_rules=None):
        super().__init__(identity_context)
        self.additional_rules = additional_rules or []
    
    def process_response(self, response):
        # Apply parent processing
        processed = super().process_response(response)
        
        # Apply additional rules
        for rule in self.additional_rules:
            processed = rule.apply(processed)
            
        return processed
```

## Conclusion

The Identity & Security Framework plays a vital role in maintaining the security and consistency of the RadisProject. By properly managing identity and sanitizing responses, it ensures a secure and reliable user experience while preventing potential information leakage or inconsistent agent behavior.

# Identity Framework

## Overview

The Identity Framework is a comprehensive system designed to maintain consistent agent identity throughout interactions with users. It provides robust mechanisms for identity management, response processing, and security enforcement within the RadisProject ecosystem.

## Key Components

1. **RadisIdentityContext** - Manages identity context information, tracks command history, and enforces project boundaries.
2. **ResponseProcessor** - Sanitizes responses to maintain consistent identity and prevent unintended disclosures.
3. **Security Boundaries** - Enforces workspace and execution boundaries to ensure secure operation.

## Why Use the Identity Framework?

- **Consistent Identity**: Ensures AI agent maintains a consistent identity (Radis) throughout interactions
- **Security**: Prevents unauthorized file access and operations outside project boundaries
- **Transparency**: Tracks command history and execution context for debugging and audit
- **Flexibility**: Easily integrates with existing tools and workflows

## Getting Started

```python
from app.agent.identity_context import RadisIdentityContext
from app.agent.response_processor import ResponseProcessor

# Initialize the identity context
identity_context = RadisIdentityContext(workspace_root="/path/to/project")

# Initialize the response processor
response_processor = ResponseProcessor()

# Process a response to ensure consistent identity
sanitized_response = response_processor.process_response(
    "I am an assistant powered by GPT-4 and I can help you.",
    identity_context
)
# Result: "I am an assistant powered by Radis and I can help you."
```

## Documentation

- [Identity Context](./IDENTITY_CONTEXT.md) - Detailed documentation on identity management
- [Response Processor](./RESPONSE_PROCESSOR.md) - Information about response processing
- [Security](./SECURITY.md) - Security boundary enforcement details
- [Usage](./USAGE.md) - Examples and usage guidelines

## Integration

The Identity Framework is designed to integrate seamlessly with the EnhancedRadis agent:

```python
from app.agent.enhanced_radis import EnhancedRadis

# Create an enhanced Radis instance with identity framework enabled
agent = EnhancedRadis(
    model="gpt-4",
    enable_identity_framework=True,
    workspace_root="/path/to/project"
)

# The agent will automatically use the identity framework for all interactions
response = agent.run("Tell me about yourself")
# Response will be sanitized to maintain consistent identity
```

## Contributing

Contributions to the Identity Framework are welcome. Please ensure all tests pass before submitting pull requests:

```bash
# Run unit tests
pytest tests/agent/test_identity_context.py
pytest tests/agent/test_response_processor.py

# Run integration tests
pytest tests/integration/test_identity_sanitization_integration.py
```

# Identity Framework

The Identity Framework provides a robust system for managing agent identity, processing responses, enforcing security boundaries, and handling errors in the Radis system.

## Core Components

1. **Identity Management**
   - Identity context tracking
   - Command history maintenance
   - Project boundary enforcement
   - Identity rule validation

2. **Response Processing**
   - Model name detection and sanitization
   - Path validation and security
   - Response content filtering
   - Identity consistency checks

3. **Security Boundaries**
   - Working directory restrictions
   - File access controls
   - Tool execution boundaries
   - Project scope enforcement

4. **Tool Execution**
   - Command validation
   - Resource cleanup
   - Security checks
   - Output sanitization

5. **Error Handling**
   - Specialized error types
   - Graceful fallbacks
   - User-friendly messages
   - Comprehensive logging

## Getting Started

See the following documents for detailed information:
- [Identity Management](IDENTITY.md)
- [Response Processing](RESPONSE_PROCESSING.md)
- [Security](SECURITY.md)
- [Tools](TOOLS.md)
- [Errors](ERRORS.md)

## Architecture

The framework is built on several key classes:
- `RadisIdentityContext`: Manages identity and command history
- `ResponseProcessor`: Handles response sanitization and validation
- `EnhancedRadis`: Implements security and tool management
- Custom error classes for specialized error handling

