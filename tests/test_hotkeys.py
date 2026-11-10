"""Tests the key-combination logic of HotkeyService.

If pynput/PySide6 are not installed, minimal stand-ins are used just to
import the module — what is being tested is the logic, not the keyboard.
"""

import enum
import importlib
import sys
import types


def _install_stubs():
    try:
        import pynput  # noqa: F401
        import PySide6  # noqa: F401
        return
    except ImportError:
        pass

    class Key(enum.Enum):
        ctrl = 1; ctrl_l = 2; ctrl_r = 3; alt = 4; alt_l = 5; alt_r = 6  # noqa: E702
        alt_gr = 7; shift = 8; shift_l = 9; shift_r = 10; cmd = 11  # noqa: E702
        cmd_l = 12; cmd_r = 13; esc = 14; f12 = 15  # noqa: E702

    class KeyCode:
        def __init__(self, vk=None, char=None):
            self.vk, self.char = vk, char

        @classmethod
        def from_char(cls, c):
            return cls(char=c)

    class HotKey:
        @staticmethod
        def parse(s):
            out = []
            for part in s.split("+"):
                if part.startswith("<"):
                    out.append(Key[part[1:-1]])
                else:
                    out.append(KeyCode.from_char(part))
            return out

    kb = types.ModuleType("pynput.keyboard")
    kb.Key, kb.KeyCode, kb.HotKey = Key, KeyCode, HotKey
    kb.Listener = kb.Controller = object
    pynput = types.ModuleType("pynput")
    pynput.keyboard = kb
    sys.modules["pynput"], sys.modules["pynput.keyboard"] = pynput, kb

    class Signal:
        def __init__(self, *a):
            pass

    qtcore = types.ModuleType("PySide6.QtCore")
    qtcore.QObject, qtcore.Signal = object, Signal
    pyside = types.ModuleType("PySide6")
    pyside.QtCore = qtcore
    sys.modules["PySide6"], sys.modules["PySide6.QtCore"] = pyside, qtcore


_install_stubs()
hk = importlib.import_module("radial.hotkeys")
from pynput.keyboard import Key, KeyCode  # noqa: E402


def make(*hotkeys):
    return hk.HotkeyService(list(hotkeys))


def test_alt_q_opens_and_releases():
    svc = make("<alt>+q", "<alt>+w")
    assert svc.handle_press(hk.ident(Key.alt_l)) is None
    assert svc.handle_press(hk.ident(KeyCode(vk=0x51, char="q"))) == 0
    assert svc.modifiers_down()
    # auto-repeat does not reopen
    assert svc.handle_press(hk.ident(KeyCode(vk=0x51, char="q"))) is None
    assert svc.handle_release(hk.ident(KeyCode(vk=0x51, char="q"))) == 0
    assert svc.handle_release(hk.ident(Key.alt_l)) is None
    assert not svc.modifiers_down()


def test_ctrl_combo_with_control_char():
    # On Windows, Ctrl+Q arrives as char '\x11' — it must match by virtual-key code.
    svc = make("<ctrl>+q")
    svc.handle_press(hk.ident(Key.ctrl_l))
    assert svc.handle_press(hk.ident(KeyCode(vk=0x51, char="\x11"))) == 0


def test_second_menu():
    svc = make("<alt>+q", "<alt>+w")
    svc.handle_press(hk.ident(Key.alt_r))
    assert svc.handle_press(hk.ident(KeyCode(vk=0x57, char="w"))) == 1


def test_letter_alone_does_not_open_alt_menu():
    svc = make("<alt>+q")
    assert svc.handle_press(hk.ident(KeyCode(vk=0x51, char="q"))) is None


def test_modifier_pressed_last_still_opens():
    svc = make("<alt>+q")
    svc.handle_press(hk.ident(KeyCode(vk=0x51, char="q")))
    assert svc.handle_press(hk.ident(Key.alt_l)) == 0
