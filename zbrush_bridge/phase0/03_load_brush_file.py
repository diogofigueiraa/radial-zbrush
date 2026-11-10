"""Fase 0, teste 3 — carregar um brush a partir de um arquivo .ZBP.

Usa set_next_filename (pré-define o arquivo do próximo load) e aperta o botão de
carregar brush. O nome desse botão precisa ser confirmado: o teste mostra se
"Brush:Load Brush" existe. Se não existir, grave uma macro clicando no botão
de carregar brush e copie o item path para LOAD_BRUSH_ITEM aqui e em
radial_bridge.py.
"""

import os

from zbrush import commands as zbc

LOAD_BRUSH_ITEM = "Brush:Load Brush"

print(f"[fase0] {LOAD_BRUSH_ITEM} existe? {zbc.exists(LOAD_BRUSH_ITEM)}")

path = zbc.ask_string("", "Caminho completo do arquivo .ZBP")
if not path:
    print("[fase0] cancelado")
elif not os.path.isfile(path):
    print(f"[fase0] arquivo não encontrado: {path}")
elif not zbc.exists(LOAD_BRUSH_ITEM):
    zbc.message_ok(f"Botão não encontrado: {LOAD_BRUSH_ITEM}", "Fase 0 — teste 3")
else:
    zbc.set_next_filename(path)
    zbc.press(LOAD_BRUSH_ITEM)
    print(f"[fase0] pedido de load enviado: {path}")
    print("[fase0] Confira: abriu janela de arquivo? (não deveria) O brush trocou?")
