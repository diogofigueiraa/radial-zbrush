"""Fase 0, teste 4 (EXPERIMENTO) — uma thread consegue rodar dentro do ZBrush?

A ponte atual NÃO depende disso (usa um botão disparado por atalho). Este
teste existe só para saber se uma ponte "sempre escutando" seria possível.

Salve sua cena antes: a documentação não fala de threads, e a Maxon avisa que
iniciar outro interpretador Python com subprocess pode derrubar o ZBrush.

O que observar por ~5 s:
  1. As linhas "[thread] tick" aparecem no console?
  2. A interface continua respondendo enquanto isso?
"""

import threading
import time


def worker():
    for i in range(5):
        print(f"[thread] tick {i + 1}/5")
        time.sleep(1)
    print("[thread] fim")


threading.Thread(target=worker, daemon=True).start()
print("[fase0] thread iniciada — mexa na interface do ZBrush e observe o console")
