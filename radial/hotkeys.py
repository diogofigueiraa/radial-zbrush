"""Atalhos globais (pynput) e envio de teclas.

O listener roda numa thread do pynput. Os sinais Qt emitidos daqui chegam na
thread principal pela conexão em fila (AutoConnection), então a interface só é
tocada na thread do Qt.

Comparação de teclas: no Windows, com Ctrl apertado o pynput entrega um
caractere de controle (Ctrl+Q vira '\\x11'). Por isso cada tecla vira um
conjunto de identidades (código virtual e caractere) e duas teclas "batem"
quando os conjuntos se cruzam.
"""

from __future__ import annotations

import sys
import threading
import time

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

from . import sendinput

LLKHF_INJECTED = 0x10  # flag do Windows para teclas geradas por software

_MODIFIER_NAMES = {"ctrl", "alt", "shift", "cmd"}
_SIDE_ALIASES = {
    "ctrl_l": "ctrl", "ctrl_r": "ctrl",
    "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
    "shift_l": "shift", "shift_r": "shift",
    "cmd_l": "cmd", "cmd_r": "cmd",
}


def ident(key) -> frozenset:
    """Identidades de uma tecla, para comparação tolerante."""
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
            # No Windows o código virtual de letras e números é o ASCII maiúsculo.
            ids.add(("vk", ord(c.upper())))
    return frozenset(ids)


def parse_combo(combo: str) -> list:
    """'<ctrl>+<shift>+<f12>' -> [Key.ctrl, Key.shift, Key.f12]"""
    return keyboard.HotKey.parse(combo)


def _is_modifier(i: frozenset) -> bool:
    return any(kind == "key" and name in _MODIFIER_NAMES for kind, name in i)


class HotkeyService(QObject):
    menu_pressed = Signal(int)   # índice do menu
    menu_released = Signal(int)
    escape_pressed = Signal()

    def __init__(self, hotkeys: list[str]):
        super().__init__()
        self._combos = [[ident(k) for k in parse_combo(h)] for h in hotkeys]
        self._pressed: set[frozenset] = set()
        self._active: int | None = None
        self._lock = threading.Lock()
        self._listener: keyboard.Listener | None = None

    # --- ciclo de vida -------------------------------------------------
    def start(self) -> None:
        kwargs = {"on_press": self._on_press, "on_release": self._on_release}
        if sys.platform == "win32":
            # Ignora teclas que o próprio app injeta (ex.: o gatilho da ponte).
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

    # --- estado --------------------------------------------------------
    def modifiers_down(self) -> bool:
        with self._lock:
            return any(_is_modifier(i) for i in self._pressed)

    def wait_modifiers_released(self, timeout: float) -> None:
        end = time.monotonic() + timeout
        while self.modifiers_down() and time.monotonic() < end:
            time.sleep(0.01)

    # --- lógica de combinação (testável sem teclado) --------------------
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
        """Registra a tecla; devolve o índice do menu ativado, se houver."""
        with self._lock:
            self._pressed.add(key_id)
            pressed = set(self._pressed)
            if self._active is not None:
                return None  # menu já aberto por atalho; ignora auto-repeat
            for idx, combo in enumerate(self._combos):
                if self._combo_hit(combo, key_id, pressed):
                    self._active = idx
                    return idx
        return None

    def handle_release(self, key_id: frozenset) -> int | None:
        """Solta a tecla; devolve o índice do menu liberado, se houver."""
        with self._lock:
            self._pressed = {p for p in self._pressed if not (p & key_id)}
            active = self._active
            if active is not None and any(item & key_id for item in self._combos[active]):
                self._active = None
                return active
        return None

    # --- callbacks do pynput (thread do listener) ----------------------
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
    """Aperta uma ou mais combinações separadas por espaço.

    '<ctrl>+<shift>+<f12>'  -> uma combinação
    'b s t'                 -> B, depois S, depois T (atalho de brush do ZBrush)
    """
    global _controller
    # O ZBrush pode não registrar teclas apertadas por poucos milissegundos,
    # então cada combinação fica pressionada por KEY_HOLD_S.
    for combo in spec.split():
        # No Windows: tecla física via SendInput (o ZBrush ignora o caractere
        # Unicode que o pynput manda para letras).
        if sendinput.available():
            try:
                sendinput.send_combo(combo, KEY_STEP_S, KEY_HOLD_S)
                time.sleep(KEY_GAP_S)
                continue
            except sendinput.UnsupportedKey as exc:
                print(f"[radial] {exc} — usando o envio do pynput")
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


KEY_STEP_S = 0.02   # entre uma tecla e outra da mesma combinação
KEY_HOLD_S = 0.06   # tempo com a combinação inteira pressionada
KEY_GAP_S = 0.06    # entre combinações
