"""Curses terminal UI for OMO Manager.

One curses session covers every screen: no terminal handoffs, no numeric
shortcuts, no "press Enter to continue" screens. Arrow keys navigate, Enter
selects, Esc returns, and searchable lists filter as you type.
"""

from __future__ import annotations

import contextlib
import curses
import io
import json
import os
import shlex
import sys
from typing import Any, Callable

import omo_model_slim as slim

ACTIONS = [
    "Dashboard / overview",
    "Configure all agent models",
    "Configure individual agents",
    "Manage presets",
    "Browse and search models",
    "Manage variants",
    "Manage model fallbacks",
    "Custom providers and models",
    "MCP servers",
    "Default OpenCode model",
    "Verify assignments",
    "Doctor",
    "Backup and restore",
    "Refresh model catalog",
    "Exit",
]
MIN_HEIGHT, MIN_WIDTH = 7, 30

# A menu draws a title, a count row, and a blank row above the options. All
# three must be reserved or the highlighted option gets clipped at the bottom.
def menu_capacity(height: int, header_lines: int) -> int:
    return max(1, height - 5 - header_lines - 2)


def preset_agent_target(preset_name: str, preset: dict, agent_name: str) -> str:
    """Build the editable target path for either supported preset shape."""
    base = f"presets/{preset_name}"
    if isinstance(preset, dict) and isinstance(preset.get("agents"), dict):
        base += "/agents"
    return f"{base}/{agent_name}"


def _clear() -> None:
    if sys.stdout.isatty() and not os.environ.get("OMO_NO_CLEAR"):
        print("\033[H\033[2J\033[3J", end="", flush=True)


def _capture(fn: Callable[[], Any]) -> str:
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            fn()
        return output.getvalue()
    except Exception as exc:  # surfaced in the viewer, not raised through curses
        return output.getvalue() + f"\n✗ {exc}"


def run_tui() -> None:
    """Run the full-screen UI, restoring the terminal on exit or error."""
    import opencode_manage as oc

    state: dict[str, Any] = {"known": [], "providers": set(), "error": None}

    def app(win: Any) -> None:  # curses window
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        win.keypad(True)
        try:
            curses.use_default_colors()
        except curses.error:
            pass

        def put(row: int, value: str, attr: int = 0) -> None:
            height, width = win.getmaxyx()
            if not 0 <= row < height:
                return
            try:
                win.addnstr(row, 1, str(value), max(1, width - 3), attr)
            except curses.error:
                pass

        def draw(lines: list[str], footer: str = "", selected: int | None = None, top: int = 0) -> int:
            win.erase()
            height, _ = win.getmaxyx()
            if height < MIN_HEIGHT or win.getmaxyx()[1] < MIN_WIDTH:
                try:
                    win.addnstr(0, 0, "Enlarge terminal (min 30x7). Esc to exit.", max(1, win.getmaxyx()[1] - 1))
                except curses.error:
                    pass
                win.refresh()
                return 0
            capacity = height - 5
            put(0, f" OMO MANAGER  ·  v{slim.VERSION}", curses.A_BOLD)
            put(1, "─" * max(1, win.getmaxyx()[1] - 3))
            for index, line in enumerate(lines[top : top + capacity]):
                attr = curses.A_REVERSE | curses.A_BOLD if selected == top + index else 0
                put(index + 2, (" ❯ " if selected == top + index else "   ") + line, attr)
            put(height - 2, "─" * max(1, win.getmaxyx()[1] - 3))
            put(height - 1, footer)
            win.refresh()
            return capacity

        def menu(title: str, options: list[str], footer: str = "", searchable: bool = False) -> int | None:
            query, selected, top = "", 0, 0
            while True:
                filtered = [(i, str(item)) for i, item in enumerate(options) if query.casefold() in str(item).casefold()]
                selected = min(selected, max(0, len(filtered) - 1))
                height = win.getmaxyx()[0]
                header = title.splitlines()
                capacity = menu_capacity(height, len(header))
                top = max(0, min(selected - capacity + 1, max(0, len(filtered) - capacity)))
                lines = list(header) + [
                    f"{len(filtered)} items" + (f"  ·  filter: {query}" if query else ""),
                    "",
                ] + [label for _, label in filtered[top : top + capacity]]
                highlighted = selected - top + len(header) + 2 if filtered else None
                hint = footer + ("  ·  type to filter" if searchable else "")
                draw(lines, hint, selected=highlighted)
                key = win.get_wch()
                if key == "\x1b":
                    if query:
                        query, selected, top = "", 0, 0
                    else:
                        return None
                elif key in ("\n", "\r", curses.KEY_ENTER):
                    if filtered:
                        return filtered[selected][0]
                elif key == curses.KEY_UP:
                    selected = max(0, selected - 1)
                elif key == curses.KEY_DOWN:
                    selected = min(len(filtered) - 1, selected + 1)
                elif key == curses.KEY_NPAGE:
                    selected = min(len(filtered) - 1, selected + capacity)
                elif key == curses.KEY_PPAGE:
                    selected = max(0, selected - capacity)
                elif key == curses.KEY_HOME:
                    selected = 0
                elif key == curses.KEY_END:
                    selected = max(0, len(filtered) - 1)
                elif key in (curses.KEY_BACKSPACE, "\x7f", "\b") and searchable:
                    query, selected, top = query[:-1], 0, 0
                elif searchable and isinstance(key, str) and key.isprintable():
                    query += key
                    selected, top = 0, 0

        def viewer(title: str, message: str) -> None:
            lines = [title, ""] + str(message).splitlines()
            offset = 0
            while True:
                height = win.getmaxyx()[0]
                capacity = max(1, height - 5)
                draw(lines, "↑↓ scroll  ·  PgUp/PgDn  ·  Esc/Enter back", top=offset)
                key = win.get_wch()
                if key in ("\x1b", "q", "\n", "\r", curses.KEY_ENTER):
                    return
                if key == curses.KEY_DOWN:
                    offset = min(max(0, len(lines) - capacity), offset + 1)
                elif key == curses.KEY_UP:
                    offset = max(0, offset - 1)
                elif key == curses.KEY_NPAGE:
                    offset = min(max(0, len(lines) - capacity), offset + capacity)
                elif key == curses.KEY_PPAGE:
                    offset = max(0, offset - capacity)

        def confirm(title: str, details: str) -> bool:
            choice = menu(title + "\n" + details, ["No, go back", "Yes, apply changes"], "↑↓ choose  ·  Enter confirm  ·  Esc cancel")
            return choice == 1

        def ask(prompt: str, default: str = "") -> str | None:
            value = str(default)
            try:
                curses.curs_set(1)
            except curses.error:
                pass
            try:
                while True:
                    draw([prompt, "", value], "Type value  ·  Enter save  ·  Esc cancel")
                    key = win.get_wch()
                    if key == "\x1b":
                        return None
                    if key in ("\n", "\r", curses.KEY_ENTER):
                        return value.strip()
                    if key in ("\x7f", "\b", curses.KEY_BACKSPACE):
                        value = value[:-1]
                    elif isinstance(key, str) and key.isprintable():
                        value += key
            finally:
                try:
                    curses.curs_set(0)
                except curses.error:
                    pass

        def ask_json(prompt: str, original: Any = None) -> dict[str, Any] | None:
            raw = ask(prompt + " (JSON object)", json.dumps(original if original is not None else {}, ensure_ascii=False))
            if raw is None:
                return None
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                raise ValueError("Expected a JSON object")
            return obj

        def refresh() -> None:
            draw(["Discovering models and authentication…"], "Please wait")
            try:
                state["known"] = slim.models()
                state["error"] = None
            except Exception as exc:
                state["known"] = []
                state["error"] = str(exc)
            try:
                state["providers"] = slim.auth_providers()
            except Exception:
                state["providers"] = set()

        def ordered_models() -> tuple[list[str], list[str], list[str]]:
            known = state["known"]
            providers = state["providers"]
            free = [m for m in known if slim.free_model(m)]
            auth = [m for m in known if m not in free and m.split("/", 1)[0].lower() in providers]
            other = [m for m in known if m not in free and m not in auth]
            return free, auth, other

        def picker(title: str, pool: list[str] | None = None) -> int | None:
            free, auth, other = ordered_models()
            choices = pool if pool is not None else free + auth + other
            return menu(
                title,
                choices,
                "↑↓ navigate  ·  Enter select  ·  Esc back  ·  type to search",
                searchable=True,
            )

        def do_apply(model: str, targets: list[str] | None = None, all_entries: bool = False) -> bool:
            count = len(slim.model_paths(slim.read()[1])) if all_entries else len(targets or [])
            if not confirm("Confirm model change", f"Model: {model}\nTargets: {count} assignment(s)"):
                return False
            message = _capture(
                lambda: slim.apply(
                    model,
                    agents=targets,
                    all_entries=all_entries,
                    yes=True,
                    known=state["known"],
                )
            )
            viewer("Apply result", message)
            return "✓ Updated" in message or "no changes required" in message

        def assignments() -> list[tuple[str, str]]:
            paths = slim.model_paths(slim.read()[1])
            return [
                ("/".join(map(str, slim._base_of(path))), model)
                for path, model in paths.items()
                if slim.is_primary(path)
            ]

        def dashboard() -> None:
            try:
                _, data = slim.read()
                paths = slim.model_paths(data)
                used = sorted(set(paths.values()))
                free, auth, other = ordered_models()
                effective = slim.effective_agents(data)
                rows = [
                    "DASHBOARD",
                    "",
                    f"Config:      {slim.CONFIG}",
                    f"Active preset: {data.get('preset', '(none)')}",
                    f"Assignments: {len(paths)}  ·  Models in use: {len(used)}",
                    f"Catalog:     {len(free)} free  ·  {len(auth)} authenticated  ·  {len(other)} other",
                    f"Effective agents resolved: {len(effective)}",
                    "",
                    "Models in use:",
                    *(f"  {model}" for model in used[:12]),
                ]
                if state["error"]:
                    rows += ["", f"Catalog warning: {state['error']}"]
            except Exception as exc:
                rows = ["DASHBOARD", "", f"Configuration error: {exc}"]
            viewer("Dashboard / overview", "\n".join(rows))

        def show_effective(preset_name: str | None = None) -> None:
            _, data = slim.read()
            chain = slim.preset_chain(data, preset_name)
            agents = slim.effective_agents(data, preset_name)
            rows = [f"Inheritance: {' < '.join(chain) if chain else '(none)'}", ""]
            rows += [f"{' '.join(name.split()).ljust(14)} {slim.effective_model(entry)}" for name, entry in agents.items()]
            viewer("Effective model resolution", "\n".join(rows))

        def set_all() -> None:
            index = picker("Set model for ALL agents")
            if index is not None and do_apply((ordered_models()[0] + ordered_models()[1] + ordered_models()[2])[index], all_entries=True):
                return

        def set_one() -> None:
            while True:
                targets = assignments()
                if not targets:
                    viewer("Configure one agent", "No model assignments found.")
                    return
                index = menu("Configure one agent", [f"{name}  [{model}]" for name, model in targets], searchable=True)
                if index is None:
                    return
                name, old = targets[index]
                chosen = picker(f"Model for {name} (current: {old})")
                if chosen is None:
                    continue
                pool = ordered_models()[0] + ordered_models()[1] + ordered_models()[2]
                do_apply(pool[chosen], targets=[name])

        def manage_presets() -> None:
            while True:
                _, data = slim.read()
                presets = data.get("presets")
                if not isinstance(presets, dict) or not presets:
                    viewer("Manage presets", "No presets defined in this configuration.")
                    return
                names = sorted(presets)
                index = menu("Manage presets", ["View effective resolution"] + names)
                if index is None:
                    return
                if index == 0:
                    show_effective()
                    continue
                preset_name = names[index - 1]
                agents = sorted(slim._preset_agents(presets[preset_name]))
                if not agents:
                    viewer("Manage presets", f"Preset '{preset_name}' has no direct agents.")
                    continue
                agent_index = menu(f"Preset: {preset_name}", agents, searchable=True)
                if agent_index is None:
                    continue
                agent_name = agents[agent_index]
                chosen = picker(f"Model for {preset_name}/{agent_name}")
                if chosen is None:
                    continue
                pool = ordered_models()[0] + ordered_models()[1] + ordered_models()[2]
                do_apply(pool[chosen], targets=[preset_agent_target(preset_name, presets[preset_name], agent_name)])

        def browse() -> None:
            free, auth, other = ordered_models()
            pools = [free, auth, other, free + auth + other]
            category = menu("Browse model catalog", [f"Free-labeled ({len(free)})", f"Authenticated ({len(auth)})", f"Other ({len(other)})", f"All ({len(pools[3])})"])
            if category is None:
                return
            pool = pools[category]
            chosen = picker("Browse models", pool)
            if chosen is not None and confirm("Selected model", f"{pool[chosen]}\nApply to ALL assignments?"):
                do_apply(pool[chosen], all_entries=True)

        def manage_fields(field: str) -> None:
            _, data = slim.read()
            entries = list(slim.option_paths(data, field).items())
            if not entries:
                viewer("Manage " + field, f"No existing {field} fields found; unsupported fields are not added automatically.")
                return
            index = menu(f"Choose {field}", [f'{".".join(map(str, path))}  [{value}]' for path, value in entries], searchable=True)
            if index is None:
                return
            path, old = entries[index]
            if field == "fallback":
                pool = ordered_models()[0] + ordered_models()[1] + ordered_models()[2]
                chosen = picker("Select fallback", pool)
                if chosen is None:
                    return
                value: Any = pool[chosen]
            else:
                values = sorted({"none", "low", "medium", "high", "xhigh", "max", old})
                chosen = menu("Select variant", values)
                if chosen is None:
                    return
                value = values[chosen] if values[chosen] != "none" else ""
            if confirm("Confirm change", f"{old} -> {value}"):
                viewer("Change result", _capture(lambda: slim.edit_value(path, value, yes=True)))

        def manage_opencode(section: str) -> None:
            import opencode_manage as manager

            while True:
                _, data = manager.load()
                group = data.get(section, {})
                if not isinstance(group, dict):
                    raise ValueError("Invalid " + section + " configuration")
                keys = sorted(group)
                labels = [
                    f"{key}  [{'enabled' if group[key].get('enabled', True) else 'disabled'}]"
                    if section == "mcp" and isinstance(group[key], dict)
                    else key
                    for key in keys
                ]
                index = menu(f"OpenCode {section}\n{manager.config_path()}", ["+ Add new"] + labels, searchable=True)
                if index is None:
                    return
                if index == 0:
                    name = ask("New " + section + " ID")
                    if not name:
                        continue
                    if name in group:
                        viewer("Already exists", name)
                        continue
                    if section == "mcp":
                        kind = menu("MCP type", ["Local command", "Remote URL"])
                        if kind is None:
                            continue
                        if kind == 0:
                            command = ask("Command (space-separated; no shell interpretation)")
                            if not command:
                                continue
                            entry: dict[str, Any] = {"type": "local", "command": shlex.split(command)}
                        else:
                            url = ask("Remote MCP URL (https://)")
                            if not url or not url.startswith("https://"):
                                viewer("Invalid URL", "Use https://")
                                continue
                            entry = {"type": "remote", "url": url}
                    else:
                        base = ask("Provider base URL (optional)")
                        entry = {"npm": "@ai-sdk/openai-compatible", "options": {"baseURL": base}} if base else {"models": {}}
                    if confirm("Save new " + section, json.dumps(entry, indent=2)):
                        viewer("Saved", str(manager.mutate(section, name, entry)))
                    continue
                name = keys[index - 1]
                entry = group[name]
                choices = ["Edit JSON", "Delete"]
                if section == "mcp":
                    choices.insert(1, "Enable / disable")
                if section == "provider":
                    choices.insert(1, "Manage custom models")
                action = menu(name + "\n" + json.dumps(entry, ensure_ascii=False, indent=2), choices)
                if action is None:
                    continue
                choice = choices[action]
                if choice == "Manage custom models":
                    while True:
                        _, data = manager.load()
                        custom = data.get("provider", {}).get(name, {}).get("models", {})
                        names = sorted(custom)
                        model_index = menu(name + " / custom models", ["+ Add model"] + names, searchable=True)
                        if model_index is None:
                            break
                        if model_index == 0:
                            model_id = ask("Model ID")
                            if not model_id:
                                continue
                            definition = ask_json("Model definition", {"name": model_id})
                            if definition is not None and confirm("Add model", model_id):
                                viewer("Saved", str(manager.provider_model(name, model_id, definition)))
                        else:
                            model_id = names[model_index - 1]
                            act = menu(model_id, ["Edit JSON", "Delete"])
                            if act == 0:
                                definition = ask_json("Edit model", custom[model_id])
                                if definition is not None and confirm("Save model", model_id):
                                    viewer("Saved", str(manager.provider_model(name, model_id, definition)))
                            elif act == 1 and confirm("Delete model", model_id):
                                viewer("Deleted", str(manager.provider_model(name, model_id, operation="delete")))
                elif choice == "Edit JSON":
                    edited = ask_json("Edit " + name, entry)
                    if edited is not None and confirm("Save changes", name):
                        viewer("Saved", str(manager.mutate(section, name, edited)))
                elif choice == "Enable / disable":
                    if confirm("Toggle MCP", name):
                        viewer("Updated", str(manager.mutate(section, name, operation="toggle")))
                elif choice == "Delete" and confirm("Delete " + section, name):
                    viewer("Deleted", str(manager.mutate(section, name, operation="delete")))

        def default_model() -> None:
            import opencode_manage as manager

            source, data = manager.load()
            old = data.get("model", "(unset)")
            mode = menu(f"OpenCode default model: {old}", ["Choose discovered model", "Enter model ID manually"])
            if mode is None:
                return
            if mode == 0:
                index = picker("Default model", state["known"])
                if index is None:
                    return
                model = state["known"][index]
            else:
                model = ask("Default model ID (provider/model)") or ""
            if not model:
                return
            if confirm("Set OpenCode default", f"{old} -> {model}"):
                viewer("Saved", str(manager.save_section("model", model, yes=True)))

        def backup_restore() -> None:
            available = slim.backups()
            if not available:
                viewer("Backup and restore", "No backups found. Changes are backed up automatically before each write.")
                return
            index = menu("Backup and restore", [f"Restore: {path.name}" for path in available], searchable=True)
            if index is None:
                return
            chosen = available[index]
            if confirm("Restore backup", chosen.name):
                viewer("Backup restored", _capture(lambda: slim.restore(chosen.read_text(encoding="utf-8"), yes=True)))

        refresh()
        while True:
            try:
                _, data = slim.read()
                paths = slim.model_paths(data)
                status = f"{len(paths)} assignments  ·  {len(set(paths.values()))} models in use"
                current = ", ".join(sorted(set(paths.values()))[:2])
            except Exception as exc:
                status, current = f"Config error: {exc}", ""
            free, auth, other = ordered_models()
            header = "\n".join(
                [
                    "OMO MANAGER — Oh My OpenCode Slim",
                    "",
                    f"Config:  {slim.CONFIG}",
                    f"Status:  {status}",
                    f"Catalog: {len(free)} free  ·  {len(auth)} authenticated  ·  {len(other)} other",
                    *(["Catalog warning: " + state["error"]] if state["error"] else []),
                    f"Current: {current}",
                    "",
                    "CHOOSE AN ACTION",
                    "",
                ]
            )
            index = menu(header, ACTIONS, "↑↓ navigate  ·  Enter select  ·  Esc back")
            if index is None or index == len(ACTIONS) - 1:
                return
            handlers = {
                0: dashboard,
                1: set_all,
                2: set_one,
                3: manage_presets,
                4: browse,
                5: lambda: manage_fields("variant"),
                6: lambda: manage_fields("fallback"),
                7: lambda: manage_opencode("provider"),
                8: lambda: manage_opencode("mcp"),
                9: default_model,
                10: lambda: viewer("Verify assignments", _capture(slim.verify)),
                11: lambda: viewer("Doctor", _capture(slim.doctor)),
                12: backup_restore,
                13: lambda: (refresh(), viewer("Catalog refreshed", state["error"] or f"{len(state['known'])} models discovered")),
            }
            try:
                handlers[index]()
            except Exception as exc:
                viewer("Error", str(exc))

    _clear()
    try:
        curses.wrapper(app)
    except (KeyboardInterrupt, EOFError):
        pass
    except (curses.error, OSError):
        sys.stderr.write("Curses UI unavailable; use the CLI subcommands. See --help.\n")
    finally:
        _clear()


def run_basic() -> None:
    """Minimal fallback for non-interactive terminals without curses."""
    while True:
        print(f"OMO Manager v{slim.VERSION}  ·  {slim.CONFIG}")
        print("Actions: dashboard, all, agent, preset, browse, variant, fallback,")
        print("         provider, mcp, default, verify, doctor, backup, refresh, exit")
        answer = input("Action (or 'exit') › ").strip().lower()
        try:
            if answer in ("", "exit", "q"):
                return
            elif answer == "dashboard":
                _, data = slim.read()
                print(slim.effective_agents(data))
            elif answer == "all":
                model = input("Model ID › ").strip()
                slim.apply(model, all_entries=True, known=slim.models())
            elif answer in ("agent", "preset"):
                name = input("Assignment path › ").strip()
                model = input("Model ID › ").strip()
                slim.apply(model, agents=[name], known=slim.models())
            elif answer == "browse":
                keyword = input("Search › ").strip().lower()
                for model in slim.models():
                    if keyword in model.lower():
                        print(model)
            elif answer in ("variant", "fallback"):
                paths = slim.option_paths(slim.read()[1], answer)
                for path, value in paths.items():
                    print(".".join(map(str, path)), value)
                target = input("Field path › ").strip()
                path = next((p for p in paths if ".".join(map(str, p)) == target), None)
                if path:
                    slim.edit_value(path, input("New value › ").strip())
            elif answer == "verify":
                slim.verify()
            elif answer == "doctor":
                slim.doctor()
            elif answer == "backup":
                for path in slim.backups():
                    print(path)
            elif answer == "refresh":
                print(f"{len(slim.models())} models discovered")
            else:
                print("Unknown action.")
        except Exception as exc:
            print(f"✗ {exc}", file=sys.stderr)


def interactive() -> None:
    if sys.stdin.isatty() and sys.stdout.isatty() and not os.environ.get("OMO_BASIC_UI"):
        try:
            run_tui()
            return
        except ImportError:
            pass
    run_basic()
