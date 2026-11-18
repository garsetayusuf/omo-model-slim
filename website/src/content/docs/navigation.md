---
title: CLI navigation
order: 3
description: Keyboard controls and the fifteen main menu actions.
---

# CLI navigation

Run `omo-model-slim` with no arguments to open the interactive menu.

| Key | Action |
| --- | --- |
| ↑ / ↓ | Move between options |
| Enter | Open the highlighted option |
| Esc | Return to the previous screen |
| Type | Filter a searchable list (models, presets, servers) |
| Backspace | Edit the search query |
| PgUp / PgDn / Home / End | Move through long lists |

The terminal is restored to its original state on exit, errors, and interrupts. Resize your terminal at any time; the menu reflows and redraws without flicker.

## Main menu

1. Dashboard / overview
2. Configure all agent models
3. Configure individual agents
4. Manage presets
5. Browse and search models
6. Manage variants
7. Manage model fallbacks
8. Custom providers and models
9. MCP servers
10. Default OpenCode model
11. Verify assignments
12. Doctor
13. Backup and restore
14. Refresh model catalog
15. Exit

Exit is always last. There are no numeric shortcuts and no "press Enter to continue" screens.

## Useful subcommands

```sh
omo-model-slim --version
omo-model-slim effective              # resolved models after inheritance
omo-model-slim current                # every configured field and its path
omo-model-slim set openai/gpt-6.1-sol --all --dry-run
omo-model-slim edit variant presets.openai.oracle.variant high
omo-model-slim verify
omo-model-slim doctor --full
omo-model-slim config-path
omo-model-slim upgrade               # upgrade/reinstall (aliases: update, install)
omo-model-slim uninstall             # remove the CLI, keep configuration
```

Use `--dry-run` to preview a change without writing, and `--yes` to skip the confirmation prompt in scripts.
