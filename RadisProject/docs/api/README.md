# RadisProject API Reference

This document provides a reference for the RadisProject APIs.

## OpenAI Compatibility API

RadisProject supports the OpenAI Compatibility API, allowing you to use existing OpenAI clients with RadisProject.

### Endpoints

*   `GET /v1/models`: Lists the available models.
*   `POST /v1/chat/completions`: Sends a chat history and receives the assistant's response.
*   `POST /v1/embeddings`: Sends a string or array of strings and gets an array of text embeddings.
*   `POST /v1/completions`: Sends a string and gets the model's continuation of that string.

For more information, see the [OpenAI Compatibility API Documentation](openai-api.md).

## RadisProject REST API (Beta)

RadisProject also provides its own REST API, offering enhanced stats and model information.

### Endpoints

*   `GET /api/v0/models`: Lists available models.
*   `GET /api/v0/models/{model}`: Gets info about a specific model.
*   `POST /api/v0/chat/completions`: Chat Completions API.
*   `POST /api/v0/completions`: Text Completions API.
*   `POST /api/v0/embeddings`: Text Embeddings API.

For more information, see the [RadisProject REST API Documentation](rest-api.md).
