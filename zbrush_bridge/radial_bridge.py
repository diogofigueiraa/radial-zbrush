"""Ponte do menu radial — roda DENTRO do ZBrush 2026 (Python).

SÓ PARA ZBRUSH 2026. Para ZBrush 2023/2024 use zscript/RadialBridge.txt.
No config, use "protocol": "python" com esta ponte.

Como usar:
    ZBrush > ZScript > Python Scripting > Load > escolha este arquivo.

O script cria o subpalette ZPlugin > Radial Bridge com o botão "Run".
Atribua a ele o mesmo atalho do config (trigger_hotkey):
    Ctrl+Alt+clique no botão "Run" e aperte o atalho.

Quando o app externo grava zbrush_bridge/data/command.json e aperta o atalho,
o botão lê o comando, executa e apaga o arquivo. O resultado vai para
zbrush_bridge/data/last_result.json e para o console Python do ZBrush.

Este arquivo não depende de nada fora da biblioteca padrão + zbrush.
"""

from __future__ import annotations

import json
import os
import time
import traceback

try:
    from zbrush import commands as zbc  # só existe dentro do ZBrush
except ImportError:  # permite importar nos testes
    zbc = None

# Mesma pasta do "command_dir" padrão do config: <projeto>/zbrush_bridge/data
COMMAND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
COMMAND_FILE = os.path.join(COMMAND_DIR, "command.json")
RESULT_FILE = os.path.join(COMMAND_DIR, "last_result.json")

SUBPALETTE = "ZPlugin:Radial Bridge"
RUN_BUTTON = f"{SUBPALETTE}:Run"
TEST_BUTTON = f"{SUBPALETTE}:Test"

# Item path do botão de carregar brush. VERIFICAR na Fase 0
# (phase0/02_load_brush_file.py) — se o nome for outro, ajuste aqui.
LOAD_BRUSH_ITEM = "Brush:Load Brush"

# Comandos com mais de 10 s são considerados velhos e ignorados.
MAX_COMMAND_AGE_S = 10.0


class BridgeError(Exception):
    pass


def execute_action(action: dict, api=None) -> str:
    """Executa uma ação e devolve uma descrição curta do que fez."""
    api = api or zbc
    if api is None:
        raise BridgeError("API do ZBrush indisponível (rode dentro do ZBrush)")

    atype = action.get("type")
    if atype == "press":
        item = action["item"]
        if not api.exists(item):
            raise BridgeError(f"item não existe na interface: {item}")
        api.press(item)
        return f"press {item}"

    if atype == "brush_file":
        path = action["path"]
        if not os.path.isfile(path):
            raise BridgeError(f"arquivo de brush não encontrado: {path}")
        if not api.exists(LOAD_BRUSH_ITEM):
            raise BridgeError(f"botão de carregar brush não encontrado: {LOAD_BRUSH_ITEM}")
        api.set_next_filename(path)
        api.press(LOAD_BRUSH_ITEM)
        return f"load {os.path.basename(path)}"

    raise BridgeError(f"tipo de ação não suportado na ponte: {atype!r}")


def read_command(path: str = COMMAND_FILE, now: float | None = None) -> dict | None:
    """Lê e apaga o comando pendente. Devolve None se não houver comando válido."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    now = time.time() if now is None else now
    if now - float(payload.get("created", 0)) > MAX_COMMAND_AGE_S:
        return None
    return payload


def write_result(result: dict, path: str = RESULT_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)


def run_pending(api=None, command_path: str = COMMAND_FILE,
                result_path: str = RESULT_FILE) -> dict:
    """Lê o comando pendente, executa as ações e grava o resultado."""
    result = {"time": time.time(), "ok": True, "done": [], "errors": []}
    try:
        payload = read_command(command_path)
    except (OSError, ValueError) as exc:
        payload = None
        result["errors"].append(f"comando ilegível: {exc}")
    if payload is None:
        if not result["errors"]:
            result["errors"].append("nenhum comando pendente (ou comando velho)")
        result["ok"] = False
    else:
        result["id"] = payload.get("id")
        for action in payload.get("actions", []):
            try:
                result["done"].append(execute_action(action, api))
            except Exception as exc:  # noqa: BLE001 — reporta qualquer falha
                result["ok"] = False
                result["errors"].append(f"{action!r}: {exc}")
    write_result(result, result_path)
    return result


# --- interface dentro do ZBrush ------------------------------------------

def _on_run(item: str) -> None:
    try:
        result = run_pending()
        tag = "ok" if result["ok"] else "ERRO"
        print(f"[radial-bridge] {tag}: {result['done']} {result['errors']}")
    except Exception:  # noqa: BLE001
        print("[radial-bridge] falha inesperada:\n" + traceback.format_exc())


def _on_test(item: str) -> None:
    """Botão de teste: aperta o brush Move pela ponte, sem o app externo."""
    try:
        print("[radial-bridge] teste:", execute_action({"type": "press", "item": "Brush:Move"}))
    except Exception as exc:  # noqa: BLE001
        print(f"[radial-bridge] teste falhou: {exc}")


def install() -> None:
    os.makedirs(COMMAND_DIR, exist_ok=True)
    if not zbc.exists(SUBPALETTE):
        zbc.add_subpalette(SUBPALETTE)
    if not zbc.exists(RUN_BUTTON):
        zbc.add_button(RUN_BUTTON, "Executa o comando do menu radial. "
                       "Atribua o atalho com Ctrl+Alt+clique.", _on_run, width=0.5)
    if not zbc.exists(TEST_BUTTON):
        zbc.add_button(TEST_BUTTON, "Teste: seleciona o brush Move.", _on_test, width=0.5)
    print(f"[radial-bridge] instalado em {SUBPALETTE}. Pasta de comandos: {COMMAND_DIR}")


# Não depende de __name__: não está documentado como o ZBrush executa o arquivo.
if zbc is not None:
    install()
