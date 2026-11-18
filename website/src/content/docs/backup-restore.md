---
title: Backup and restore
order: 10
description: Automatic backups, manual restore, and rollback.
---

# Backup and restore

Every write creates a timestamped backup next to the configuration file before the atomic replace:

```text
oh-my-opencode-slim.jsonc.bak.20261118-114502-123456
```

Backups are stored with `0600` permissions. The original file's permissions are preserved on the new file.

## Restore from the menu

Open **Backup and restore**, pick a backup, and confirm. The current state is backed up first, so a restore is itself reversible.

## Restore from the CLI

```sh
omo-model-slim backups
omo-model-slim restore --yes
```

The CLI restores the most recent backup. For a specific backup, choose it in the menu.

## If a write fails

Writes are validated before and after replacement. If verification fails, the previous content is written back automatically and the error is reported. No changes should be left half-applied.

## Installation rollback

An upgrade keeps the previous application directory as `~/.local/share/omo-model-slim.rollback.<timestamp>`. See [Updating](/docs/updating) for the rollback command.
