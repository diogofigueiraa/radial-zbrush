"""Outside half of the bridge: writes the command to disk and "wakes" ZBrush.

Two possible bridges (bridge.protocol in the config):

- "zscript" (ZBrush 2023/2024): zbrush_bridge/zscript/RadialBridge.txt
    <command_dir>/command.txt with ONE line:  press|Brush:Move  or  load|C:/x/Clay.ZBP

- "python" (ZBrush 2026): zbrush_bridge/radial_bridge.py
    <command_dir>/command.json  {"id": ..., "created": ..., "actions": [...]}

After writing, the app presses `trigger_hotkey`, which in ZBrush is assigned to
the ZPlugin > Radial Bridge > Run button. The button reads the file, runs it and
deletes it.

Why this design: neither ZScript nor ZBrush's Python API can "listen" in the
background. Code in ZBrush runs from a button.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

from .config import PROJECT_ROOT

JSON_COMMAND_FILE = "command.json"
TEXT_COMMAND_FILE = "command.txt"
RESULT_FILE = "last_result.json"

BRIDGE_ACTIONS = {"press", "brush_file"}
ZSCRIPT_KINDS = {"press": ("press", "item"), "brush_file": ("load", "path")}
ZSCRIPT_MAX_LINE = 250  # MemReadString reads at most 255 characters


class BridgeCommandError(ValueError):
    pass


def command_dir(raw: str) -> Path:
    """Expands ~ and variables; a relative path is relative to the project root."""
    path = Path(os.path.expandvars(os.path.expanduser(raw)))
    return path if path.is_absolute() else PROJECT_ROOT / path


def _atomic_write(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, target)


def zscript_line(action: dict) -> str:
    """Turns an action into the line RadialBridge.txt understands."""
    atype = action.get("type")
    if atype not in ZSCRIPT_KINDS:
        raise BridgeCommandError(f"action {atype!r} does not go through the bridge")
    kind, field = ZSCRIPT_KINDS[atype]
    arg = str(action[field])
    if atype == "brush_file":
        arg = arg.replace("\\", "/")
    line = f"{kind}|{arg}"
    if "\n" in line or "\r" in line:
        raise BridgeCommandError("the command cannot contain line breaks")
    if len(line) > ZSCRIPT_MAX_LINE:
        raise BridgeCommandError(
            f"command is {len(line)} characters long; ZScript reads at most {ZSCRIPT_MAX_LINE}"
        )
    if not line.isascii():
        raise BridgeCommandError(
            "use only ASCII characters (no accents) in the path or item path: "
            "ZScript may not read the text correctly"
        )
    return line


def write_command(directory: Path, actions: list[dict], protocol: str = "zscript") -> Path:
    """Writes the command atomically and returns the file path."""
    if protocol == "zscript":
        if len(actions) != 1:
            raise BridgeCommandError("the ZScript bridge runs one action at a time")
        target = directory / TEXT_COMMAND_FILE
        _atomic_write(target, zscript_line(actions[0]))
        return target
    if protocol == "python":
        payload = {"id": uuid.uuid4().hex, "created": time.time(), "actions": actions}
        target = directory / JSON_COMMAND_FILE
        _atomic_write(target, json.dumps(payload, ensure_ascii=False))
        return target
    raise BridgeCommandError(f"unknown protocol: {protocol!r}")


def read_result(directory: Path) -> dict | None:
    try:
        return json.loads((directory / RESULT_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class ActionRunner:
    """Runs a slot's action.

    - press / brush_file: go through the bridge in ZBrush.
    - keys: the app only presses keys (native ZBrush shortcuts).
    """

    def __init__(
        self,
        cfg_bridge: dict,
        send_keys: Callable[[str], None],
        wait_modifiers_released: Callable[[float], None],
        ensure_focus: Callable[[], bool] | None = None,
        confirm_timeout: float = 1.5,
    ):
        self.directory = command_dir(cfg_bridge["command_dir"])
        self.trigger = cfg_bridge["trigger_hotkey"]
        self.protocol = cfg_bridge.get("protocol", "zscript")
        self._send_keys = send_keys
        self._wait_mods = wait_modifiers_released
        self._focus = ensure_focus
        self.confirm_timeout = confirm_timeout

    def run(self, action: dict) -> None:
        # On a separate thread so the menu UI doesn't freeze.
        threading.Thread(target=self._run, args=(action,), daemon=True).start()

    def _run(self, action: dict) -> None:
        # If the user is still holding Alt/Ctrl/Shift from the menu hotkey, ZBrush
        # would receive a different combo. Wait for release (up to 0.6 s).
        self._wait_mods(0.6)
        atype = action.get("type")
        try:
            if atype == "keys":
                self._ensure_focus()
                self._send_keys(action["keys"])
                print(f"[radial] keys sent: {action['keys']}")
            elif atype in BRIDGE_ACTIONS:
                path = write_command(self.directory, [action], self.protocol)
                self._ensure_focus()
                self._send_keys(self.trigger)
                self._report_bridge(path)
            else:
                print(f"[radial] unknown action: {action!r}")
        except BridgeCommandError as exc:
            print(f"[radial] command rejected: {exc}")

    def _ensure_focus(self) -> None:
        if self._focus is not None:
            self._focus()

    def _report_bridge(self, path: Path) -> None:
        """The bridge deletes the file when it reads it. If it is still there,
        the hotkey never arrived."""
        deadline = time.monotonic() + self.confirm_timeout
        while time.monotonic() < deadline:
            if not path.exists():
                print("[radial] bridge ran the command")
                return
            time.sleep(0.05)
        print("[radial] WARNING: ZBrush did not read the command. The hotkey "
              f"{self.trigger} did not reach the Run button. Check that ZBrush "
              "is focused and that the Run hotkey is assigned.")
