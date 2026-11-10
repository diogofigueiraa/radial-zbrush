"""App entry point: wires up the hotkeys, the radial menu and the bridge.

Usage:
    python -m radial                 # uses config/menus.json
    python -m radial path.json       # another config file
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from . import config as config_mod
from .bridge_client import ActionRunner
from .editor import MenuEditor
from .hotkeys import HotkeyService, send_keys
from .overlay import RadialOverlay
from .winfocus import ensure_zbrush_foreground


def _tray_icon(color: str) -> QIcon:
    pm = QPixmap(32, 32)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor(color))
    p.setBrush(QColor(0, 0, 0, 0))
    pen = p.pen()
    pen.setWidth(5)
    p.setPen(pen)
    p.drawEllipse(5, 5, 22, 22)
    p.end()
    return QIcon(pm)


class RadialApp(QObject):
    def __init__(self, qt_app: QApplication, config_path: Path | None):
        super().__init__()
        self.qt_app = qt_app
        self.config_path = config_path
        self.cfg: dict = {}
        self.hotkeys: HotkeyService | None = None
        self.overlay: RadialOverlay | None = None
        self.runner: ActionRunner | None = None
        self.tray: QSystemTrayIcon | None = None
        self._open_index: int | None = None
        self.editor: MenuEditor | None = None

    # --- load / reload ---------------------------------------------------
    def load(self) -> None:
        self.cfg = config_mod.load(self.config_path)

        if self.hotkeys:
            self.hotkeys.stop()
        if self.overlay:
            self.overlay.close_menu()
            self.overlay.deleteLater()

        self.overlay = RadialOverlay(self.cfg["appearance"], self.cfg["selection"])
        self.overlay.selected.connect(self._on_selected)
        self.overlay.closed.connect(self._on_closed)

        hotkeys = [m["hotkey"] for m in self.cfg["menus"]]
        self.hotkeys = HotkeyService(hotkeys)
        self.hotkeys.menu_pressed.connect(self._on_menu_pressed)
        self.hotkeys.menu_released.connect(self._on_menu_released)
        self.hotkeys.escape_pressed.connect(self._on_escape)
        self.hotkeys.start()

        self.runner = ActionRunner(
            self.cfg["bridge"], send_keys, self.hotkeys.wait_modifiers_released,
            ensure_focus=ensure_zbrush_foreground,
        )
        names = ", ".join(f'{m["name"]} ({m["hotkey"]})' for m in self.cfg["menus"])
        print(f"[radial] menus loaded: {names}")

    def reload(self) -> None:
        try:
            self.load()
            if self.tray:
                self.tray.showMessage("Radial", "Config reloaded.")
        except config_mod.ConfigError as exc:
            QMessageBox.warning(None, "Radial — config error", str(exc))

    def open_editor(self) -> None:
        if self.editor and self.editor.isVisible():
            self.editor.raise_()
            self.editor.activateWindow()
            return
        # The editor works on a copy of the config and writes the file on Save.
        self.editor = MenuEditor(self.cfg, self.config_path)
        self.editor.setAttribute(Qt.WA_DeleteOnClose)
        self.editor.saved.connect(self.reload)
        self.editor.show()

    # --- events ------------------------------------------------------------
    def _on_menu_pressed(self, idx: int) -> None:
        mode = self.cfg["selection"]["mode"]
        if self.overlay.isVisible():
            if mode == "toggle" and self._open_index == idx:
                self.overlay.close_menu()
            return
        self._open_index = idx
        self.overlay.open_menu(self.cfg["menus"][idx], QCursor.pos())

    def _on_menu_released(self, idx: int) -> None:
        if self.cfg["selection"]["mode"] != "hold" or not self.overlay.isVisible():
            return
        if self.overlay.confirm_hovered():
            return
        # Quick tap without pointing: keep the menu open and wait for a click.
        if self.overlay.opened_ms >= self.cfg["selection"]["tap_ms"]:
            self.overlay.close_menu()

    def _on_escape(self) -> None:
        if self.overlay and self.overlay.isVisible():
            self.overlay.close_menu()

    def _on_closed(self) -> None:
        self._open_index = None

    def _on_selected(self, slot: dict) -> None:
        print(f"[radial] selected: {slot['label']} -> {slot['action']}")
        self.runner.run(slot["action"])

    # --- system tray -------------------------------------------------------
    def setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(_tray_icon(self.cfg["appearance"]["accent_color"]))
        self.tray.setToolTip("Radial menu for ZBrush")
        menu = QMenu()
        act_edit = QAction("Edit menus…", menu)
        act_edit.triggered.connect(self.open_editor)
        act_reload = QAction("Reload config", menu)
        act_reload.triggered.connect(self.reload)
        act_quit = QAction("Quit", menu)
        act_quit.triggered.connect(self.quit)
        menu.addAction(act_edit)
        menu.addAction(act_reload)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.show()
        self._tray_menu = menu  # keep a live reference

    def quit(self) -> None:
        if self.hotkeys:
            self.hotkeys.stop()
        self.qt_app.quit()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    config_path = Path(argv[0]) if argv else None

    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    app = RadialApp(qt_app, config_path)
    try:
        app.load()
    except config_mod.ConfigError as exc:
        QMessageBox.critical(None, "Radial — config error", str(exc))
        return 1
    app.setup_tray()
    print("[radial] running. Use the tray icon to reload or quit.")
    return qt_app.exec()
