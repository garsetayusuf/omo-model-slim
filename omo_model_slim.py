"""Core logic for OMO Manager.

Dependency-free, JSONC-safe editing of Oh My OpenCode Slim configuration.

Schema reference: the published ``oh-my-opencode-slim.schema.json`` and
``docs/configuration.md`` from alvinunreal/oh-my-opencode-slim. Relevant facts:

* ``presets.<name>`` may define agents directly, or use ``extends`` with an
  ``agents`` object (single-parent inheritance).
* A model is either a string, or an ordered fallback chain of strings and
  ``{"id": ..., "variant": ...}`` objects.
* ``inheritModelFrom`` is agent-level (``session`` or ``orchestrator``).
* Effective precedence is ancestor preset < child preset < root ``agents``
  < OpenCode host config. This module resolves the first three layers.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

VERSION = "1.0.3"
CONFIG_DIR = Path(os.environ.get("OPENCODE_CONFIG_DIR", "~/.config/opencode")).expanduser()
AGENT_NAMES = (
    "orchestrator",
    "oracle",
    "explorer",
    "designer",
    "fixer",
    "observer",
    "librarian",
)
PROVIDERS = (
    "openai",
    "opencode",
    "anthropic",
    "google",
    "github-copilot",
    "openrouter",
    "groq",
    "deepseek",
    "xai",
    "azure",
    "amazon-bedrock",
    "vertexai",
)
FALLBACK_FIELDS = ("fallback_models", "fallbackModels")


def config_path() -> Path:
    """Discover the active Slim configuration (tests override via env)."""
    override = os.environ.get("OMO_SLIM_CONFIG")
    if override:
        return Path(override).expanduser()
    for name in ("oh-my-opencode-slim.jsonc", "oh-my-opencode-slim.json"):
        candidate = CONFIG_DIR / name
        if candidate.is_file():
            return candidate
    return CONFIG_DIR / "oh-my-opencode-slim.json"


CONFIG = config_path()


# --------------------------------------------------------------------------- #
# External commands / model discovery
# --------------------------------------------------------------------------- #
def run(*args: str, timeout: int = 45) -> str:
    try:
        process = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"{args[0]}: {exc}") from exc
    if process.returncode:
        detail = (process.stderr or process.stdout).strip() or f"exit {process.returncode}"
        raise RuntimeError(f"{' '.join(args)}: {detail}")
    return process.stdout


def models() -> list[str]:
    return sorted(
        {
            line.strip()
            for line in run("opencode", "models").splitlines()
            if re.fullmatch(r"[\w.\-]+/[\w.\-]+", line.strip())
        }
    )


def auth_providers() -> set[str]:
    raw = run("opencode", "auth", "list")
    names: set[str] = set()
    for line in raw.splitlines():
        if "●" not in line and not re.match(r"^\s*[-*]\s+", line):
            continue
        part = re.split(r"[●*-]", line, maxsplit=1)[-1].strip().lower()
        for provider in PROVIDERS:
            if re.search(r"(?<![a-z])" + re.escape(provider) + r"(?![a-z])", part):
                names.add(provider)
    return names


def free_model(model: str) -> bool:
    return bool(re.search(r"(^|[-_/])free($|[-_/])", model, re.I))


# --------------------------------------------------------------------------- #
# JSONC parsing and positional token maps (preserves comments/formatting)
# --------------------------------------------------------------------------- #
def masked(source: str) -> str:
    """Blank out JSONC comments while preserving every character position."""
    out = list(source)
    i = 0
    while i < len(source):
        if source[i] == '"':
            i += 1
            while i < len(source):
                if source[i] == "\\":
                    i += 2
                elif source[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ValueError("Unterminated string in JSONC")
            continue
        if source.startswith("//", i):
            end = source.find("\n", i)
            if end < 0:
                end = len(source)
            for j in range(i, end):
                out[j] = " "
            i = end
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated JSONC comment")
            end += 2
            for j in range(i, end):
                if source[j] != "\n":
                    out[j] = " "
            i = end
        else:
            i += 1
    return "".join(out)


def parse(source: str) -> dict[str, Any]:
    """Parse JSONC (comments + trailing commas) into a dict."""
    clean = masked(source)
    outside = list(clean)
    i = 0
    while i < len(clean):
        if clean[i] == '"':
            start = i
            i += 1
            while i < len(clean):
                if clean[i] == "\\":
                    i += 2
                elif clean[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            for j in range(start, i):
                outside[j] = "X"
        else:
            i += 1
    for match in re.finditer(r",(?=\s*[}\]])", "".join(outside)):
        clean = clean[: match.start()] + " " + clean[match.start() + 1 :]
    try:
        result = json.loads(clean)
    except json.JSONDecodeError as exc:
        lines = source.splitlines()
        lo, hi = max(1, exc.lineno - 3), min(len(lines), exc.lineno + 2)
        context = "\n".join(
            f"{i:>4} {'-->' if i == exc.lineno else '   '} {lines[i - 1]}"
            for i in range(lo, hi + 1)
        )
        raise ValueError(
            f"Invalid JSONC in {CONFIG} at line {exc.lineno}, column {exc.colno}: {exc.msg}\n"
            f"{context}\nNo changes were made. Check for a missing comma, extra brace, or malformed string."
        ) from exc
    if not isinstance(result, dict):
        raise ValueError("Configuration root must be a JSON object")
    return result


def token_spans(source: str) -> dict[tuple[Any, ...], tuple[int, int]]:
    """Map exact JSON paths to the byte offsets of their string values."""
    clean = masked(source)
    token = re.compile(
        r'\s*("(?:\\.|[^"\\])*"|[{}\[\]:,]|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)',
        re.S,
    )
    tokens: list[tuple[str, int, int]] = []
    i = 0
    while i < len(clean):
        match = token.match(clean, i)
        if not match:
            if not clean[i:].strip():
                break
            raise ValueError(f"Unexpected JSONC token at character {i}")
        tokens.append((match.group(1), match.start(1), match.end(1)))
        i = match.end()
    index = 0
    spans: dict[tuple[Any, ...], tuple[int, int]] = {}

    def value(path: tuple[Any, ...]) -> None:
        nonlocal index
        if index >= len(tokens):
            raise ValueError("Unexpected end of JSONC")
        token_value, start, end = tokens[index]
        index += 1
        if token_value == "{":
            while index < len(tokens) and tokens[index][0] != "}":
                key = tokens[index][0]
                if not key.startswith('"'):
                    raise ValueError("Expected object key")
                index += 1
                if tokens[index][0] != ":":
                    raise ValueError("Expected colon")
                index += 1
                value(path + (json.loads(key),))
                if tokens[index][0] == ",":
                    index += 1
                elif tokens[index][0] != "}":
                    raise ValueError("Expected comma or closing brace")
            if index >= len(tokens):
                raise ValueError("Unclosed object")
            index += 1
        elif token_value == "[":
            n = 0
            while index < len(tokens) and tokens[index][0] != "]":
                value(path + (n,))
                n += 1
                if tokens[index][0] == ",":
                    index += 1
                elif tokens[index][0] != "]":
                    raise ValueError("Expected comma or closing bracket")
            if index >= len(tokens):
                raise ValueError("Unclosed array")
            index += 1
        elif token_value.startswith('"'):
            spans[path] = (start, end)

    value(())
    if index != len(tokens):
        raise ValueError("Extra JSONC tokens")
    return spans


def read() -> tuple[str, dict[str, Any]]:
    path = CONFIG
    if not path.is_file():
        raise RuntimeError(f"Configuration not found: {path}")
    source = path.read_text(encoding="utf-8")
    return source, parse(source)


# --------------------------------------------------------------------------- #
# Schema-aware traversal
# --------------------------------------------------------------------------- #
def _agent_containers(data: dict[str, Any]) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
    """Return (path prefix, agent-mapping) pairs for every agent scope."""
    containers: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    root_agents = data.get("agents")
    if isinstance(root_agents, dict):
        containers.append((("agents",), root_agents))
    categories = data.get("categories")
    if isinstance(categories, dict):
        containers.append((("categories",), categories))
    presets = data.get("presets")
    if isinstance(presets, dict):
        for preset_name, preset in presets.items():
            if not isinstance(preset, dict):
                continue
            nested = preset.get("agents")
            if isinstance(nested, dict):
                containers.append((("presets", preset_name, "agents"), nested))
            else:
                direct = {
                    name: agent
                    for name, agent in preset.items()
                    if isinstance(agent, dict) and name not in ("extends", "marketplace")
                }
                if direct:
                    containers.append((("presets", preset_name), direct))
    return containers


def _model_leaves(agent: dict[str, Any]) -> list[tuple[tuple[Any, ...], str]]:
    """String leaves of a model assignment (primary + fallback chain)."""
    leaves: list[tuple[tuple[Any, ...], str]] = []
    value = agent.get("model")
    if isinstance(value, str):
        leaves.append((("model",), value))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, str):
                leaves.append((("model", index), item))
            elif isinstance(item, dict) and isinstance(item.get("id"), str):
                leaves.append((("model", index, "id"), item["id"]))
    return leaves


def model_paths(data: dict[str, Any]) -> dict[tuple[Any, ...], str]:
    """Every configured model string, keyed by its exact JSON path."""
    paths: dict[tuple[Any, ...], str] = {}
    for prefix, agents in _agent_containers(data):
        if not isinstance(agents, dict):
            continue
        for name, agent in agents.items():
            if not isinstance(agent, dict):
                continue
            for suffix, value in _model_leaves(agent):
                paths[prefix + (name,) + suffix] = value
    # Legacy top-level agent blocks (e.g. {"oracle": {"model": ...}}).
    for name in AGENT_NAMES:
        agent = data.get(name)
        if isinstance(agent, dict):
            for suffix, value in _model_leaves(agent):
                paths[(name,) + suffix] = value
    return paths


def _base_of(path: tuple[Any, ...]) -> tuple[Any, ...]:
    """The agent entry path for a model/fallback/variant leaf path."""
    parts = list(path)
    for marker in ("model",) + FALLBACK_FIELDS:
        if marker in parts:
            return tuple(parts[: parts.index(marker)])
    return tuple(parts[:-1])


def is_primary(path: tuple[Any, ...]) -> bool:
    """True for a primary model value, never for a fallback-chain element."""
    if "model" not in path:
        return False
    tail = path[path.index("model") + 1 :]
    return not tail or tail == (0,) or tail == (0, "id")


def option_paths(data: dict[str, Any], key: str) -> dict[tuple[Any, ...], str]:
    """Editable existing variant or fallback fields, keyed by JSON path."""
    result: dict[tuple[Any, ...], str] = {}
    for model_path in model_paths(data):
        base = _base_of(model_path)
        item: Any = data
        for part in base:
            item = item[part]
        if not isinstance(item, dict):
            continue
        if key == "variant":
            if isinstance(item.get("variant"), str):
                result[base + ("variant",)] = item["variant"]
            value = item.get("model")
            if isinstance(value, list) and value and isinstance(value[0], dict):
                if isinstance(value[0].get("variant"), str):
                    result[base + ("model", 0, "variant")] = value[0]["variant"]
        elif key == "fallback":
            models_value = item.get("model")
            if isinstance(models_value, list):
                for index, entry in enumerate(models_value[1:], 1):
                    if isinstance(entry, str):
                        result[base + ("model", index)] = entry
                    elif isinstance(entry, dict) and isinstance(entry.get("id"), str):
                        result[base + ("model", index, "id")] = entry["id"]
            for field in FALLBACK_FIELDS:
                values = item.get(field)
                if isinstance(values, list):
                    for index, entry in enumerate(values):
                        if isinstance(entry, str):
                            result[base + (field, index)] = entry
    return result


def target_matches(path: tuple[Any, ...], requested: str) -> bool:
    base = _base_of(path)
    name = "/".join(map(str, base))
    return name == requested or base[-1] == requested or name.endswith("/" + requested)


# --------------------------------------------------------------------------- #
# Preset inheritance and effective model resolution
# --------------------------------------------------------------------------- #
def _preset_agents(preset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if isinstance(preset.get("agents"), dict):
        return {k: v for k, v in preset["agents"].items() if isinstance(v, dict)}
    return {
        k: v
        for k, v in preset.items()
        if isinstance(v, dict) and k not in ("extends", "marketplace")
    }


def preset_chain(data: dict[str, Any], preset_name: str | None = None) -> list[str]:
    """Resolve a preset's single-parent inheritance chain, ancestor first."""
    presets = data.get("presets")
    if not isinstance(presets, dict):
        return []
    name = preset_name or data.get("preset")
    chain: list[str] = []
    seen: set[str] = set()
    while isinstance(name, str) and name in presets:
        if name in seen:
            raise ValueError(f"Inheritance cycle detected in preset chain: {' -> '.join(chain + [name])}")
        seen.add(name)
        chain.append(name)
        preset = presets[name]
        name = preset.get("extends") if isinstance(preset, dict) else None
    return list(reversed(chain))


def effective_agents(data: dict[str, Any], preset_name: str | None = None) -> dict[str, dict[str, Any]]:
    """Resolve ancestor < child preset < root `agents` precedence."""
    presets = data.get("presets")
    resolved: dict[str, dict[str, Any]] = {}
    if isinstance(presets, dict):
        for name in preset_chain(data, preset_name):
            for agent_name, agent in _preset_agents(presets[name]).items():
                merged = dict(resolved.get(agent_name, {}))
                merged.update(agent)
                resolved[agent_name] = merged
    root = data.get("agents")
    if isinstance(root, dict):
        for agent_name, agent in root.items():
            if not isinstance(agent, dict):
                continue
            merged = dict(resolved.get(agent_name, {}))
            merged.update(agent)
            resolved[agent_name] = merged
    return resolved


def effective_model(entry: dict[str, Any]) -> str:
    """Human-readable primary model for an effective agent entry."""
    value = entry.get("model")
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict) and isinstance(first.get("id"), str):
            return first["id"]
    source = entry.get("inheritModelFrom")
    if source in ("session", "orchestrator"):
        return f"inherit:{source}"
    return "(unset)"


# --------------------------------------------------------------------------- #
# Safe writes: symlink-aware backups and atomic replacement
# --------------------------------------------------------------------------- #
def write_target() -> Path:
    """Follow a config symlink to its real target; fail closed if dangling."""
    path = CONFIG
    if path.is_symlink():
        try:
            return path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise RuntimeError(f"Cannot resolve configuration symlink {path}: {exc}") from exc
    return path


def backups() -> list[Path]:
    target = write_target()
    return sorted(target.parent.glob(target.name + ".bak.*"), reverse=True)


def backup_file() -> Path:
    target = write_target()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = target.with_name(target.name + ".bak." + stamp)
    shutil.copy2(target, destination)
    os.chmod(destination, 0o600)
    return destination


def atomic_write(content: str) -> None:
    """Write to a temp file, fsync, then atomically replace the target."""
    target = write_target()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=target.parent, prefix=".omo-model-", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        mode = target.stat().st_mode & 0o777 if target.exists() else 0o600
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _replace_value(source: str, spans: dict[tuple[Any, ...], tuple[int, int]], path: tuple[Any, ...], value: Any) -> str:
    start, end = spans[path]
    return source[:start] + json.dumps(value, ensure_ascii=False) + source[end:]


def edit_value(path: tuple[Any, ...], value: Any, yes: bool = False, dry_run: bool = False) -> bool:
    source, _ = read()
    spans = token_spans(source)
    if path not in spans:
        raise RuntimeError("Configuration field not found: " + ".".join(map(str, path)))
    old = json.loads(source[spans[path][0] : spans[path][1]])
    print(f'Change: {".".join(map(str, path))}: {old} -> {value}')
    if old == value:
        return True
    if dry_run:
        print("Dry run: unchanged")
        return True
    if not yes and input("Apply changes? [y/N]: ").strip().lower() != "y":
        return False
    updated = _replace_value(source, spans, path, value)
    parse(updated)
    saved = backup_file()
    try:
        atomic_write(updated)
        new_source, _ = read()
        new_spans = token_spans(new_source)
        start, end = new_spans[path]
        if json.loads(new_source[start:end]) != value:
            raise RuntimeError("Verification failed")
    except Exception:
        atomic_write(saved.read_text(encoding="utf-8"))
        raise
    print(f"Updated. Backup: {saved}")
    return True


def apply(
    model: str,
    agents: list[str] | None = None,
    categories: list[str] | None = None,
    all_entries: bool = False,
    yes: bool = False,
    dry_run: bool = False,
    known: list[str] | set[str] | None = None,
) -> bool:
    """Set the primary model of selected agents, preserving every fallback."""
    known = models() if known is None else set(known)
    if model not in known:
        raise RuntimeError(f"Model not in OpenCode registry: {model}")
    source, data = read()
    paths = model_paths(data)
    if not paths:
        raise RuntimeError("No agent/category model assignments found")
    agents = set(agents or [])
    categories = set(categories or [])
    if not all_entries and not agents and not categories:
        all_entries = True
    selected = {
        path: old
        for path, old in paths.items()
        if is_primary(path)
        and (
            all_entries
            or any(target_matches(path, name) for name in agents)
            or any(target_matches(path, name) for name in categories)
        )
    }
    for name in agents | categories:
        if not any(is_primary(path) and target_matches(path, name) for path in paths):
            raise RuntimeError(f"Unknown assignment: {name}")
    if not selected:
        raise RuntimeError("No matching primary assignments")
    edits = [(path, old) for path, old in selected.items() if old != model]
    print(f"\nChange preview: {len(edits)} of {len(selected)} selected assignments")
    for path, old in edits:
        print(f'  {".".join(map(str, path))}: {old} -> {model}')
    if not edits:
        print("✓ Already configured; no changes required")
        return True
    if dry_run:
        print("✓ Dry run: configuration unchanged")
        return True
    if not yes and input("Apply changes? [y/N]: ").strip().lower() != "y":
        print("Cancelled")
        return False
    spans = token_spans(source)
    missing = [path for path, _ in edits if path not in spans]
    if missing:
        raise RuntimeError(f"Unable to locate model values: {missing}")
    updated = source
    for start, end in sorted((spans[path] for path, _ in edits), reverse=True):
        updated = updated[:start] + json.dumps(model, ensure_ascii=False) + updated[end:]
    expected = dict(paths)
    expected.update({path: model for path, _ in edits})
    if model_paths(parse(updated)) != expected:
        raise RuntimeError("Pre-write verification failed")
    saved = backup_file()
    try:
        atomic_write(updated)
        if model_paths(read()[1]) != expected:
            raise RuntimeError("Post-write verification failed")
    except Exception:
        atomic_write(saved.read_text(encoding="utf-8"))
        raise
    print(f"✓ Updated {len(edits)} assignments; JSONC preserved and verified")
    print(f"✓ Backup: {saved}")
    print("Restart OpenCode to apply changes.")
    return True


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #
def verify() -> int:
    _, data = read()
    paths = dict(model_paths(data))
    for key, value in option_paths(data, "fallback").items():
        paths[key] = value
    if not paths:
        raise RuntimeError("No model assignments found")
    known = set(models())
    failed = 0
    for path, model in paths.items():
        ok = model in known
        print(f'{"✓" if ok else "✗"} {".".join(map(str, path))}: {model}')
        failed += not ok
    print(f"{len(paths)} assignments; {failed} unavailable model IDs (registry check only).")
    return 1 if failed else 0


def doctor(full: bool = False) -> int:
    failed = 0
    if shutil.which("opencode"):
        print("✓ OpenCode")
    else:
        failed += 1
        print("✗ OpenCode: not installed")
    config_ok = False
    try:
        read()
        config_ok = True
        print(f"✓ Slim configuration ({CONFIG})")
    except Exception as exc:
        failed += 1
        print(f"✗ Slim configuration: {exc}")
    known: set[str] | None = None
    try:
        known = set(models())
        print(f"✓ Model discovery ({len(known)} models)")
    except Exception as exc:
        failed += 1
        print(f"✗ Model discovery: {exc}")
    if config_ok and known is not None:
        data = read()[1]
        paths = dict(model_paths(data))
        paths.update(option_paths(data, "fallback"))
        missing = [(path, model) for path, model in paths.items() if model not in known]
        if missing:
            failed += 1
            print(f"✗ Model availability ({len(missing)} unknown of {len(paths)} assignments)")
            for path, model in missing:
                print(f'    {".".join(map(str, path))}: {model}')
        else:
            print(f"✓ Model availability ({len(paths)} assignments found)")
    else:
        print("– Model availability: skipped (requires valid config and model list)")
    try:
        providers = auth_providers()
        print(f'✓ Authentication discovery ({", ".join(sorted(providers)) or "none"})')
    except Exception as exc:
        failed += 1
        print(f"✗ Authentication discovery: {exc}")
    try:
        import opencode_manage as oc

        print(f"✓ OpenCode configuration ({oc.config_path()})")
    except Exception as exc:
        failed += 1
        print(f"✗ OpenCode configuration: {exc}")
    if full:
        if shutil.which("bunx"):
            print("\nRunning official Oh My OpenCode Slim doctor…")
            try:
                print(run("bunx", "oh-my-opencode-slim", "doctor", timeout=120))
            except Exception as exc:
                failed += 1
                print(f"✗ Official doctor: {exc}")
        else:
            print("⚠ bunx not found; official doctor skipped")
    return 1 if failed else 0


def restore(content: str, yes: bool = False) -> bool:
    if not isinstance(parse(content), dict):
        raise RuntimeError("Invalid backup")
    if not yes and input("Restore this backup? [y/N]: ").strip().lower() != "y":
        return False
    previous = backup_file()
    try:
        atomic_write(content)
        read()
    except Exception:
        atomic_write(previous.read_text(encoding="utf-8"))
        raise
    print(f"✓ Restored configuration; previous state saved at {previous}")
    return True
