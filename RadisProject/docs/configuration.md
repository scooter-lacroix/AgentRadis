# RadisProject Configuration Guide

This guide provides detailed information on how to configure RadisProject.

## Configuration File

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
    api_base: "http://localhost:1234/v1"
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

## Customization

You can customize RadisProject by modifying the `config.yaml` file to suit your specific needs.

## Validation

Ensure that the `config.yaml` file is valid YAML. You can use online YAML validators to check for syntax errors.
