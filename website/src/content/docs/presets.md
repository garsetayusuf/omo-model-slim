---
title: Presets and inheritance
order: 5
description: Multiple presets, extends chains, and effective model resolution.
---

# Presets and inheritance

Oh My OpenCode Slim supports two preset shapes, both handled by OMO Manager.

## Direct preset agents

```jsonc
{
  "preset": "openai",
  "presets": {
    "openai": {
      "orchestrator": { "model": "openai/gpt-6.1-sol", "variant": "medium", "skills": ["*"] },
      "oracle": { "model": ["openai/gpt-6.1-sol", "openai/gpt-6-luna"], "variant": "high" }
    }
  }
}
```

The nested `agents` form is also supported:

```jsonc
{ "presets": { "openai": { "agents": { "oracle": { "model": "openai/gpt-6-luna" } } } } }
```

## Preset inheritance

A preset may inherit from one parent using `extends`. Multi-parent inheritance is not supported.

```jsonc
{
  "preset": "powerful",
  "presets": {
    "base": { "oracle": { "model": "openai/gpt-6-luna", "variant": "medium" } },
    "powerful": { "extends": "base", "orchestrator": { "model": "openai/gpt-6.1-sol" } }
  }
}
```

Inheritance cycles are detected and reported instead of looping.

## Effective resolution

`omo-model-slim effective` prints the models that actually apply after layering:

```text
ancestor preset < child preset < root agents < OpenCode host config
```

Root `agents` entries are global: they override the active preset. Put a per-preset value inside each preset instead.

## inheritModelFrom

An agent can follow the session or orchestrator model:

```jsonc
{ "agents": { "fixer": { "inheritModelFrom": "session", "model": ["fallback/one"] } } }
```

The primary model is inherited; the array becomes its fallback chain. An explicit scalar `model` wins over `inheritModelFrom`. Both forms are displayed correctly by **Dashboard** and the effective view.
