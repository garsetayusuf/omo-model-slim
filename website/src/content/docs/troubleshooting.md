---
title: Troubleshooting
order: 13
description: Diagnose command discovery, config, and model registry problems.
---

# Troubleshooting

## `omo-model-slim: command not found`

Add the install directory to your PATH and restart your shell:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

On macOS the default shell is zsh, so add that line to `~/.zshrc`; on Linux it is usually `~/.bashrc`.

## `Configuration not found`

The CLI looks for `~/.config/opencode/oh-my-opencode-slim.jsonc`, then `.json`. Point it at another file:

```sh
OMO_SLIM_CONFIG=/path/to/config.jsonc omo-model-slim
```

## Invalid JSONC error

The error includes the file, line, column, and surrounding lines. Fix the malformed comma, brace, or string and re-run. No changes are written when parsing fails.

## Unknown model IDs

`verify` compares configured IDs to `opencode models`. If a provider is not authenticated, its models may not appear. Check `omo-model-slim auth` and refresh the catalog from the menu.

## Terminal looks wrong after an error

The curses UI restores the terminal on exit and interrupts. If a crashed session left your terminal odd, run `reset` in the shell.

## Small terminal

The menu needs at least 30 columns and 7 rows. Enlarge the window and press any navigation key.

## Curses unavailable

Set `OMO_BASIC_UI=1` to use the line-based fallback interface, or use the subcommands described in [CLI navigation](/docs/navigation).
