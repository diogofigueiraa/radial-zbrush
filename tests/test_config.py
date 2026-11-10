import json

import pytest

from radial import config as c


def _write(tmp_path, data):
    p = tmp_path / "menus.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


MINIMAL = {
    "menus": [
        {"name": "A", "hotkey": "<alt>+q",
         "slots": [{"label": "Move", "action": {"type": "press", "item": "Brush:Move"}}]}
    ]
}


def test_shipped_config_is_valid():
    cfg = c.load()
    assert cfg["menus"]


def test_defaults_are_merged(tmp_path):
    cfg = c.load(_write(tmp_path, MINIMAL))
    assert cfg["appearance"]["radius"] == c.DEFAULTS["appearance"]["radius"]
    assert cfg["selection"]["mode"] == "hold"


def test_partial_override_keeps_other_defaults(tmp_path):
    data = dict(MINIMAL, appearance={"radius": 150})
    cfg = c.load(_write(tmp_path, data))
    assert cfg["appearance"]["radius"] == 150
    assert cfg["appearance"]["slot_size"] == c.DEFAULTS["appearance"]["slot_size"]


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d.update(menus=[]), "at least one menu"),
    (lambda d: d["menus"][0].pop("hotkey"), "hotkey"),
    (lambda d: d["menus"][0]["slots"][0]["action"].update(type="nope"), "action.type"),
    (lambda d: d["menus"][0]["slots"][0]["action"].pop("item"), "requires 'item'"),
    (lambda d: d.update(selection={"mode": "x"}), "selection.mode"),
])
def test_invalid_configs(tmp_path, mutate, message):
    data = json.loads(json.dumps(MINIMAL))
    mutate(data)
    with pytest.raises(c.ConfigError, match=message):
        c.load(_write(tmp_path, data))


def test_duplicate_hotkeys(tmp_path):
    data = json.loads(json.dumps(MINIMAL))
    data["menus"].append(json.loads(json.dumps(data["menus"][0])))
    with pytest.raises(c.ConfigError, match="duplicate"):
        c.load(_write(tmp_path, data))


def test_bad_json(tmp_path):
    p = tmp_path / "menus.json"
    p.write_text("{", encoding="utf-8")
    with pytest.raises(c.ConfigError, match="invalid JSON"):
        c.load(p)
