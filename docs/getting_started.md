# Getting Started with RadisProject

This guide provides instructions on how to get started with RadisProject.

## Prerequisites

*   Python 3.11+
*   Conda (recommended)

## Installation Steps

1.  **Create a Conda Environment:**

    ```bash
    conda create -n radis python=3.11
    conda activate radis
    ```

2.  **Clone the Repository:**

    ```bash
    git clone https://example.com/RadisProject.git
    cd RadisProject
    ```

3.  **Install RadisProject with Dependencies:**

    ```bash
    pip install -e ".[gpu]"  # For GPU support
    # Or, for specific GPU support:
    pip install -e ".[rocm]" # For AMD GPUs (ROCm)
    pip install -e ".[cuda]" # For NVIDIA GPUs (CUDA)
    ```

    *   `pip install -e ".[gpu]"`: Installs RadisProject in editable mode along with core dependencies and GPU support.
    *   `pip install -e ".[rocm]"`: Installs RadisProject with ROCm support for AMD GPUs.
    *   `pip install -e ".[cuda]"`: Installs RadisProject with CUDA support for NVIDIA GPUs.

## Configuration

RadisProject is configured using a `config.yaml` file. This file specifies various parameters for the system, including the active LLM, LLM settings, browser settings, and logging level.

### Location

The `config.yaml` file should be located in the root directory of the RadisProject.

### Structure

The `config.yaml` file has the following structure:

```yaml
active_llm: lm_studio
llm:
  lm_studio:
    api_type: local
    model: gemma-3-4b-it
    fallback_model: null
    temperature: 0.7
    max_tokens: 2000
    api_key: "lm-studio"
    api_base: "http://127.0.0.1:1234/v1"
browser:
  headless: true
  executable_path: "/usr/bin/firefox"
log_level: info
```

### Parameters

*   `active_llm`: Specifies which LLM configuration to use from the `llm` section.
*   `llm`: Contains the configuration for different LLM providers.
    *   `lm_studio`: Configuration for the LM Studio LLM provider.
        *   `api_type`: The API type (e.g., local).
        *   `model`: The model identifier.
        *   `fallback_model`: A fallback model to use if the primary model is unavailable.
        *   `temperature`: The sampling temperature.
        *   `max_tokens`: The maximum number of tokens to generate.
        *   `api_key`: The API key for the LLM provider.
        *   `api_base`: The base URL for the LLM API.
*   `browser`: Contains the configuration for the browser.
    *   `headless`: Whether to run the browser in headless mode.
    *   `executable_path`: The executable path for the browser.
*   `log_level`: Specifies the logging level (e.g., info, debug, warning, error).

## Basic Usage

```python
from app.agent import RadisAgent
from app.core import ContextManager
from app.tool import ToolRegistry

# Initialize the agent with session context
context_manager = ContextManager()
session_context = context_manager.get_context("user_session_123")
agent = RadisAgent(session_context=session_context)

# Access the tool registry
tool_registry = ToolRegistry.get_instance()

# Run the agent with a task
result = agent.run("Summarize the key findings in the research paper.")

print(result)
```

## Next Steps

*   Explore the [Architecture Documentation](architecture.md) to understand the system's components and data flows.
*   Review the [Tool Development Guide](tools.md) to learn how to create and integrate new tools.
*   Consult the [API Reference](api/) for details on the available APIs.
