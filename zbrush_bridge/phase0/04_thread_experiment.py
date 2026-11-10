"""Phase 0, test 4 (EXPERIMENT) — can a thread run inside ZBrush?

The current bridge does NOT depend on this (it uses a button fired by a
hotkey). This test only exists to find out whether an "always listening"
bridge would be possible.

Save your scene first: the documentation says nothing about threads, and Maxon
warns that starting another Python interpreter with subprocess can crash ZBrush.

What to watch for ~5 s:
  1. Do the "[thread] tick" lines show up in the console?
  2. Does the interface keep responding meanwhile?
"""

import threading
import time


def worker():
    for i in range(5):
        print(f"[thread] tick {i + 1}/5")
        time.sleep(1)
    print("[thread] done")


threading.Thread(target=worker, daemon=True).start()
print("[phase0] thread started — poke around the ZBrush interface and watch the console")
