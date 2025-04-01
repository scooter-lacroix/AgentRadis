# LM Studio Integration Guide

This guide explains how to properly integrate with the LM Studio API using the Radis system.

## Using the GenerateParams Class

The `GenerateParams` class provides a structured way to pass parameters to the LM Studio API. It replaces direct dictionary usage, improves error handling, and ensures consistent parameter formatting.

### Basic Usage

```python
from app.schema.lmstudio_params import GenerateParams
import lmstudio

# Initialize client
client = lmstudio.Client(api_host="http://127.0.0.1:1234")
llm = client.llm

# Create GenerateParams object
generate_params = GenerateParams(
    prompt="Hello, world!",
    max_tokens=100,
    temperature=0.7
)

# Convert to dict and send
params_dict = generate_params.to_dict()
result = llm.remote_call("completions/generate", params_dict)
```

### Error Handling

Always wrap remote_call in a try/except block and implement a fallback:

```python
try:
    generate_params = GenerateParams(prompt="Hello, world!")
    result = llm.remote_call("completions/generate", generate_params.to_dict())
except Exception as e:
    logger.error(f"Error in remote_call: {e}")
    # Fallback to OpenAI-compatible API
    # [fallback implementation]
```

### Server Connectivity Check

Before making API calls, check if the server is running:

```python
def check_server_connection(host="127.0.0.1", port=1234, timeout=3):
    """Check if the LM Studio server is running and accessible."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

server_available = check_server_connection()
if not server_available:
    # Handle unavailable server case
```

### Available Parameters

The `GenerateParams` class supports the following parameters:

- `prompt` (required): The prompt to generate completions for
- `max_tokens`: Maximum number of tokens to generate (default: 1024)
- `temperature`: Sampling temperature (default: 0.7)
- `top_p`: Nucleus sampling parameter (default: 0.95)
- `top_k`: Top-k sampling parameter (default: 40)
- `stop`: Sequences to stop generation at
- `frequency_penalty`: Penalty for token frequency (default: 0.0)
- `presence_penalty`: Penalty for token presence (default: 0.0)

## Integration Tests

Two test files demonstrate proper integration:

1. `test_lmstudio_sdk.py` - A comprehensive test of the SDK functionality
2. `test_simple_lmstudio.py` - A simpler test with fallback examples

Run these tests to verify your integration.
