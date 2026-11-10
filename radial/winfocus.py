"""Makes sure ZBrush is focused before the app sends keys.

Keys sent by the app go to the active window. If the active window is not
ZBrush (the run.bat window, the browser...), the bridge hotkey is lost.

Windows only (uses the Win32 API through ctypes, no extra dependencies).
"""

from __future__ import annotations

import sys
import time

TITLE_HINT = "zbrush"


def _win32():
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    return ctypes, wintypes, user32


def _title(user32, ctypes, hwnd) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def is_zbrush_title(title: str) -> bool:
    t = title.lower()
    # Excludes windows that merely mention ZBrush in the title (e.g. this folder
    # in Explorer, the run.bat console at ...\radial-zbrush).
    return TITLE_HINT in t and "radial-zbrush" not in t and "cmd.exe" not in t


def foreground_title() -> str:
    if sys.platform != "win32":
        return ""
    ctypes, _, user32 = _win32()
    return _title(user32, ctypes, user32.GetForegroundWindow())


def find_zbrush_window():
    """First visible window whose title looks like ZBrush's."""
    ctypes, wintypes, user32 = _win32()
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd) and is_zbrush_title(_title(user32, ctypes, hwnd)):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(callback, 0)
    return found[0] if found else None


def ensure_zbrush_foreground() -> bool:
    """True if ZBrush is (or became) focused. Always True outside Windows."""
    if sys.platform != "win32":
        return True
    ctypes, _, user32 = _win32()
    if is_zbrush_title(_title(user32, ctypes, user32.GetForegroundWindow())):
        return True
    hwnd = find_zbrush_window()
    if not hwnd:
        print("[radial] WARNING: could not find an open ZBrush window.")
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.08)
    ok = is_zbrush_title(_title(user32, ctypes, user32.GetForegroundWindow()))
    if not ok:
        print("[radial] WARNING: ZBrush is not focused and Windows would not "
              "bring it to the front. Click on ZBrush and try again.")
    return ok
