"""Fase 0, teste 1 — o Python do ZBrush funciona?

ZBrush > ZScript > Python Scripting > Load > este arquivo.
Ative ZScript > Script Window Mode > Python Output para ver o print no console.
"""

import sys

from zbrush import commands as zbc

print("[fase0] Olá do Python dentro do ZBrush")
print("[fase0] Python", sys.version)
print("[fase0] system_info:", zbc.system_info())
zbc.message_ok("O Python está rodando dentro do ZBrush.", "Fase 0 — teste 1")
