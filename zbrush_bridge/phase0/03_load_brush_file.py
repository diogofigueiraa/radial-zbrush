"""Phase 0, test 3 — load a brush from a .ZBP file.

Uses set_next_filename (pre-sets the file for the next load) and presses the
Load Brush button. That button's name must be confirmed: the test shows whether
"Brush:Load Brush" exists. If it does not, record a macro by clicking the
Load Brush button and copy the item path into LOAD_BRUSH_ITEM here and in
radial_bridge.py.
"""

import os

from zbrush import commands as zbc

LOAD_BRUSH_ITEM = "Brush:Load Brush"

print(f"[phase0] {LOAD_BRUSH_ITEM} exists? {zbc.exists(LOAD_BRUSH_ITEM)}")

path = zbc.ask_string("", "Full path of the .ZBP file")
if not path:
    print("[phase0] cancelled")
elif not os.path.isfile(path):
    print(f"[phase0] file not found: {path}")
elif not zbc.exists(LOAD_BRUSH_ITEM):
    zbc.message_ok(f"Button not found: {LOAD_BRUSH_ITEM}", "Phase 0 — test 3")
else:
    zbc.set_next_filename(path)
    zbc.press(LOAD_BRUSH_ITEM)
    print(f"[phase0] load request sent: {path}")
    print("[phase0] Check: did a file dialog open? (it should not) Did the brush change?")
