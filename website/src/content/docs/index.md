---
title: Introduction
order: 1
description: What OMO Manager is, what it changes, and how to get started.
---

# Introduction

OMO Manager is a lightweight, dependency-free Python terminal app for managing [OpenCode](https://opencode.ai) and [Oh My OpenCode Slim](https://github.com/alvinunreal/oh-my-opencode-slim) configuration. It replaces manual JSON editing with a keyboard-driven menu.

The CLI command is `omo-model-slim`. It installs to `~/.local/bin/omo-model-slim` and never modifies an existing `omo-model` executable.

## What it manages

- Agent and category models across Slim presets
- Model fallback chains and reasoning variants
- Preset inheritance (`extends`) and `inheritModelFrom`
- Custom OpenCode providers and models
- Local and remote MCP servers
- The default OpenCode model
- Backups, restore, verification, and doctor checks

## What it does not do

The website terminal is a **browser-only simulation**. It never runs shell commands, reads your files, or contacts your machine. The CLI only edits two local configuration files, always after creating a backup and after showing a preview.

## Prerequisites

- Python 3.10 or newer
- `curl` for installation
- OpenCode and Oh My OpenCode Slim installed if you want model discovery and verification to work
- macOS, Linux, or WSL 2 (WSL 1 best-effort)

## Quick start

```sh
curl -fsSL https://raw.githubusercontent.com/garsetayusuf/omo-model-slim/main/install.sh | bash
omo-model-slim --version
omo-model-slim
```

Read [Installation](/docs/installation) for platform-specific notes, then [CLI navigation](/docs/navigation) for the menu controls.
