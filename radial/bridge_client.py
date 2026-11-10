"""Lado de fora da ponte: grava o comando em disco e "acorda" o ZBrush.

Duas pontes possíveis (bridge.protocol no config):

- "zscript" (ZBrush 2023/2024): zbrush_bridge/zscript/RadialBridge.txt
    <command_dir>/command.txt com UMA linha:  press|Brush:Move  ou  load|C:/x/Clay.ZBP

- "python" (ZBrush 2026): zbrush_bridge/radial_bridge.py
    <command_dir>/command.json  {"id": ..., "created": ..., "actions": [...]}

Depois de gravar, o app aperta o `trigger_hotkey`, atribuído no ZBrush ao botão
ZPlugin > Radial Bridge > Run. O botão lê o arquivo, executa e apaga.

Por que assim: nem o ZScript nem a API Python do ZBrush têm um jeito de
"escutar" em segundo plano. Código no ZBrush roda a partir de um botão.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

from .config import PROJECT_ROOT

JSON_COMMAND_FILE = "command.json"
TEXT_COMMAND_FILE = "command.txt"
RESULT_FILE = "last_result.json"

BRIDGE_ACTIONS = {"press", "brush_file"}
ZSCRIPT_KINDS = {"press": ("press", "item"), "brush_file": ("load", "path")}
ZSCRIPT_MAX_LINE = 250  # MemReadString lê no máximo 255 caracteres


class BridgeCommandError(ValueError):
    pass


def command_dir(raw: str) -> Path:
    """Expande ~ e variáveis; caminho relativo é relativo à raiz do projeto."""
    path = Path(os.path.expandvars(os.path.expanduser(raw)))
    return path if path.is_absolute() else PROJECT_ROOT / path


def _atomic_write(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, target)


def zscript_line(action: dict) -> str:
    """Converte uma ação na linha que o RadialBridge.txt entende."""
    atype = action.get("type")
    if atype not in ZSCRIPT_KINDS:
        raise BridgeCommandError(f"ação {atype!r} não passa pela ponte")
    kind, field = ZSCRIPT_KINDS[atype]
    arg = str(action[field])
    if atype == "brush_file":
        arg = arg.replace("\\", "/")
    line = f"{kind}|{arg}"
    if "\n" in line or "\r" in line:
        raise BridgeCommandError("o comando não pode ter quebra de linha")
    if len(line) > ZSCRIPT_MAX_LINE:
        raise BridgeCommandError(
            f"comando com {len(line)} caracteres; o ZScript lê no máximo {ZSCRIPT_MAX_LINE}"
        )
    if not line.isascii():
        raise BridgeCommandError(
            "use só caracteres ASCII (sem acentos) no caminho ou item path: "
            "o ZScript pode não ler o texto corretamente"
        )
    return line


def write_command(directory: Path, actions: list[dict], protocol: str = "zscript") -> Path:
    """Grava o comando de forma atômica e devolve o caminho do arquivo."""
    if protocol == "zscript":
        if len(actions) != 1:
            raise BridgeCommandError("a ponte ZScript executa uma ação por vez")
        target = directory / TEXT_COMMAND_FILE
        _atomic_write(target, zscript_line(actions[0]))
        return target
    if protocol == "python":
        payload = {"id": uuid.uuid4().hex, "created": time.time(), "actions": actions}
        target = directory / JSON_COMMAND_FILE
        _atomic_write(target, json.dumps(payload, ensure_ascii=False))
        return target
    raise BridgeCommandError(f"protocolo desconhecido: {protocol!r}")


def read_result(directory: Path) -> dict | None:
    try:
        return json.loads((directory / RESULT_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class ActionRunner:
    """Executa a ação de um slot.

    - press / brush_file: passam pela ponte no ZBrush.
    - keys: o app só aperta as teclas (atalhos nativos do ZBrush).
    """

    def __init__(
        self,
        cfg_bridge: dict,
        send_keys: Callable[[str], None],
        wait_modifiers_released: Callable[[float], None],
        ensure_focus: Callable[[], bool] | None = None,
        confirm_timeout: float = 1.5,
    ):
        self.directory = command_dir(cfg_bridge["command_dir"])
        self.trigger = cfg_bridge["trigger_hotkey"]
        self.protocol = cfg_bridge.get("protocol", "zscript")
        self._send_keys = send_keys
        self._wait_mods = wait_modifiers_released
        self._focus = ensure_focus
        self.confirm_timeout = confirm_timeout

    def run(self, action: dict) -> None:
        # Em thread separada para não travar a interface do menu.
        threading.Thread(target=self._run, args=(action,), daemon=True).start()

    def _run(self, action: dict) -> None:
        # Se o usuário ainda segura Alt/Ctrl/Shift do atalho do menu, o ZBrush
        # receberia outra combinação. Espera soltar (até 0,6 s).
        self._wait_mods(0.6)
        atype = action.get("type")
        try:
            if atype == "keys":
                self._ensure_focus()
                self._send_keys(action["keys"])
                print(f"[radial] teclas enviadas: {action['keys']}")
            elif atype in BRIDGE_ACTIONS:
                path = write_command(self.directory, [action], self.protocol)
                self._ensure_focus()
                self._send_keys(self.trigger)
                self._report_bridge(path)
            else:
                print(f"[radial] ação desconhecida: {action!r}")
        except BridgeCommandError as exc:
            print(f"[radial] comando recusado: {exc}")

    def _ensure_focus(self) -> None:
        if self._focus is not None:
            self._focus()

    def _report_bridge(self, path: Path) -> None:
        """A ponte apaga o arquivo ao ler. Se continuar lá, o atalho não chegou."""
        deadline = time.monotonic() + self.confirm_timeout
        while time.monotonic() < deadline:
            if not path.exists():
                print("[radial] ponte executou o comando")
                return
            time.sleep(0.05)
        print("[radial] AVISO: o ZBrush não leu o comando. O atalho "
              f"{self.trigger} não chegou ao botão Run. Confira se o ZBrush "
              "está em foco e se o atalho do Run está atribuído.")
