# OMO Manager

Cross-platform terminal configuration manager for OpenCode and Oh My OpenCode Slim.

**Status:** v1.0.0 development — not yet released.

## Planned support

- macOS (Intel and Apple Silicon), Linux, and WSL 2
- Manage Slim agent presets, model assignments, variants, and fallbacks
- Manage OpenCode providers, models, and MCP servers
- Backups, restore, and configuration diagnostics
- Interactive Astro + React + xterm.js website at https://omo-manager.seri.my.id (not deployed yet)

## Source import

The initial project source is being prepared for import. Do **not** run a remote installer until `install.sh` and its companion Python files are published and verified.

## Development

CLI requires Python 3.10+. Website is planned to use Astro, React, TypeScript, Tailwind CSS, and xterm.js. GitHub Actions will run tests on macOS and Linux.

## Security

The website terminal is a browser-only simulation, not a real shell. The CLI must back up files before modifying user configuration.
