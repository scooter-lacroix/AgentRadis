# Response Processor

The `ResponseProcessor` class is a critical component of the Identity Framework that ensures consistent identity representation in all agent responses.

## Overview

The Response Processor provides:
- Model name detection and replacement
- Path validation and sanitization
- Security boundary enforcement
- Content sanitization for sensitive information

## Core Components

### ModelNameDetector

The `ModelNameDetector` class uses regex patterns to identify and replace references to known AI models:

```python
from app.agent.response_processor import ModelNameDetector

detector = ModelNameDetector()

# Detect and replace model references
sanitized = detector.replace_model_references(
    "I am powered by GPT-4 and using OpenAI technology."
)
# Result: "I am powered by Radis and using Radis technology."
```

The detector includes patterns for common AI models:
- GPT models (GPT-3, GPT-4, etc.)
- Claude models
- LLaMA models
- Other common AI references

### PathValidator

The `PathValidator` class ensures all file paths in responses are safe and within project boundaries:

```python
from app.agent.response_processor import PathValidator

validator = PathValidator(workspace_root="/path/to/project")

# Validate a path
try:
    safe_path = validator.validate_path("/path/to/project/data.txt")
    # Returns normalized path if valid
except SecurityBoundaryError:
    # Handles paths outside project boundary
```

### ResponseProcessor

The main `ResponseProcessor` class combines model detection and path validation:

```python
from app.agent.response_processor import ResponseProcessor
from app.agent.identity_context import RadisIdentityContext

# Create identity context
identity_context = RadisIdentityContext(workspace_root="/path/to/project")

# Create response processor
processor = ResponseProcessor()

# Process a response
original_response = """
I'm an AI assistant based on GPT-4. I can help you access files like
/etc/passwd or /home/user/secret.txt.
"""

sanitized_response = processor.process_response(
    original_response, 
    identity_context
)

# Result will replace GPT-4 with Radis and sanitize unsafe paths
```

## Processing Pipeline

The ResponseProcessor uses a multi-stage pipeline:

1. **Pre-processing**: Prepares the response for sanitization
2. **Model Name Detection**: Identifies and replaces model references
3. **Path Validation**: Ensures all file paths are safe
4. **Identity Rule Enforcement**: Applies identity rules
5. **Post-processing**: Final cleanup and formatting

## Handling Complex Responses

The processor can handle various response formats:

### String Responses

```python
sanitized = processor.process_response(
    "I am GPT-4, an AI model developed by OpenAI.",
    identity_context
)
```

### Dictionary Responses

```python
response_dict = {
    "answer": "I am GPT-4, an AI assistant.",
    "files": ["/path/to/project/data.txt", "/etc/passwd"],
    "metadata": {"model": "gpt-4-turbo"}
}

sanitized_dict = processor.process_dict_response(
    response_dict,
    identity_context
)
```

### JSON Responses

```python
json_response = '{"model": "GPT-4", "response": "I can help with that."}'
sanitized_json = processor.process_json_response(
    json_response,
    identity_context
)
```

## Integration with EnhancedRadis

```python
from app.agent.enhanced_radis import EnhancedRadis
from app.agent.response_processor import ResponseProcessor

# Create processor
processor = ResponseProcessor()

# Create Radis agent with processor
agent = EnhancedRadis(
    model="gpt-4",
    response_processor=processor
)

# All responses will be automatically sanitized
```

## Best Practices

1. **Always Process Responses**: Never return raw model responses to users
2. **Use with Identity Context**: Always provide identity context for full security
3. **Handle Failures Gracefully**: Implement proper error handling for sanitization failures
4. **Customize for Specific Needs**: Extend with custom patterns for specific use cases
5. **Monitor and Log**: Track sanitization operations for security auditing

## Advanced Configuration

```python
# Custom configuration
processor = ResponseProcessor(
    extra_model_patterns=[r"Your-Custom-Model-\d+"],
    identity_replacement="CustomAgentName",
    strict_mode=True,  # Fail on any unhandled references
    max_recursion_depth=3  # For nested content
)
```

## Testing

Comprehensive tests for the Response Processor are available in:
```
tests/agent/test_response_processor.py
tests/integration/test_identity_sanitization_integration.py
```

