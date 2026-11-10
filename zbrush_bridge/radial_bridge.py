"""Radial menu bridge — runs INSIDE ZBrush 2026 (Python).

ZBRUSH 2026 ONLY. For ZBrush 2023/2024 use zscript/RadialBridge.txt.
In the config, use "protocol": "python" with this bridge.

How to use:
    ZBrush > ZScript > Python Scripting > Load > pick this file.

The script creates the ZPlugin > Radial Bridge subpalette with a "Run" button.
Assign it the same hotkey as in the config (trigger_hotkey):
    Ctrl+Alt+click the "Run" button and press the hotkey.

When the external app writes zbrush_bridge/data/command.json and presses the
hotkey, the button reads the command, runs it and deletes the file. The result
goes to zbrush_bridge/data/last_result.json and to ZBrush's Python console.

This file depends on nothing outside the standard library + zbrush.
"""

from __future__ import annotations

import json
import os
import time
import traceback

try:
    from zbrush import commands as zbc  # only exists inside ZBrush
except ImportError:  # allows importing in tests
    zbc = None

# Same folder as the default "command_dir" in the config: <project>/zbrush_bridge/data
COMMAND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
COMMAND_FILE = os.path.join(COMMAND_DIR, "command.json")
RESULT_FILE = os.path.join(COMMAND_DIR, "last_result.json")

SUBPALETTE = "ZPlugin:Radial Bridge"
RUN_BUTTON = f"{SUBPALETTE}:Run"
TEST_BUTTON = f"{SUBPALETTE}:Test"

# Item path of the Load Brush button. VERIFY in Phase 0
# (phase0/03_load_brush_file.py) — if the name is different, adjust it here.
LOAD_BRUSH_ITEM = "Brush:Load Brush"

# Commands older than 10 s are considered stale and ignored.
MAX_COMMAND_AGE_S = 10.0


class BridgeError(Exception):
    pass


def execute_action(action: dict, api=None) -> str:
    """Runs an action and returns a short description of what it did."""
    api = api or zbc
    if api is None:
        raise BridgeError("ZBrush API unavailable (run inside ZBrush)")

    atype = action.get("type")
    if atype == "press":
        item = action["item"]
        if not api.exists(item):
            raise BridgeError(f"item does not exist in the interface: {item}")
        api.press(item)
        return f"press {item}"

    if atype == "brush_file":
        path = action["path"]
        if not os.path.isfile(path):
            raise BridgeError(f"brush file not found: {path}")
        if not api.exists(LOAD_BRUSH_ITEM):
            raise BridgeError(f"Load Brush button not found: {LOAD_BRUSH_ITEM}")
        api.set_next_filename(path)
        api.press(LOAD_BRUSH_ITEM)
        return f"load {os.path.basename(path)}"

    raise BridgeError(f"action type not supported by the bridge: {atype!r}")


def read_command(path: str = COMMAND_FILE, now: float | None = None) -> dict | None:
    """Reads and deletes the pending command. Returns None if there is no valid command."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    now = time.time() if now is None else now
    if now - float(payload.get("created", 0)) > MAX_COMMAND_AGE_S:
        return None
    return payload


def write_result(result: dict, path: str = RESULT_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)


def run_pending(api=None, command_path: str = COMMAND_FILE,
                result_path: str = RESULT_FILE) -> dict:
    """Reads the pending command, runs the actions and writes the result."""
    result = {"time": time.time(), "ok": True, "done": [], "errors": []}
    try:
        payload = read_command(command_path)
    except (OSError, ValueError) as exc:
        payload = None
        result["errors"].append(f"unreadable command: {exc}")
    if payload is None:
        if not result["errors"]:
            result["errors"].append("no pending command (or stale command)")
        result["ok"] = False
    else:
        result["id"] = payload.get("id")
        for action in payload.get("actions", []):
            try:
                result["done"].append(execute_action(action, api))
            except Exception as exc:  # noqa: BLE001 — report any failure
                result["ok"] = False
                result["errors"].append(f"{action!r}: {exc}")
    write_result(result, result_path)
    return result


# --- interface inside ZBrush ------------------------------------------

def _on_run(item: str) -> None:
    try:
        result = run_pending()
        tag = "ok" if result["ok"] else "ERROR"
        print(f"[radial-bridge] {tag}: {result['done']} {result['errors']}")
    except Exception:  # noqa: BLE001
        print("[radial-bridge] unexpected failure:\n" + traceback.format_exc())


def _on_test(item: str) -> None:
    """Test button: presses the Move brush through the bridge, without the external app."""
    try:
        print("[radial-bridge] test:", execute_action({"type": "press", "item": "Brush:Move"}))
    except Exception as exc:  # noqa: BLE001
        print(f"[radial-bridge] test failed: {exc}")


def install() -> None:
    os.makedirs(COMMAND_DIR, exist_ok=True)
    if not zbc.exists(SUBPALETTE):
        zbc.add_subpalette(SUBPALETTE)
    if not zbc.exists(RUN_BUTTON):
        zbc.add_button(RUN_BUTTON, "Runs the radial menu command. "
                       "Assign the hotkey with Ctrl+Alt+click.", _on_run, width=0.5)
    if not zbc.exists(TEST_BUTTON):
        zbc.add_button(TEST_BUTTON, "Test: selects the Move brush.", _on_test, width=0.5)
    print(f"[radial-bridge] installed in {SUBPALETTE}. Command folder: {COMMAND_DIR}")


# Does not depend on __name__: it is not documented how ZBrush executes the file.
if zbc is not None:
    install()
