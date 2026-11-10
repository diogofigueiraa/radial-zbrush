"""Loading and validation of config/menus.json.

The JSON file is the source of truth. Missing values get the defaults below.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "menus.json"

VALID_ACTIONS = {"press", "brush_file", "keys"}
VALID_MODES = {"hold", "toggle"}
VALID_PROTOCOLS = {"zscript", "python"}

DEFAULTS: dict[str, Any] = {
    "bridge": {
        # "zscript" for ZBrush 2023/2024, "python" for ZBrush 2026.
        "protocol": "zscript",
        # Hotkey the app presses to fire the bridge's "Run" button in ZBrush.
        # Must be the SAME hotkey assigned to ZPlugin > Radial Bridge > Run.
        "trigger_hotkey": "<ctrl>+<alt>+<shift>+j",
        # Folder where the app writes the command and the bridge reads it.
        # Relative to the project root. In the ZScript bridge the same folder
        # is set in rbDir (RadialBridge.txt).
        "command_dir": "zbrush_bridge/data",
    },
    "appearance": {
        "radius": 110,
        "inner_radius": 36,
        "slot_size": 58,
        "ring_color": "#1E1E22",
        "slot_color": "#2B2B31",
        "accent_color": "#FF8A3D",
        "text_color": "#F2F2F2",
        "opacity": 0.94,
        "font_size": 10,
    },
    "selection": {
        # hold: hold the hotkey, point and release. toggle: press, point and click.
        "mode": "hold",
        # In hold mode, a quick tap (shorter than this) keeps the menu open in click mode.
        "tap_ms": 220,
        # Selects when the cursor rests on a slot for X ms. 0 = off.
        "hover_dwell_ms": 0,
        # Selects when the cursor is "flicked" past the ring.
        "flick": True,
        # Distance from the center (in px) that counts as a flick, beyond radius + slot.
        "flick_margin": 30,
    },
    "menus": [],
}


class ConfigError(ValueError):
    pass


def _merge(defaults: dict, data: dict) -> dict:
    out = copy.deepcopy(defaults)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def validate(cfg: dict) -> dict:
    protocol = cfg["bridge"]["protocol"]
    if protocol not in VALID_PROTOCOLS:
        raise ConfigError(f"invalid bridge.protocol: {protocol!r} (use zscript or python)")

    mode = cfg["selection"]["mode"]
    if mode not in VALID_MODES:
        raise ConfigError(f"invalid selection.mode: {mode!r} (use hold or toggle)")

    menus = cfg.get("menus")
    if not isinstance(menus, list) or not menus:
        raise ConfigError("define at least one menu in 'menus'")

    seen_hotkeys: set[str] = set()
    for mi, menu in enumerate(menus):
        where = f"menus[{mi}]"
        if not menu.get("name"):
            raise ConfigError(f"{where}: missing 'name'")
        hotkey = menu.get("hotkey")
        if not hotkey:
            raise ConfigError(f"{where}: missing 'hotkey'")
        if hotkey in seen_hotkeys:
            raise ConfigError(f"{where}: duplicate hotkey {hotkey!r}")
        seen_hotkeys.add(hotkey)

        slots = menu.get("slots")
        if not isinstance(slots, list) or not slots:
            raise ConfigError(f"{where}: needs at least one slot")
        if len(slots) > 16:
            raise ConfigError(f"{where}: at most 16 slots")
        for si, slot in enumerate(slots):
            swhere = f"{where}.slots[{si}]"
            if not slot.get("label"):
                raise ConfigError(f"{swhere}: missing 'label'")
            action = slot.get("action") or {}
            atype = action.get("type")
            if atype not in VALID_ACTIONS:
                raise ConfigError(
                    f"{swhere}: invalid action.type {atype!r} "
                    f"(use {', '.join(sorted(VALID_ACTIONS))})"
                )
            required = {"press": "item", "brush_file": "path", "keys": "keys"}[atype]
            if not action.get(required):
                raise ConfigError(f"{swhere}: action '{atype}' requires '{required}'")
    return cfg


def load(path: str | Path | None = None) -> dict:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc}") from exc
    return validate(_merge(DEFAULTS, data))


def save(cfg: dict, path: str | Path | None = None) -> None:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    validate(cfg)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
