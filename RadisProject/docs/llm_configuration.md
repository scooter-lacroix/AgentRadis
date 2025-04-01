# LLM Configuration

This document describes how to configure Large Language Models (LLMs) in the Radis project.

## Configuration File

The LLM configuration is stored in the `config.yaml` file. This file centralizes settings for all LLM providers, such as OpenAI, Anthropic, and LM Studio, under the `llm_settings` section.

## LLMConfig Class

The `LLMConfig` class in `app/config.py` defines the structure of the LLM configuration. It includes the following attributes:

*   `api_type`: The type of API to use (e.g., "openai", "anthropic", "local").
*   `model`: The name of the LLM model to use (e.g., "gpt-3.5-turbo", "claude-3-opus", "gemma-3-4b-it").
*   `fallback_model`: An optional fallback model to use if the primary model is not available.
*   `temperature`: The temperature to use for text generation (default: 0.7).
*   `max_tokens`: The maximum number of tokens to generate (default: 2000).
*   `api_key`: The API key for the LLM provider (if required).
*   `api_base`: The base URL for the LLM API (if applicable).
*   `model_path`: The path to a local model file (.gguf, .safetensors) for local models.
*   `tokenizer`: Optional, specific tokenizer to use (e.g., "tiktoken", "sentencepiece").
*   `tokenizer_fallback`: Boolean, whether to use fallback tokenizers when primary not available.
*   `context_length`: Optional, maximum context length for the model.
*   `gpu_layers`: Integer, number of layers to offload to GPU (for local models).
*   `timeout`: Float, timeout in seconds for API calls.
*   `retry_count`: Integer, number of retries for failed API calls.
*   `retry_delay`: Float, initial delay between retries (seconds).


## Centralized LLM Settings in `config.yaml`

The `config.yaml` now uses a centralized `llm_settings` section to manage configurations for different LLM providers. The `active_llm` setting specifies which LLM configuration to use.

Example `llm_settings` in `config.yaml`:

```yaml
active_llm: "lm_studio"  # Specify active LLM

llm_settings:
  lm_studio: # Configuration for LM Studio
    api_type: "local"
    model: "gemma-3-4b-it"
    api_base: "http://localhost:1234/"
    api_key: "lm-studio"
    model_path: "/path/to/your/model.gguf" # Path to your local model file

  openai: # Configuration for OpenAI (example)
    enabled: false
    api_type: "openai"
    model: "gpt-4-turbo"
    api_base: "https://api.openai.com/v1"
    api_key: "" # Add your OpenAI API key if enabled
    max_tokens: 4096
    temperature: 0.0
```

## Configuring LM Studio with `model_path`

To configure LM Studio to load a local model file directly (without using the LM Studio API), you need to specify the `model_path` in the `config.yaml` file under the `llm_settings.lm_studio` section:

```yaml
active_llm: "lm_studio"

llm_settings:
  lm_studio:
    api_type: "local"
    model: "gemma-3-4b-it"
    model_path: "/path/to/your/model.gguf" # Path to your local model file
```

*   `active_llm`: Set to `"lm_studio"` to use LM Studio configuration.
*   `llm_settings.lm_studio.api_type`: Set to `"local"` to indicate local LLM.
*   `llm_settings.lm_studio.model`: Set to the name of the model you are using.
*   `llm_settings.lm_studio.model_path`: **Specify the full path to your local model file** (`.gguf` or `.safetensors` format). 
*   `llm_settings.lm_studio.api_base` and `api_key`: These are not required when using `model_path` for direct model loading, but you can keep the default values or remove them.

**Note:** When `model_path` is provided, the application will attempt to load the local model file directly using libraries like `ctransformers`, bypassing the LM Studio API. Ensure that the specified path is correct and the model file exists.

## Configuring LM Studio API

If you prefer to use the LM Studio API (e.g., for models not directly supported by `ctransformers` or for using LM Studio's server features), configure LM Studio as follows:

```yaml
active_llm: "lm_studio"

llm_settings:
  lm_studio:
    api_type: "local"
    model: "gemma-3-4b-it"
    api_base: "http://localhost:1234/" # Base URL of your LM Studio API
    api_key: "lm-studio" # Default API key for LM Studio
```

*   `active_llm`: Set to `"lm_studio"`.
*   `llm_settings.lm_studio.api_type`: Set to `"local"`.
*   `llm_settings.lm_studio.model`: Set to the name of the model you are using in LM Studio.
*   `llm_settings.lm_studio.api_base`: Set to the base URL of the LM Studio API (default: `"http://localhost:1234/"`).
*   `llm_settings.lm_studio.api_key`: Set to `"lm-studio"`. This value is generally ignored by LM Studio but is included for configuration consistency.

## Setting the API Base

The API base URL can be overridden using the `--api-base` command-line argument. This is useful for testing different LM Studio API configurations or if your LM Studio API is running on a different port or host.

```bash
python main.py --api-base "http://localhost:8080/v1"
```

This command-line argument will override the `api_base` specified in the `config.yaml` file.

## Fallback Tokenizers

The `LLMConfig` class includes settings for tokenizer handling:

*   `tokenizer`: Specifies the tokenizer to use (e.g., "tiktoken", "sentencepiece"). If not set, the system tries to auto-detect based on the model.
*   `tokenizer_fallback`: If `true` (default), the system will attempt to use fallback tokenizers if the primary tokenizer is not available for a given model. This ensures robustness across different models and environments.

These settings are generally auto-configured, but you can adjust them in the `config.yaml` if needed for specific models or tokenizer requirements.

By centralizing the LLM configurations and providing options for both LM Studio API and direct model loading, RadisProject offers flexible and maintainable LLM configuration management.
