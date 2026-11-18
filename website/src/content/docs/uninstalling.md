---
title: Uninstalling
order: 12
description: Remove the CLI without losing configuration.
---

# Uninstalling

A copy of the installer is installed beside the application files:

```sh
omo-model-slim uninstall
```

Or run the installed installer directly:

```sh
sh ~/.local/share/omo-model-slim/install.sh uninstall
```

This removes `~/.local/bin/omo-model-slim` and `~/.local/share/omo-model-slim/`. It does **not** delete Slim/OpenCode configuration, backups, or rollback directories.

Remove the PATH line you added earlier if you no longer need `~/.local/bin` on your PATH.

## Manual removal

```sh
rm -f ~/.local/bin/omo-model-slim
rm -rf ~/.local/share/omo-model-slim
```

Your existing `omo-model` executable is never touched by either method.
