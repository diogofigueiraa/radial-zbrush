"""Pure (Qt-free) helpers used by the menu editor, so they can be unit tested."""

from __future__ import annotations

import copy

from . import config as config_mod

MAX_SLOTS = 16

# action type -> the field that holds its value
ACTION_FIELDS = {"press": "item", "brush_file": "path", "keys": "keys"}

_MODIFIERS = {"ctrl": "<ctrl>", "alt": "<alt>", "shift": "<shift>", "meta": "<cmd>"}
_MODIFIER_ORDER = ["<ctrl>", "<alt>", "<shift>", "<cmd>"]
_SPECIAL_KEYS = {
    "space": "<space>", "tab": "<tab>", "return": "<enter>", "enter": "<enter>",
    "backspace": "<backspace>", "del": "<delete>", "ins": "<insert>",
    "home": "<home>", "end": "<end>", "pgup": "<page_up>", "pgdown": "<page_down>",
    "up": "<up>", "down": "<down>", "left": "<left>", "right": "<right>",
}


def qt_sequence_to_pynput(text: str) -> str:
    """'Alt+Q' -> '<alt>+q', 'Ctrl+Shift+F5' -> '<ctrl>+<shift>+<f5>'.

    Takes the portable text of a QKeySequence (first chord only). Returns ''
    if it has no non-modifier key or uses an unsupported key.
    """
    text = text.split(",")[0].strip()
    if not text:
        return ""
    parts = [p.strip() for p in text.split("+") if p.strip()]
    # A literal '+' key shows up as an empty token at the end ("Ctrl++").
    if text.endswith("++"):
        parts.append("+")
    mods: list[str] = []
    key = ""
    for part in parts:
        low = part.lower()
        if low in _MODIFIERS:
            mods.append(_MODIFIERS[low])
        elif key:
            return ""  # more than one non-modifier key
        elif len(part) == 1:
            key = part.lower()
        elif low in _SPECIAL_KEYS:
            key = _SPECIAL_KEYS[low]
        elif low.startswith("f") and low[1:].isdigit():
            key = f"<{low}>"
        else:
            return ""
    if not key or key == "+":
        return ""
    mods.sort(key=_MODIFIER_ORDER.index)
    return "+".join(mods + [key])


def pynput_to_display(combo: str) -> str:
    """'<ctrl>+<alt>+q' -> 'Ctrl+Alt+Q' (for labels in the UI)."""
    out = []
    for token in combo.split("+"):
        name = token.strip("<>")
        out.append(name.upper() if len(name) == 1 else name.capitalize())
    return "+".join(out)


def new_slot(action_type: str = "press") -> dict:
    return {"label": "New slot", "action": {"type": action_type, ACTION_FIELDS[action_type]: ""}}


def unique_hotkey(menus: list[dict]) -> str:
    """A hotkey not used by any existing menu (for newly added menus)."""
    used = {m.get("hotkey") for m in menus}
    for key in "ertyuiopasdfghjklzxcvbnm":
        combo = f"<alt>+{key}"
        if combo not in used:
            return combo
    return ""


def new_menu(menus: list[dict]) -> dict:
    names = {m.get("name") for m in menus}
    n = len(menus) + 1
    while f"Menu {n}" in names:
        n += 1
    return {"name": f"Menu {n}", "hotkey": unique_hotkey(menus), "slots": [new_slot()]}


def move_item(items: list, index: int, delta: int) -> int:
    """Moves items[index] by delta (clamped). Returns its new index."""
    target = max(0, min(len(items) - 1, index + delta))
    if target != index:
        items.insert(target, items.pop(index))
    return target


def set_action_type(slot: dict, action_type: str) -> None:
    """Changes the action type, keeping a value if the field name is shared."""
    old = slot.get("action", {})
    slot["action"] = {"type": action_type, ACTION_FIELDS[action_type]: ""}
    if old.get("type") == action_type:
        slot["action"] = old


def clean_slot(slot: dict) -> dict:
    """Drops empty optional fields (icon/color) so the JSON stays tidy."""
    for key in ("icon", "color"):
        if not slot.get(key):
            slot.pop(key, None)
    return slot


def validate_menus(menus: list[dict], base_cfg: dict) -> str | None:
    """Returns an error message, or None if the menus pass config validation."""
    cfg = copy.deepcopy(base_cfg)
    cfg["menus"] = copy.deepcopy(menus)
    for menu in cfg["menus"]:
        for slot in menu.get("slots", []):
            clean_slot(slot)
    try:
        config_mod.validate(cfg)
    except config_mod.ConfigError as exc:
        return str(exc)
    return None
