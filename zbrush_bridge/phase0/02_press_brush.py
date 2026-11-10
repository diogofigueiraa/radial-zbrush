"""Fase 0, teste 2 — trocar de brush pelo item path.

Pergunta um item path (ex.: Brush:Move, Brush:ClayBuildup), confere se existe
e aperta. Se não existir, grave uma macro em Python Scripting > New Macro,
escolha o brush e leia o item path que a macro registrou.
"""

from zbrush import commands as zbc

item = zbc.ask_string("Brush:Move", "Item path do brush")
if not item:
    print("[fase0] cancelado")
elif not zbc.exists(item):
    print(f"[fase0] NÃO existe: {item}")
    zbc.message_ok(f"Item não encontrado:\n{item}", "Fase 0 — teste 2")
else:
    zbc.press(item)
    print(f"[fase0] OK, apertado: {item}")
