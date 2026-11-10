import pytest

from radial import config as c
from radial import editing as e


@pytest.mark.parametrize("seq, expected", [
    ("Alt+Q", "<alt>+q"),
    ("Ctrl+Shift+E", "<ctrl>+<shift>+e"),
    ("Shift+Ctrl+Alt+J", "<ctrl>+<alt>+<shift>+j"),
    ("Ctrl+F5", "<ctrl>+<f5>"),
    ("Alt+Space", "<alt>+<space>"),
    ("Alt+Q, Ctrl+W", "<alt>+q"),
    ("Ctrl+Alt", ""),
    ("", ""),
    ("Ctrl+Bogus", ""),
])
def test_qt_sequence_to_pynput(seq, expected):
    assert e.qt_sequence_to_pynput(seq) == expected


def test_pynput_to_display():
    assert e.pynput_to_display("<ctrl>+<alt>+q") == "Ctrl+Alt+Q"
    assert e.pynput_to_display("<alt>+<f5>") == "Alt+F5"


def test_move_item_clamps():
    items = [1, 2, 3]
    assert e.move_item(items, 0, -1) == 0
    assert e.move_item(items, 0, 1) == 1 and items == [2, 1, 3]
    assert e.move_item(items, 2, 5) == 2


def test_new_menu_is_valid_once_slot_filled():
    existing = {"name": "Menu 2", "hotkey": "<alt>+e",
                "slots": [{"label": "A", "action": {"type": "keys", "keys": "x"}}]}
    menus = [existing]
    menu = e.new_menu(menus)
    assert menu["name"] != "Menu 2"
    assert menu["hotkey"] != "<alt>+e"
    menu["slots"][0]["action"]["item"] = "Brush:Move"
    assert e.validate_menus(menus + [menu], c.DEFAULTS) is None


def test_validate_menus_reports_errors():
    menu = e.new_menu([])  # empty action value
    assert "requires 'item'" in e.validate_menus([menu], c.DEFAULTS)


def test_clean_slot_drops_empty_optionals():
    slot = {"label": "A", "color": "", "icon": "", "action": {}}
    assert e.clean_slot(slot) == {"label": "A", "action": {}}


def test_set_action_type_resets_value():
    slot = e.new_slot("press")
    slot["action"]["item"] = "Brush:Move"
    e.set_action_type(slot, "keys")
    assert slot["action"] == {"type": "keys", "keys": ""}
