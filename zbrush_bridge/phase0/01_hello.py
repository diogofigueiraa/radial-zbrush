"""Phase 0, test 1 — does ZBrush's Python work?

ZBrush > ZScript > Python Scripting > Load > this file.
Enable ZScript > Script Window Mode > Python Output to see the print in the console.
"""

import sys

from zbrush import commands as zbc

print("[phase0] Hello from Python inside ZBrush")
print("[phase0] Python", sys.version)
print("[phase0] system_info:", zbc.system_info())
zbc.message_ok("Python is running inside ZBrush.", "Phase 0 — test 1")
