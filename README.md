# OMO Manager

A lightweight, dependency-free Python terminal app for managing [OpenCode](https://opencode.ai) and [Oh My OpenCode Slim](https://github.com/alvinunreal/oh-my-opencode-slim) configuration, plus a static documentation site with a browser-only terminal playground.

- CLI executable: `omo-model-slim`
- Version: **v1.0.4**
- Lifecycle output: branded, color-aware step summaries for install/upgrade/uninstall/verify
- Repository: https://github.com/garsetayusuf/omo-model-slim
- Website: https://omo-manager.seri.my.id
- License: MIT

## What it actually does

- Full-screen keyboard UI: arrow keys navigate, Enter selects, Esc returns, and model/preset lists are searchable. The full-screen UI has no numeric shortcuts and no "press Enter to continue" screens. A simple line-based fallback is used only in non-TTY sessions.
- Reads and edits Slim configuration with JSONC support (comments and trailing commas). Edits are positional, so formatting, comments, and unrelated keys survive.
- Handles direct preset agents, nested `preset.agents` maps, multiple presets, single-parent `extends` chains, root-level `agents` overrides, and resolves/preserves agent-level `inheritModelFrom`.
- Handles model strings, ordered fallback chains (including `{ id, variant }` entries), `variant`, `fallback_models`, and `fallbackModels`. Changing a primary model leaves fallback entries intact.
- Manages OpenCode providers, custom models, local and remote MCP servers (including enable/disable), and the default model via `opencode.json` / `.jsonc`.
- Creates a timestamped backup before every write, validates before and after replacement, writes atomically, follows symlinks to their targets, and rolls back on verification failure.
- Offers `verify` against `opencode models`, `doctor` diagnostics, a catalog refresh, dry-run previews for `set`/`edit`, and restore.

## Requirements

- Python **3.10+** and `curl` for the installer
- `opencode` on PATH for model discovery, model changes, `verify`, and `doctor`. Without it, `config-path`, `current`, and `effective` still work, but selecting models from the registry is unavailable.
- macOS, Linux, or WSL 2. WSL 1 is best-effort.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/garsetayusuf/omo-model-slim/main/install.sh | bash
```

No sudo. The installer downloads the pinned `v1.0.4` artifacts, verifies their SHA-256 checksums, validates Python syntax, and installs into your home directory.

Lifecycle commands print a compact, color-aware summary:

```text
OMO Manager - v1.0.4

  *  Install
  *  1/5  Platform detected             OK macOS
  *  2/5  Python 3.10+                  OK Python 3.15.2
  *  3/5  Download & checksums          OK 4 files verified
  *  4/5  Install application files     OK
  *  5/5  Verify executable             OK omo-model-slim 1.0.4

  OK Install complete
    Command   omo-model-slim
    Location  ~/.local/bin/omo-model-slim
    Next      omo-model-slim
```

If `omo-model-slim` is not found afterwards, add `~/.local/bin` to your PATH:

```sh
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc   # or ~/.bashrc
```

### Upgrade, verify, uninstall, rollback

```sh
omo-model-slim upgrade          # aliases: update, install; reports "Already up to date" when unchanged
omo-model-slim uninstall        # removes the CLI, skips PATH cleanup while
                                # ~/.local/bin still holds other executables;
                                # otherwise surgically removes just the OMO
                                # PATH segment from zsh/bash profiles and backs them up
sh ~/.local/share/omo-model-slim/install.sh verify
```

Upgrades save the previous application directory as `~/.local/share/omo-model-slim.rollback.<timestamp>`. To roll back, use the exact path printed by the installer:

```sh
rm -rf ~/.local/share/omo-model-slim
mv ~/.local/share/omo-model-slim.rollback.<timestamp> ~/.local/share/omo-model-slim
```

More detail: [website/src/content/docs/installation.md](website/src/content/docs/installation.md).

## CLI reference

| Command | Purpose |
| --- | --- |
| `omo-model-slim` | Full-screen interactive menu |
| `--version` | Print the CLI version |
| `set MODEL [--all \| --agent NAME \| --category NAME] [--dry-run] [-y]` | Set primary models; fallback chains are preserved |
| `edit variant\|fallback TARGET VALUE [--dry-run] [-y]` | Change an existing variant/fallback field; `TARGET` is the dot-separated path shown by `current` |
| `list` / `free` / `search KEYWORD` | Browse the OpenCode model catalog |
| `providers` / `auth` | List authenticated providers |
| `current` | Show every configured model, variant, and fallback with its exact path |
| `effective [--preset NAME]` | Show resolved models after preset inheritance and root overrides |
| `verify` | Check configured model IDs against `opencode models` |
| `doctor [--full]` | Run diagnostics; `--full` also calls the official Slim doctor via `bunx` |
| `backups` / `restore [-y]` | List backups / restore the most recent one |
| `config-path` / `opencode-current` | Print the active Slim config path / OpenCode config |
| `upgrade` (`update`, `install`) | Re-run the verified installer |
| `uninstall` | Remove the CLI |

Environment overrides: `OMO_SLIM_CONFIG`, `OMO_OPENCODE_CONFIG`, `OPENCODE_CONFIG_DIR`; `OMO_BASIC_UI=1` forces the line-based fallback; `OMO_NO_CLEAR=1` disables screen clearing. Installer overrides: `OMO_VERSION`, `OMO_BASE_URL`, `OMO_NO_VERIFY=1` (testing only), `PREFIX`, `OMO_COLOR=0` or `NO_COLOR=1` for plain output, `OMO_VERBOSE=1` for per-file checksum details.

## Interactive menu

Dashboard, configure all agents, configure one agent, manage presets, browse/search models, manage variants, manage fallbacks, custom providers and models, MCP servers, default OpenCode model, verify, doctor, backup/restore, refresh catalog, Exit.

## Configuration

| File | Purpose |
| --- | --- |
| `~/.config/opencode/oh-my-opencode-slim.jsonc` / `.json` | Slim agent/preset settings (`.jsonc` wins) |
| `~/.config/opencode/opencode.jsonc` / `.json` | OpenCode providers, MCPs, default model |

## Website

Four static pages: home, documentation (14 Markdown topics), playground, and changelog. Built with Astro 7, React 19, Tailwind CSS 4, Motion, Lucide, and xterm.js. The terminal is a deterministic TypeScript state machine: it runs no shell commands, opens no sockets, reads no local files, and adapts its layout to narrow screens. The site has a persistent dark/light theme and a single-open FAQ.

## Repository layout

```text
omo-model-slim            CLI entry point (argparse + lifecycle commands)
omo_model_slim.py         core config logic, JSONC parser, safe writes
omo_tui.py                curses terminal UI
opencode_manage.py        OpenCode provider/model/MCP editor
install.sh                version-pinned, checksum-verified installer
tests/                    CLI, lifecycle, installer and config unit tests
website/                  Astro + React + Tailwind site
  src/content/docs/       documentation sources
  tests/                  Playwright browser tests
  vercel.json             deployment settings
.github/workflows/        CI and release pipelines
```

## Development

```sh
python3 -m unittest discover -s tests -v          # 37 tests

cd website
npm ci
npm run dev
npm run check                                     # astro check, strict TypeScript
npx tsc --noEmit
npm run build
npx playwright install chromium
npm run test:e2e                                  # 34 tests, desktop + mobile
```

`npm audit` currently reports 0 vulnerabilities.

## Verification status

| Item | Status |
| --- | --- |
| Python 3.10 / 3.12 / 3.13 on Ubuntu and macOS | CI matrix, green |
| macOS Apple Silicon (`macos-latest`) | CI + local installer verification |
| macOS Intel | Not separately verified |
| Linux (Ubuntu) | CI matrix + installer smoke test in CI |
| Clean install from the one-line installer | Verified locally on macOS |
| WSL 1 | Best-effort, unverified |
| WSL 2 | Not verifiable on GitHub-hosted runners |
| Website build, types, browser tests, Vercel preview | CI, green |

## Deployment

The site deploys from `main` to https://omo-manager.seri.my.id (Vercel: framework Astro, root `website`, build `npm run build`, output `dist`). The live deployment was verified in a browser after merge.

## Security

- No API keys or credentials are printed by the CLI; authentication stays in OpenCode's auth store.
- Every write is backed up, validated, atomically replaced, verified, and rolled back on failure. Symlinks are followed while preserving the link.
- The installer pins the release version, verifies SHA-256 checksums, needs no sudo, and does not write user configuration.
- The website is fully static, renders only trusted repository content, and executes no user shell commands.
- Type safety is enforced with `astro/tsconfigs/strict`; `astro check` and `tsc --noEmit` both pass cleanly.
