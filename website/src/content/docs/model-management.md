---
title: Model management
order: 4
description: Change agent models safely while preserving fallbacks and comments.
---

# Model management

## Changing models

Choose **Configure all agent models**, **Configure individual agents**, or **Manage presets** in the menu. Each flow offers a searchable model list sourced from `opencode models`, then shows a preview before writing.

For scripting:

```sh
omo-model-slim set openai/gpt-6.1-sol --all --dry-run
omo-model-slim set openai/gpt-6-luna --agent presets/openai/oracle --yes
```

Targets accept the exact model path shown by `omo-model-slim current`, the agent name, or a slash-separated path such as `presets/openai/oracle`.

## Fallback preservation

Only the **primary** model is replaced. Every element of an ordered fallback chain is left alone:

```jsonc
"oracle": {
  "model": ["openai/gpt-6.1-sol", "openai/gpt-6-luna"],
  "variant": "high"
}
```

Changing the primary with `--agent presets/openai/oracle` produces `["new/model", "openai/gpt-6-luna"]`. If a chain uses object entries with inline variants, only the `id` is rewritten so the inline variant survives.

## Verification

```sh
omo-model-slim verify
```

Each configured model ID is checked against the live OpenCode registry. Verification is a registry check only: it does not authenticate providers or make requests.

## Model discovery and catalog refresh

**Refresh model catalog** re-runs `opencode models` and `opencode auth list`. Free-labeled models appear first, then authenticated providers, then everything else. If discovery fails, the error is shown in the dashboard instead of crashing the app.
