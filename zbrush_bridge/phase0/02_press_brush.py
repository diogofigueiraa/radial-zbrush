"""Phase 0, test 2 — switch brush by item path.

Asks for an item path (e.g. Brush:Move, Brush:ClayBuildup), checks that it
exists and presses it. If it does not exist, record a macro in Python
Scripting > New Macro, pick the brush and read the item path the macro logged.
"""

from zbrush import commands as zbc

item = zbc.ask_string("Brush:Move", "Brush item path")
if not item:
    print("[phase0] cancelled")
elif not zbc.exists(item):
    print(f"[phase0] DOES NOT exist: {item}")
    zbc.message_ok(f"Item not found:\n{item}", "Phase 0 — test 2")
else:
    zbc.press(item)
    print(f"[phase0] OK, pressed: {item}")
