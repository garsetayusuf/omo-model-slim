---
title: Security considerations
order: 14
description: Credential handling, installer safety, and browser simulation boundaries.
---

# Security considerations

## Credentials

The CLI never prints API keys or secrets. Provider authentication stays in OpenCode's auth store. Do not paste credentials into the MCP URL field, provider definitions, or the website playground.

## Installer safety

- Downloads a pinned versioned release artifact over HTTPS
- Verifies SHA-256 checksums from the signed release asset before installing
- Validates Python syntax before replacing any file
- Keeps a rollback copy of the previous installation
- Uses no `sudo` and writes only inside your home directory
- Never writes to user configuration during installation

Always review a remote installer before piping it to a shell.

## File writes

- JSONC is parsed with comment and trailing-comma support; edits are positional
- Writes go to a temporary file, are `fsync`ed, and atomically replace the target
- A backup is created before every write
- Writes are verified after replacement and rolled back on failure
- Symlink targets are updated while preserving the link
- Backups use `0600` permissions

## Website boundary

The homepage terminal and playground are deterministic TypeScript state machines. They do not execute shell commands, open WebSockets, start a PTY, or access local storage containing secrets. Everything is in-memory demo data.
