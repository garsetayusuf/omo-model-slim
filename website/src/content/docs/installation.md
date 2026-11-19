---
title: Installation
order: 2
description: Install OMO Manager on macOS, Linux, and WSL.
---

# Installation

## One-line install

```sh
curl -fsSL https://raw.githubusercontent.com/garsetayusuf/omo-model-slim/main/install.sh | bash
```

Review the script before piping it to a shell. The installer requires Python 3.10+ and curl, uses no `sudo`, and writes only inside your home directory.

## macOS (Intel and Apple Silicon)

Run the command in Terminal or iTerm2. The installer detects Darwin, pins the `v1.0.5` release, verifies SHA-256 checksums, and installs to `~/.local/bin`.

If `omo-model-slim` is not found afterwards, add the bin directory to your shell profile:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Linux (Ubuntu, Debian, Fedora)

Run the command in your terminal. The installer uses POSIX shell utilities and avoids GNU-only flags that break on other systems.

```sh
omo-model-slim --version
```

## WSL

Run the installer **inside your WSL Linux shell**, not PowerShell or Command Prompt:

```sh
curl -fsSL https://raw.githubusercontent.com/garsetayusuf/omo-model-slim/main/install.sh | bash
```

Install OpenCode inside the same WSL distribution. macOS and Linux are verified in CI; WSL 2 requires verification in a real WSL environment and is not marked verified by Ubuntu CI alone.

## What gets installed

| Path | Purpose |
| --- | --- |
| `~/.local/bin/omo-model-slim` | Executable wrapper |
| `~/.local/share/omo-model-slim/` | Python source files |
| `~/.local/share/omo-model-slim.rollback.*` | Previous version, kept for rollback |

The existing `omo-model` executable is never touched. No configuration is written during installation.

## Verify and uninstall

```sh
sh ~/.local/share/omo-model-slim/install.sh verify
sh ~/.local/share/omo-model-slim/install.sh uninstall
```

To roll back an upgrade, replace the installed directory with the most recent rollback copy:

```sh
rm -rf ~/.local/share/omo-model-slim
mv ~/.local/share/omo-model-slim.rollback.* ~/.local/share/omo-model-slim
```
