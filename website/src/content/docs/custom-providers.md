---
title: Custom providers
order: 7
description: Manage OpenCode provider entries and custom model definitions.
---

# Custom providers and models

OpenCode stores providers under the `provider` key of `opencode.json` or `opencode.jsonc`. OMO Manager edits that file with the same safety guarantees as Slim configuration: backup, preview, atomic write, and verification.

## Add a provider

In **Custom providers and models**, choose **+ Add new**. You can provide a base URL for an OpenAI-compatible endpoint:

```jsonc
{
  "provider": {
    "my-local": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": {}
    }
  }
}
```

Avoid pasting API keys into the menu or website. Put credentials in OpenCode's auth store instead.

## Manage custom models

Each provider can define its own models:

```jsonc
{
  "provider": {
    "my-local": {
      "npm": "@ai-sdk/openai-compatible",
      "models": {
        "local/llama": { "name": "Local Llama" }
      }
    }
  }
}
```

Add, edit, or delete models from **Manage custom models**. Definitions are entered as a one-line JSON object and validated before saving.

## Default model

**Default OpenCode model** sets the top-level `model` field:

```jsonc
{ "model": "my-local/local/llama" }
```

Every write preserves unrelated sections and comments in the OpenCode config.
