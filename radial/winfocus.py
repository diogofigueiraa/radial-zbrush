"""Garante que o ZBrush esteja em foco antes de o app enviar teclas.

Teclas enviadas pelo app vão para a janela ativa. Se a janela ativa não for o
ZBrush (a janela do run.bat, o navegador...), o atalho da ponte se perde.

Só funciona no Windows (usa a API Win32 via ctypes, sem dependências extras).
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
    # Exclui janelas que só citam o ZBrush no título (ex.: esta pasta no Explorer,
    # o cmd do run.bat em ...\radial-zbrush).
    return TITLE_HINT in t and "radial-zbrush" not in t and "cmd.exe" not in t


def foreground_title() -> str:
    if sys.platform != "win32":
        return ""
    ctypes, _, user32 = _win32()
    return _title(user32, ctypes, user32.GetForegroundWindow())


def find_zbrush_window():
    """Primeira janela visível cujo título parece ser do ZBrush."""
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
    """True se o ZBrush está (ou ficou) em foco. Fora do Windows, sempre True."""
    if sys.platform != "win32":
        return True
    ctypes, _, user32 = _win32()
    if is_zbrush_title(_title(user32, ctypes, user32.GetForegroundWindow())):
        return True
    hwnd = find_zbrush_window()
    if not hwnd:
        print("[radial] AVISO: não encontrei a janela do ZBrush aberta.")
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.08)
    ok = is_zbrush_title(_title(user32, ctypes, user32.GetForegroundWindow()))
    if not ok:
        print("[radial] AVISO: o ZBrush não está em foco e o Windows não deixou "
              "trazê-lo para a frente. Clique no ZBrush e tente de novo.")
    return ok
