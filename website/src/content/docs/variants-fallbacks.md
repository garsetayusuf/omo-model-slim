---
title: Variants and fallbacks
order: 6
description: Edit existing reasoning variants and fallback model entries.
---

# Variants and fallbacks

## Variants

A variant selects provider-specific reasoning effort, for example `low`, `medium`, `high`, `xhigh`, or `max`.

Use **Manage variants** in the menu to pick an existing variant field and change it. OMO Manager deliberately edits only fields that already exist rather than inventing keys your provider may not support.

```sh
omo-model-slim current
omo-model-slim edit variant presets.openai.oracle.variant high
```

Inline variants inside a fallback chain are shown too:

```jsonc
"model": [
  { "id": "openai/gpt-6.1-sol", "variant": "high" },
  "openai/gpt-6-luna"
]
```

## Fallbacks

A fallback chain is the ordered `model` array. The first entry is primary; the rest are tried on failure. Legacy `fallback_models` and `fallbackModels` fields are also detected.

Use **Manage model fallbacks** to change one existing fallback entry:

```sh
omo-model-slim edit fallback presets.openai.oracle.model.1 openai/gpt-6-luna --dry-run
```

Primary model changes never remove fallback entries. To add a brand-new fallback field, edit the configuration file directly; OMO Manager avoids creating keys that are not already present.

## Fallback policy

Root-level fallback behavior is configured by Slim itself, for example:

```jsonc
{
  "fallback": {
    "enabled": true,
    "maxRetries": 3,
    "retryDelayMs": 500,
    "continuationPolicy": "retry-primary"
  }
}
```

OMO Manager preserves this object unchanged.
