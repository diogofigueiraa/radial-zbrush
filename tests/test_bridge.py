"""Testa o protocolo de ponta a ponta sem ZBrush.

- ZScript (2023/2024): confere a linha gravada em command.txt.
- Python (2026): o cliente grava, a ponte (com uma API falsa) lê e executa.
"""

import json
import time
from pathlib import Path

import pytest

from radial import bridge_client as bc
from zbrush_bridge import radial_bridge as rb

ZSCRIPT_FILE = Path(__file__).resolve().parent.parent / "zbrush_bridge" / "zscript" / "RadialBridge.txt"


# --- ZScript ---------------------------------------------------------------

def _zscript_parse(line: str) -> tuple[str, str]:
    """Mesmo corte que o rbDo faz: tudo antes do primeiro | e tudo depois."""
    sep = line.find("|")
    assert sep >= 1
    return line[:sep], line[sep + 1:]


def test_zscript_press(tmp_path):
    target = bc.write_command(tmp_path, [{"type": "press", "item": "Brush:Move"}])
    assert target.name == "command.txt"
    line = target.read_text(encoding="utf-8")
    assert line == "press|Brush:Move"
    assert _zscript_parse(line) == ("press", "Brush:Move")


def test_zscript_load_uses_forward_slashes(tmp_path):
    action = {"type": "brush_file", "path": r"J:\Brushes\Clay Buildup.ZBP"}
    line = bc.write_command(tmp_path, [action]).read_text(encoding="utf-8")
    assert line == "load|J:/Brushes/Clay Buildup.ZBP"
    assert "\n" not in line and "\r" not in line


@pytest.mark.parametrize("action, message", [
    ({"type": "press", "item": "Brush:Ação"}, "ASCII"),
    ({"type": "brush_file", "path": "C:/" + "a" * 300}, "no máximo"),
    ({"type": "keys", "keys": "x"}, "não passa pela ponte"),
])
def test_zscript_rejects(tmp_path, action, message):
    with pytest.raises(bc.BridgeCommandError, match=message):
        bc.write_command(tmp_path, [action])


def test_zscript_one_action_only(tmp_path):
    a = {"type": "press", "item": "Brush:Move"}
    with pytest.raises(bc.BridgeCommandError):
        bc.write_command(tmp_path, [a, a])


def test_zscript_file_is_balanced():
    """Colchetes balanceados no RadialBridge.txt (ignorando comentários e strings)."""
    depth = 0
    for n, raw in enumerate(ZSCRIPT_FILE.read_text(encoding="utf-8").splitlines(), 1):
        in_str = False
        for i, ch in enumerate(raw):
            if ch == '"':
                in_str = not in_str
            elif in_str:
                continue
            elif raw[i:i + 2] == "//":
                break
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                assert depth >= 0, f"']' sobrando na linha {n}"
        assert not in_str, f"aspas abertas na linha {n}"
    assert depth == 0


def test_zscript_dir_matches_default_config():
    from radial import config
    text = ZSCRIPT_FILE.read_text(encoding="utf-8")
    default = bc.command_dir(config.DEFAULTS["bridge"]["command_dir"])
    assert default.as_posix().endswith("zbrush_bridge/data")
    assert '"J:/CODING/radial-zbrush/zbrush_bridge/data/"' in text


# --- Python (ZBrush 2026) ----------------------------------------------------

class FakeZBrush:
    def __init__(self, items):
        self.items = set(items)
        self.pressed = []
        self.next_filename = None

    def exists(self, item):
        return item in self.items

    def press(self, item):
        self.pressed.append(item)

    def set_next_filename(self, path):
        self.next_filename = path


@pytest.fixture
def paths(tmp_path):
    return tmp_path, tmp_path / "command.json", tmp_path / "last_result.json"


def _write_py(d, actions):
    return bc.write_command(d, actions, protocol="python")


def test_python_press_roundtrip(paths):
    d, cmd, res = paths
    _write_py(d, [{"type": "press", "item": "Brush:Move"}])
    api = FakeZBrush({"Brush:Move"})
    result = rb.run_pending(api, str(cmd), str(res))
    assert result["ok"] and api.pressed == ["Brush:Move"]
    assert not cmd.exists(), "o comando deve ser apagado depois de lido"
    assert json.loads(res.read_text(encoding="utf-8"))["ok"]


def test_python_brush_file(paths, tmp_path):
    d, cmd, res = paths
    brush = tmp_path / "Clay.ZBP"
    brush.write_bytes(b"x")
    _write_py(d, [{"type": "brush_file", "path": str(brush)}])
    api = FakeZBrush({rb.LOAD_BRUSH_ITEM})
    result = rb.run_pending(api, str(cmd), str(res))
    assert result["ok"]
    assert api.next_filename == str(brush)
    assert api.pressed == [rb.LOAD_BRUSH_ITEM]


def test_python_missing_item_is_reported(paths):
    d, cmd, res = paths
    _write_py(d, [{"type": "press", "item": "Brush:Nope"}])
    result = rb.run_pending(FakeZBrush(set()), str(cmd), str(res))
    assert not result["ok"]
    assert "não existe" in result["errors"][0]


def test_python_no_pending_command(paths):
    _, cmd, res = paths
    assert not rb.run_pending(FakeZBrush(set()), str(cmd), str(res))["ok"]


def test_python_stale_command_is_ignored(paths):
    d, cmd, _ = paths
    _write_py(d, [{"type": "press", "item": "Brush:Move"}])
    assert rb.read_command(str(cmd), now=time.time() + rb.MAX_COMMAND_AGE_S + 1) is None


# --- ActionRunner -----------------------------------------------------------

@pytest.mark.parametrize("protocol, filename", [("zscript", "command.txt"),
                                                ("python", "command.json")])
def test_runner_routes_actions(tmp_path, protocol, filename):
    sent = []
    runner = bc.ActionRunner(
        {"command_dir": str(tmp_path), "trigger_hotkey": "<ctrl>+<alt>+<shift>+j",
         "protocol": protocol},
        send_keys=sent.append,
        wait_modifiers_released=lambda t: None,
        confirm_timeout=0.05,
    )
    runner._run({"type": "keys", "keys": "x"})
    runner._run({"type": "press", "item": "Brush:Move"})
    assert sent == ["x", "<ctrl>+<alt>+<shift>+j"]
    assert (tmp_path / filename).exists()


def test_runner_does_not_trigger_on_bad_command(tmp_path):
    sent = []
    runner = bc.ActionRunner(
        {"command_dir": str(tmp_path), "trigger_hotkey": "<ctrl>+<alt>+<shift>+j"},
        send_keys=sent.append, wait_modifiers_released=lambda t: None,
    )
    runner._run({"type": "press", "item": "Brush:Ação"})
    assert sent == []


def test_runner_focuses_and_reports(tmp_path, capsys):
    calls = []
    runner = bc.ActionRunner(
        {"command_dir": str(tmp_path), "trigger_hotkey": "<ctrl>+<alt>+<shift>+j"},
        send_keys=lambda k: calls.append(("keys", k)),
        wait_modifiers_released=lambda t: None,
        ensure_focus=lambda: calls.append(("focus",)) or True,
        confirm_timeout=0.05,
    )
    runner._run({"type": "press", "item": "Brush:Move"})
    assert calls == [("focus",), ("keys", "<ctrl>+<alt>+<shift>+j")]
    # Ninguém apagou o command.txt: o app avisa que o atalho não chegou.
    assert "não leu o comando" in capsys.readouterr().out


def test_runner_reports_success_when_bridge_consumes(tmp_path, capsys):
    target = tmp_path / "command.txt"
    runner = bc.ActionRunner(
        {"command_dir": str(tmp_path), "trigger_hotkey": "<ctrl>+<alt>+<shift>+j"},
        send_keys=lambda k: target.unlink(missing_ok=True),  # "ponte" consome
        wait_modifiers_released=lambda t: None,
        confirm_timeout=0.5,
    )
    runner._run({"type": "press", "item": "Brush:Move"})
    assert "ponte executou" in capsys.readouterr().out


def test_zbrush_title_detection():
    from radial.winfocus import is_zbrush_title
    assert is_zbrush_title("ZBrush 2024")
    assert is_zbrush_title("ZBrush 2024.0.1 - Untitled")
    assert not is_zbrush_title(r"C:\WINDOWS\system32\cmd.exe")
    assert not is_zbrush_title("radial-zbrush - File Explorer")
    assert not is_zbrush_title("Google Chrome")
