import pytest

from radial import sendinput as si


def test_trigger_hotkey():
    assert si.parse_combo_vks("<ctrl>+<alt>+<shift>+j") == [0x11, 0x12, 0x10, 0x4A]


@pytest.mark.parametrize("combo, vks", [
    ("x", [0x58]),
    ("<shift>+f", [0x10, 0x46]),
    ("<ctrl>+d", [0x11, 0x44]),
    ("<f12>", [0x7B]),
    ("<f1>", [0x70]),
    ("5", [0x35]),
    ("<ctrl>+[", [0x11, 0xDB]),
    ("X", [0x58]),
])
def test_combos(combo, vks):
    assert si.parse_combo_vks(combo) == vks


@pytest.mark.parametrize("combo", ["<nope>", "ç", "<ctrl>++", ""])
def test_unsupported(combo):
    with pytest.raises(si.UnsupportedKey):
        si.parse_combo_vks(combo)
