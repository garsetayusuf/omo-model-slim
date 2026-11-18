---
title: Configuration locations
order: 9
description: File discovery, JSONC support, schema shapes, and precedence.
---

# Configuration locations

| File | Managed by | Purpose |
| --- | --- | --- |
| `~/.config/opencode/oh-my-opencode-slim.jsonc` | Slim | Plugin settings (preferred when both exist) |
| `~/.config/opencode/oh-my-opencode-slim.json` | Slim | Same settings, plain JSON |
| `~/.config/opencode/opencode.jsonc` | OpenCode | Core settings (preferred when both exist) |
| `~/.config/opencode/opencode.json` | OpenCode | Core settings |

The CLI honors `OPENCODE_CONFIG_DIR` for the user config directory and `OMO_SLIM_CONFIG` / `OMO_OPENCODE_CONFIG` as explicit file overrides, which is useful for testing.

## Supported Slim structures

- Root `agents` overrides
- `presets.<name>.<agent>` direct definitions
- `presets.<name>.agents.<agent>` nested definitions
- `extends` inheritance (single parent)
- Model strings, arrays of strings, and arrays of `{ "id", "variant" }`
- `inheritModelFrom` with `session` or `orchestrator`
- `variant`, `fallback_models`, and `fallbackModels`
- JSONC comments and trailing commas

## Precedence

For overlapping agent fields, Slim resolves:

```text
ancestor preset < child preset < root agents < OpenCode host config
```

`omo-model-slim effective` shows the first three layers. The host config remains the final authority at runtime.

## Symlinks and permissions

Configuration symlinks are followed and their targets are updated, so the link itself is preserved. File permissions are retained on write. A dangling symlink is reported as an error rather than silently replaced.
