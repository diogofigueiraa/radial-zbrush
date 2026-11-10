"""Envio de teclas "físicas" no Windows via SendInput.

Por que existe: o pynput envia letras como caractere Unicode (VK_PACKET), não
como a tecla J de verdade. Atalhos de aplicativos como o ZBrush olham a tecla
física e ignoram isso. Aqui cada tecla vai com o código virtual (VK) e o scan
code, como um teclado de verdade.

Formato aceito: o mesmo do pynput, ex. "<ctrl>+<alt>+<shift>+j", "x", "<f5>".
"""

from __future__ import annotations

import sys
import time

VK_NAMES = {
    "ctrl": 0x11, "alt": 0x12, "shift": 0x10, "cmd": 0x5B,
    "ctrl_l": 0xA2, "ctrl_r": 0xA3, "alt_l": 0xA4, "alt_r": 0xA5,
    "shift_l": 0xA0, "shift_r": 0xA1,
    "esc": 0x1B, "enter": 0x0D, "tab": 0x09, "space": 0x20, "backspace": 0x08,
    "delete": 0x2E, "insert": 0x2D, "home": 0x24, "end": 0x23,
    "page_up": 0x21, "page_down": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    **{f"f{i}": 0x6F + i for i in range(1, 25)},  # F1 = 0x70
}
# Teclas que no Windows precisam da flag "extended".
EXTENDED = {0xA3, 0xA5, 0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22, 0x25, 0x26, 0x27, 0x28, 0x5B}

# Símbolos comuns no teclado US -> VK (VK_OEM_*).
VK_SYMBOLS = {
    ";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD, ".": 0xBE, "/": 0xBF,
    "`": 0xC0, "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}


class UnsupportedKey(ValueError):
    pass


def token_to_vk(token: str) -> int:
    """'<ctrl>' -> 0x11, 'j' -> 0x4A, '5' -> 0x35."""
    if token.startswith("<") and token.endswith(">"):
        name = token[1:-1].lower()
        if name in VK_NAMES:
            return VK_NAMES[name]
        raise UnsupportedKey(f"tecla especial não suportada: {token}")
    if len(token) == 1:
        c = token.lower()
        if c.isascii() and c.isalnum():
            return ord(c.upper())
        if c in VK_SYMBOLS:
            return VK_SYMBOLS[c]
    raise UnsupportedKey(f"tecla não suportada: {token!r}")


def parse_combo_vks(combo: str) -> list[int]:
    """'<ctrl>+<alt>+<shift>+j' -> [0x11, 0x12, 0x10, 0x4A]

    O '+' sozinho como tecla (ex.: '<ctrl>++') não é suportado.
    """
    parts = combo.split("+")
    if any(p == "" for p in parts):
        raise UnsupportedKey(f"combinação inválida: {combo!r}")
    return [token_to_vk(p) for p in parts]


def _send(vk: int, up: bool) -> None:
    import ctypes
    from ctypes import wintypes

    ULONG_PTR = ctypes.c_size_t

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    INPUT_KEYBOARD = 1
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    scan = user32.MapVirtualKeyW(vk, 0)  # MAPVK_VK_TO_VSC
    flags = KEYEVENTF_KEYUP if up else 0
    if vk in EXTENDED:
        flags |= KEYEVENTF_EXTENDEDKEY
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.u.ki = KEYBDINPUT(wVk=vk, wScan=scan, dwFlags=flags, time=0, dwExtraInfo=0)
    if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
        raise OSError(f"SendInput falhou (erro {ctypes.get_last_error()})")


def available() -> bool:
    return sys.platform == "win32"


def send_combo(combo: str, step: float, hold: float) -> None:
    vks = parse_combo_vks(combo)
    for vk in vks:
        _send(vk, up=False)
        time.sleep(step)
    time.sleep(hold)
    for vk in reversed(vks):
        _send(vk, up=True)
        time.sleep(step)
