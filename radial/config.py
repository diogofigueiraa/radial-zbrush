"""Leitura e validação do config/menus.json.

O JSON é a fonte da verdade. Valores que faltarem recebem os padrões abaixo.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "menus.json"

VALID_ACTIONS = {"press", "brush_file", "keys"}
VALID_MODES = {"hold", "toggle"}

DEFAULTS: dict[str, Any] = {
    "bridge": {
        # "zscript" para ZBrush 2023/2024, "python" para ZBrush 2026.
        "protocol": "zscript",
        # Atalho que o app aperta para disparar o botão "Run" da ponte no ZBrush.
        # Precisa ser o MESMO atalho atribuído ao botão ZPlugin > Radial Bridge > Run.
        "trigger_hotkey": "<ctrl>+<alt>+<shift>+j",
        # Pasta onde o app escreve o comando e a ponte lê. Relativa à raiz do
        # projeto. No ZScript, a mesma pasta está em rbDir (RadialBridge.txt).
        "command_dir": "zbrush_bridge/data",
    },
    "appearance": {
        "radius": 110,
        "inner_radius": 36,
        "slot_size": 58,
        "ring_color": "#1E1E22",
        "slot_color": "#2B2B31",
        "accent_color": "#FF8A3D",
        "text_color": "#F2F2F2",
        "opacity": 0.94,
        "font_size": 10,
    },
    "selection": {
        # hold: segure o atalho, aponte e solte. toggle: aperte, aponte e clique.
        "mode": "hold",
        # Em hold, um toque rápido (menos que isso) deixa o menu aberto em modo clique.
        "tap_ms": 220,
        # Seleciona ao parar o mouse sobre um slot por X ms. 0 = desligado.
        "hover_dwell_ms": 0,
        # Seleciona ao "arremessar" o mouse além do anel.
        "flick": True,
        # Distância do centro (em px) que conta como flick, além do raio + slot.
        "flick_margin": 30,
    },
    "menus": [],
}


class ConfigError(ValueError):
    pass


def _merge(defaults: dict, data: dict) -> dict:
    out = copy.deepcopy(defaults)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


VALID_PROTOCOLS = {"zscript", "python"}


def validate(cfg: dict) -> dict:
    protocol = cfg["bridge"]["protocol"]
    if protocol not in VALID_PROTOCOLS:
        raise ConfigError(f"bridge.protocol inválido: {protocol!r} (use zscript ou python)")

    mode = cfg["selection"]["mode"]
    if mode not in VALID_MODES:
        raise ConfigError(f"selection.mode inválido: {mode!r} (use hold ou toggle)")

    menus = cfg.get("menus")
    if not isinstance(menus, list) or not menus:
        raise ConfigError("defina pelo menos um menu em 'menus'")

    seen_hotkeys: set[str] = set()
    for mi, menu in enumerate(menus):
        where = f"menus[{mi}]"
        if not menu.get("name"):
            raise ConfigError(f"{where}: falta 'name'")
        hotkey = menu.get("hotkey")
        if not hotkey:
            raise ConfigError(f"{where}: falta 'hotkey'")
        if hotkey in seen_hotkeys:
            raise ConfigError(f"{where}: atalho repetido {hotkey!r}")
        seen_hotkeys.add(hotkey)

        slots = menu.get("slots")
        if not isinstance(slots, list) or not slots:
            raise ConfigError(f"{where}: precisa de pelo menos um slot")
        if len(slots) > 16:
            raise ConfigError(f"{where}: máximo de 16 slots")
        for si, slot in enumerate(slots):
            swhere = f"{where}.slots[{si}]"
            if not slot.get("label"):
                raise ConfigError(f"{swhere}: falta 'label'")
            action = slot.get("action") or {}
            atype = action.get("type")
            if atype not in VALID_ACTIONS:
                raise ConfigError(
                    f"{swhere}: action.type inválido {atype!r} "
                    f"(use {', '.join(sorted(VALID_ACTIONS))})"
                )
            required = {"press": "item", "brush_file": "path", "keys": "keys"}[atype]
            if not action.get(required):
                raise ConfigError(f"{swhere}: action '{atype}' precisa de '{required}'")
    return cfg


def load(path: str | Path | None = None) -> dict:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON inválido em {path}: {exc}") from exc
    return validate(_merge(DEFAULTS, data))


def save(cfg: dict, path: str | Path | None = None) -> None:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    validate(cfg)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
