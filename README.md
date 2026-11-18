# OMO Manager

A lightweight, dependency-free terminal app for managing [OpenCode](https://opencode.ai) and [Oh My OpenCode Slim](https://github.com/alvinunreal/oh-my-opencode-slim) configuration — plus a modern Astro documentation site with a browser-only terminal playground.

- CLI executable: `omo-model-slim`
- Version: **v1.0.0**
- Repository: https://github.com/garsetayusuf/omo-model-slim
- Website: https://omo-manager.seri.my.id
- License: MIT

## Features

- Keyboard-driven menu: arrow keys, Enter, Esc, searchable model lists, no numeric shortcuts
- Schema-aware Slim editing: direct preset agents, nested `agents`, `extends` inheritance, root `agents` overrides, `inheritModelFrom`
- Model strings, ordered fallback chains (strings and `{ id, variant }` objects), variants, and legacy fallback fields
- OpenCode provider, custom model, MCP server (local/remote, enable/disable), and default-model management
- JSONC parsing with comments and trailing commas; positional edits preserve formatting and unrelated keys
- Automatic timestamped backups, atomic writes, pre/post-write verification, dry-run previews, and restore
- Verification against `opencode models`, doctor checks, and a full model catalog refresh
- Version-pinned installer with SHA-256 verification, rollback, and no `sudo`

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/garsetayusuf/omo-model-slim/main/install.sh | bash
```

Requires Python 3.10+ and curl. Installs to `~/.local/bin/omo-model-slim` and `~/.local/share/omo-model-slim/`. The existing `omo-model` executable is never modified, and no user configuration is written during installation.

If the command is not found, add `~/.local/bin` to your PATH:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc   # or ~/.bashrc
```

### Verify, upgrade, uninstall, rollback

```sh
sh ~/.local/share/omo-model-slim/install.sh verify
sh ~/.local/share/omo-model-slim/install.sh uninstall
```

Upgrades keep the previous application directory at `~/.local/share/omo-model-slim.rollback.<timestamp>`:

```sh
rm -rf ~/.local/share/omo-model-slim
mv ~/.local/share/omo-model-slim.rollback.* ~/.local/share/omo-model-slim
```

Full instructions: [website/src/content/docs/installation.md](website/src/content/docs/installation.md).

## CLI usage

```sh
omo-model-slim                       # interactive menu
omo-model-slim --version
omo-model-slim effective             # resolved models after inheritance
omo-model-slim current               # configured fields and their exact paths
omo-model-slim set openai/gpt-6.1-sol --all --dry-run
omo-model-slim edit variant presets.openai.oracle.variant high
omo-model-slim verify
omo-model-slim doctor --full
```

Configuration files:

| File | Purpose |
| --- | --- |
| `~/.config/opencode/oh-my-opencode-slim.jsonc` / `.json` | Slim agent/preset settings (`.jsonc` wins) |
| `~/.config/opencode/opencode.jsonc` / `.json` | OpenCode providers, MCPs, default model |

## Repository layout

```text
omo-model-slim                  CLI entry point (argparse)
omo_model_slim.py               core config logic, JSONC parser, safe writes
omo_tui.py                      curses terminal UI
opencode_manage.py              OpenCode provider/MCP editor
install.sh                      versioned, checksum-verified installer
tests/                          CLI, installer and config unit tests
website/                        Astro + React + Tailwind + xterm.js site
  src/content/docs/             documentation sources (Markdown)
  tests/                        Playwright browser tests
.github/workflows/              CI and release pipelines
```

## Development

```sh
python3 -m unittest discover -s tests -v

cd website
npm ci
npm run dev
npm run check
npm run build
npx playwright install chromium
npm run test:e2e
```

The terminal in the website is a deterministic TypeScript state machine. It executes no shell commands, opens no sockets, and never reads local files.

## Platform verification

| Platform | Status |
| --- | --- |
| macOS (Intel/Apple Silicon) | CI matrix + local installer smoke test |
| Linux (Ubuntu) | CI matrix + local installer smoke test |
| Python 3.10 / 3.12 / 3.13 | CI matrix |
| WSL 1 | Best-effort, unverified |
| WSL 2 | Not verifiable on GitHub-hosted runners; requires a real WSL environment |

## Deployment

Vercel: framework **Astro**, root directory `website`, build `npm run build`, output `dist`, production branch `main`. The custom domain is `omo-manager.seri.my.id`. A live deployment is only claimed after DNS and the Vercel domain are verified.

## Security notes

- The CLI never prints API keys; credentials stay in OpenCode's auth store.
- All writes are backed up, validated, atomically replaced, verified, and rolled back on failure. Config symlinks are followed while preserving the link.
- Review remote installers before piping them to a shell.
- `npm audit` currently reports advisories in Astro 5 and its build/dev toolchain (including a `define:vars` XSS advisory affecting Astro < 6.1.6). This site is fully static, renders only trusted repository content, and never uses `define:vars` or untrusted spread attributes. A framework upgrade to Astro 7 is the tracked follow-up for a clean audit.
