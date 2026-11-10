"""Global hotkeys (pynput) and key sending.

The listener runs on a pynput thread. Qt signals emitted from here reach the
main thread through a queued connection (AutoConnection), so the UI is only
touched on the Qt thread.

Key comparison: on Windows, with Ctrl held, pynput delivers a control
character (Ctrl+Q becomes '\\x11'). So each key becomes a set of identities
(virtual-key code and character), and two keys "match" when the sets overlap.
"""

from __future__ import annotations

import sys
import threading
import time

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

from . import sendinput

LLKHF_INJECTED = 0x10  # Windows flag for software-generated keys

_MODIFIER_NAMES = {"ctrl", "alt", "shift", "cmd"}
_SIDE_ALIASES = {
    "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "shift_l": "shift", "shift_r": "shift",
    "cmd_l": "cmd", "cmd_r": "cmd",
}


def ident(key) -> frozenset:
    """Identities of a key, for tolerant comparison."""
    if isinstance(key, keyboard.Key):
        name = _SIDE_ALIASES.get(key.name, key.name)
        return frozenset({("key", name)})
    ids = set()
    vk = getattr(key, "vk", None)
    char = getattr(key, "char", None)
    if vk is not None:
        ids.add(("vk", vk))
    if char:
        c = char.lower()
        ids.add(("char", c))
        if c.isascii() and c.isalnum():
            # On Windows the virtual-key code of letters and digits is the uppercase ASCII.
            ids.add(("vk", ord(c.upper())))
    return frozenset(ids)


def parse_combo(combo: str) -> list:
    """'<ctrl>+<shift>+<f12>' -> [Key.ctrl, Key.shift, Key.f12]"""
    return keyboard.HotKey.parse(combo)


def _is_modifier(i: frozenset) -> bool:
    return any(kind == "key" and name in _MODIFIER_NAMES for kind, name in i)


class HotkeyService(QObject):
    menu_pressed = Signal(int)   # menu index
    menu_released = Signal(int)
    escape_pressed = Signal()

    def __init__(self, hotkeys: list[str]):
        super().__init__()
        self._combos = [[ident(k) for k in parse_combo(h)] for h in hotkeys]
        self._pressed: set[frozenset] = set()
        self._active: int | None = None
        self._lock = threading.Lock()
        self._listener: keyboard.Listener | None = None

    # --- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        kwargs = {"on_press": self._on_press, "on_release": self._on_release}
        if sys.platform == "win32":
            # Ignore keys the app injects itself (e.g. the bridge trigger).
            kwargs["win32_event_filter"] = (
                lambda msg, data: not (data.flags & LLKHF_INJECTED)
            )
        self._listener = keyboard.Listener(**kwargs)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    # --- state -------------------------------------------------------------
    def modifiers_down(self) -> bool:
        with self._lock:
            return any(_is_modifier(i) for i in self._pressed)

    def wait_modifiers_released(self, timeout: float) -> None:
        end = time.monotonic() + timeout
        while self.modifiers_down() and time.monotonic() < end:
            time.sleep(0.01)

    # --- combo logic (testable without a keyboard) -------------------------
    @staticmethod
    def _matches(item: frozenset, pressed: set[frozenset]) -> bool:
        return any(item & p for p in pressed)

    def _combo_hit(self, combo: list[frozenset], key_id: frozenset,
                   pressed: set[frozenset]) -> bool:
        return (
            bool(combo)
            and all(self._matches(item, pressed) for item in combo)
            and any(item & key_id for item in combo)
        )

    def handle_press(self, key_id: frozenset) -> int | None:
        """Registers the key; returns the index of the menu it opens, if any."""
        with self._lock:
            self._pressed.add(key_id)
            pressed = set(self._pressed)
            if self._active is not None:
                return None  # a menu is already open from a hotkey; ignore auto-repeat
            for idx, combo in enumerate(self._combos):
                if self._combo_hit(combo, key_id, pressed):
                    self._active = idx
                    return idx
        return None

    def handle_release(self, key_id: frozenset) -> int | None:
        """Releases the key; returns the index of the menu it releases, if any."""
        with self._lock:
            self._pressed = {p for p in self._pressed if not (p & key_id)}
            active = self._active
            if active is not None and any(item & key_id for item in self._combos[active]):
                self._active = None
                return active
        return None

    # --- pynput callbacks (listener thread) --------------------------------
    def _on_press(self, key) -> None:
        key_id = ident(key)
        if ("key", "esc") in key_id:
            self.escape_pressed.emit()
        idx = self.handle_press(key_id)
        if idx is not None:
            self.menu_pressed.emit(idx)

    def _on_release(self, key) -> None:
        idx = self.handle_release(ident(key))
        if idx is not None:
            self.menu_released.emit(idx)


_controller: keyboard.Controller | None = None


def send_keys(spec: str) -> None:
    """Presses one or more space-separated combos.

    '<ctrl>+<shift>+<f12>'  -> one combo
    'b s t'                 -> B, then S, then T (a ZBrush brush shortcut)
    """
    global _controller
    # ZBrush may miss keys held for only a few milliseconds, so each combo
    # stays pressed for KEY_HOLD_S.
    for combo in spec.split():
        # On Windows: physical key via SendInput (ZBrush ignores the Unicode
        # character pynput sends for letters).
        if sendinput.available():
            try:
                sendinput.send_combo(combo, KEY_STEP_S, KEY_HOLD_S)
                time.sleep(KEY_GAP_S)
                continue
            except sendinput.UnsupportedKey as exc:
                print(f"[radial] {exc} — falling back to pynput")
        if _controller is None:
            _controller = keyboard.Controller()
        keys = parse_combo(combo)
        for key in keys:
            _controller.press(key)
            time.sleep(KEY_STEP_S)
        time.sleep(KEY_HOLD_S)
        for key in reversed(keys):
            _controller.release(key)
            time.sleep(KEY_STEP_S)
        time.sleep(KEY_GAP_S)


KEY_STEP_S = 0.02   # between keys of the same combo
KEY_HOLD_S = 0.06   # time the whole combo stays pressed
KEY_GAP_S = 0.06    # between combos
