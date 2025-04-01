# RadisProject OpenAI Compatibility API Documentation

This document provides details on the RadisProject's OpenAI Compatibility API.

## Overview

RadisProject supports the OpenAI Compatibility API, allowing you to use existing OpenAI clients with RadisProject. This enables seamless integration with existing tools and workflows.

## Endpoints

### GET /v1/models

Lists the currently loaded models.

#### Example Request

```bash
curl http://localhost:1234/v1/models
```

#### Response Format

```json
{
  "object": "list",
  "data": [
    {
      "id": "model-identifier",
      "object": "model"
    }
  ]
}
```

### POST /v1/chat/completions

Sends a chat history and receives the assistant's response.

#### Example Request

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model-identifier",
    "messages": [{"role": "user", "content": "Say this is a test!"}],
    "temperature": 0.7
  }'
```

#### Response Format

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1685479092,
  "model": "model-identifier",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "This is a test!"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```

### POST /v1/embeddings

Sends a string or array of strings and gets an array of text embeddings.

#### Example Request

```bash
curl http://localhost:1234/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model-identifier",
    "input": "This is a test."
  }'
```

#### Response Format

```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [
        0.001,
        0.002,
        ...
      ],
      "index": 0
    }
  ],
  "model": "model-identifier",
  "usage": {
    "prompt_tokens": 5,
    "total_tokens": 5
  }
}
```

### POST /v1/completions

Sends a string and gets the model's continuation of that string.

#### Example Request

```bash
curl http://localhost:1234/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "model-identifier",
    "prompt": "This is a test.",
    "max_tokens": 10
  }'
```

#### Response Format

```json
{
  "id": "cmpl-...",
  "object": "text_completion",
  "created": 1685479092,
  "model": "model-identifier",
  "choices": [
    {
      "text": " This is a test continuation.",
      "index": 0,
      "logprobs": null,
      "finish_reason": "length"
    }
  ],
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 10,
    "total_tokens": 15
  }
}
```

## Re-using an Existing OpenAI Client

You can reuse existing OpenAI clients (in Python, JS, C#, etc) by switching up the "base URL" property to point to your LM Studio instead of OpenAI's servers.

### Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)
```

### TypeScript

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseUrl: "http://localhost:1234/v1"
});