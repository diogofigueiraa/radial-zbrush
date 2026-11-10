"""Menu editor window: edit menus, hotkeys and slots without touching the JSON."""

from __future__ import annotations

import copy
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QKeySequenceEdit, QLabel, QLineEdit, QListWidget, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from . import config as config_mod
from . import editing

ACTION_LABELS = {
    "press": "Press item (Palette:Button)",
    "brush_file": "Load brush file (.ZBP)",
    "keys": "Send keys",
}
FIELD_HINTS = {
    "press": "Brush:Move",
    "brush_file": "C:/path/to/Brush.ZBP",
    "keys": "<shift>+f",
}


class MenuEditor(QDialog):
    """Edits a copy of the config. Nothing is written until Save is pressed."""

    saved = Signal()

    def __init__(self, cfg: dict, path: Path | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Radial — Menu editor")
        self.resize(900, 520)
        self._cfg = copy.deepcopy(cfg)
        self._path = path
        self._menu_row = -1
        self._slot_row = -1
        self._loading = False
        self._dirty = False
        self._build_ui()
        self._fill_menus()

    # --- UI construction ---------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        columns = QHBoxLayout()
        root.addLayout(columns, 1)

        # Menus column
        self.menu_list = QListWidget()
        self.menu_list.currentRowChanged.connect(self._on_menu_selected)
        columns.addWidget(self._list_group(
            "Menus", self.menu_list,
            [("Add", self._add_menu), ("Remove", self._remove_menu),
             ("↑", lambda: self._move_menu(-1)), ("↓", lambda: self._move_menu(1))],
            self._menu_fields(),
        ), 1)

        # Slots column
        self.slot_list = QListWidget()
        self.slot_list.currentRowChanged.connect(self._on_slot_selected)
        self.slot_list.setDragDropMode(QListWidget.NoDragDrop)
        columns.addWidget(self._list_group(
            "Slots", self.slot_list,
            [("Add", self._add_slot), ("Duplicate", self._duplicate_slot),
             ("Remove", self._remove_slot),
             ("↑", lambda: self._move_slot(-1)), ("↓", lambda: self._move_slot(1))],
        ), 1)

        # Slot form
        self.slot_box = QGroupBox("Slot")
        form = QFormLayout(self.slot_box)
        self.label_edit = QLineEdit()
        self.label_edit.textEdited.connect(self._on_slot_changed)
        form.addRow("Label", self.label_edit)

        self.type_combo = QComboBox()
        for key, text in ACTION_LABELS.items():
            self.type_combo.addItem(text, key)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Action", self.type_combo)

        self.value_edit = QLineEdit()
        self.value_edit.textEdited.connect(self._on_slot_changed)
        self.browse_btn = QPushButton("Browse…")
        self.browse_btn.clicked.connect(self._browse_brush)
        value_row = QHBoxLayout()
        value_row.addWidget(self.value_edit, 1)
        value_row.addWidget(self.browse_btn)
        form.addRow("Value", value_row)

        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("default")
        self.color_edit.textEdited.connect(self._on_slot_changed)
        color_btn = QPushButton("Pick…")
        color_btn.clicked.connect(self._pick_color)
        color_row = QHBoxLayout()
        color_row.addWidget(self.color_edit, 1)
        color_row.addWidget(color_btn)
        form.addRow("Color", color_row)

        self.icon_edit = QLineEdit()
        self.icon_edit.setPlaceholderText("none (shows the label)")
        self.icon_edit.textEdited.connect(self._on_slot_changed)
        icon_btn = QPushButton("Browse…")
        icon_btn.clicked.connect(self._browse_icon)
        icon_row = QHBoxLayout()
        icon_row.addWidget(self.icon_edit, 1)
        icon_row.addWidget(icon_btn)
        form.addRow("Icon (PNG)", icon_row)
        columns.addWidget(self.slot_box, 2)

        # Footer
        self.status = QLabel("")
        self.status.setStyleSheet("color: #c0392b;")
        root.addWidget(self.status)
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.save_btn = QPushButton("Save && reload")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._save)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        footer.addWidget(self.save_btn)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def _menu_fields(self) -> QWidget:
        box = QWidget()
        form = QFormLayout(box)
        form.setContentsMargins(0, 4, 0, 0)
        self.menu_name_edit = QLineEdit()
        self.menu_name_edit.textEdited.connect(self._on_menu_changed)
        form.addRow("Name", self.menu_name_edit)
        self.hotkey_edit = QKeySequenceEdit()
        self.hotkey_edit.setMaximumSequenceLength(1)
        self.hotkey_edit.keySequenceChanged.connect(self._on_hotkey_changed)
        form.addRow("Hotkey", self.hotkey_edit)
        self.hotkey_label = QLabel("")
        self.hotkey_label.setStyleSheet("color: gray;")
        form.addRow("", self.hotkey_label)
        return box

    def _list_group(self, title, list_widget, buttons, extra: QWidget | None = None) -> QGroupBox:
        box = QGroupBox(title)
        lay = QVBoxLayout(box)
        lay.addWidget(list_widget, 1)
        row = QHBoxLayout()
        for text, handler in buttons:
            b = QPushButton(text)
            b.clicked.connect(handler)
            row.addWidget(b)
        lay.addLayout(row)
        if extra:
            lay.addWidget(extra)
        return box

    # --- helpers -----------------------------------------------------------
    @property
    def _menus(self) -> list[dict]:
        return self._cfg["menus"]

    def _menu(self) -> dict | None:
        return self._menus[self._menu_row] if 0 <= self._menu_row < len(self._menus) else None

    def _slot(self) -> dict | None:
        menu = self._menu()
        if menu and 0 <= self._slot_row < len(menu["slots"]):
            return menu["slots"][self._slot_row]
        return None

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.status.setText("")

    # --- list population ---------------------------------------------------
    def _fill_menus(self, select: int = 0) -> None:
        self._loading = True
        self.menu_list.clear()
        for m in self._menus:
            self.menu_list.addItem(m.get("name") or "(unnamed)")
        self._loading = False
        if self._menus:
            self.menu_list.setCurrentRow(max(0, min(select, len(self._menus) - 1)))
        else:
            self._on_menu_selected(-1)

    def _fill_slots(self, select: int = 0) -> None:
        self._loading = True
        self.slot_list.clear()
        menu = self._menu()
        for s in (menu["slots"] if menu else []):
            self.slot_list.addItem(s.get("label") or "(no label)")
        self._loading = False
        count = self.slot_list.count()
        if count:
            self.slot_list.setCurrentRow(max(0, min(select, count - 1)))
        else:
            self._on_slot_selected(-1)

    # --- selection ---------------------------------------------------------
    def _on_menu_selected(self, row: int) -> None:
        if self._loading:
            return
        self._menu_row = row
        menu = self._menu()
        self._loading = True
        self.menu_name_edit.setText(menu["name"] if menu else "")
        self.hotkey_edit.setKeySequence(QKeySequence())
        self.hotkey_label.setText(
            editing.pynput_to_display(menu["hotkey"]) + f"  ({menu['hotkey']})"
            if menu and menu.get("hotkey") else "")
        self._loading = False
        for w in (self.menu_name_edit, self.hotkey_edit):
            w.setEnabled(menu is not None)
        self._fill_slots()

    def _on_slot_selected(self, row: int) -> None:
        if self._loading:
            return
        self._slot_row = row
        slot = self._slot()
        self._loading = True
        self.slot_box.setEnabled(slot is not None)
        if slot:
            action = slot["action"]
            atype = action.get("type", "press")
            self.label_edit.setText(slot.get("label", ""))
            self.type_combo.setCurrentIndex(self.type_combo.findData(atype))
            self.value_edit.setText(action.get(editing.ACTION_FIELDS[atype], ""))
            self.color_edit.setText(slot.get("color", ""))
            self.icon_edit.setText(slot.get("icon", ""))
            self._refresh_value_hint(atype)
        else:
            for w in (self.label_edit, self.value_edit, self.color_edit, self.icon_edit):
                w.clear()
        self._loading = False

    def _refresh_value_hint(self, atype: str) -> None:
        self.value_edit.setPlaceholderText(FIELD_HINTS[atype])
        self.browse_btn.setVisible(atype == "brush_file")

    # --- edits -------------------------------------------------------------
    def _on_menu_changed(self) -> None:
        menu = self._menu()
        if self._loading or not menu:
            return
        menu["name"] = self.menu_name_edit.text()
        item = self.menu_list.item(self._menu_row)
        if item:
            item.setText(menu["name"] or "(unnamed)")
        self._mark_dirty()

    def _on_hotkey_changed(self, seq: QKeySequence) -> None:
        menu = self._menu()
        if self._loading or not menu or seq.isEmpty():
            return
        combo = editing.qt_sequence_to_pynput(seq.toString(QKeySequence.PortableText))
        if not combo:
            self.status.setText("That key combination is not supported.")
            return
        menu["hotkey"] = combo
        self.hotkey_label.setText(f"{editing.pynput_to_display(combo)}  ({combo})")
        self._mark_dirty()

    def _on_slot_changed(self) -> None:
        slot = self._slot()
        if self._loading or not slot:
            return
        slot["label"] = self.label_edit.text()
        atype = self.type_combo.currentData()
        slot["action"] = {"type": atype, editing.ACTION_FIELDS[atype]: self.value_edit.text()}
        if self.color_edit.text():
            slot["color"] = self.color_edit.text()
        else:
            slot.pop("color", None)
        if self.icon_edit.text():
            slot["icon"] = self.icon_edit.text()
        else:
            slot.pop("icon", None)
        item = self.slot_list.item(self._slot_row)
        if item:
            item.setText(slot["label"] or "(no label)")
        self._mark_dirty()

    def _on_type_changed(self) -> None:
        if self._loading:
            return
        atype = self.type_combo.currentData()
        self._refresh_value_hint(atype)
        self.value_edit.clear()  # the old value belongs to another action type
        self._on_slot_changed()

    # --- pickers -----------------------------------------------------------
    def _browse_brush(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Brush file", "", "ZBrush brush (*.ZBP)")
        if path:
            self.value_edit.setText(path.replace("\\", "/"))
            self._on_slot_changed()

    def _browse_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Icon", "", "Images (*.png)")
        if path:
            self.icon_edit.setText(path.replace("\\", "/"))
            self._on_slot_changed()

    def _pick_color(self) -> None:
        start = QColor(self.color_edit.text() or self._cfg["appearance"]["slot_color"])
        color = QColorDialog.getColor(start, self, "Slot color")
        if color.isValid():
            self.color_edit.setText(color.name())
            self._on_slot_changed()

    # --- menu / slot list operations -----------------------------------------
    def _add_menu(self) -> None:
        self._menus.append(editing.new_menu(self._menus))
        self._mark_dirty()
        self._fill_menus(len(self._menus) - 1)

    def _remove_menu(self) -> None:
        if not self._menu():
            return
        if len(self._menus) == 1:
            self.status.setText("At least one menu is required.")
            return
        del self._menus[self._menu_row]
        self._mark_dirty()
        self._fill_menus(self._menu_row)

    def _move_menu(self, delta: int) -> None:
        if not self._menu():
            return
        new = editing.move_item(self._menus, self._menu_row, delta)
        self._mark_dirty()
        self._fill_menus(new)

    def _add_slot(self) -> None:
        menu = self._menu()
        if not menu:
            return
        if len(menu["slots"]) >= editing.MAX_SLOTS:
            self.status.setText(f"At most {editing.MAX_SLOTS} slots per menu.")
            return
        menu["slots"].append(editing.new_slot())
        self._mark_dirty()
        self._fill_slots(len(menu["slots"]) - 1)

    def _duplicate_slot(self) -> None:
        menu, slot = self._menu(), self._slot()
        if not slot:
            return
        if len(menu["slots"]) >= editing.MAX_SLOTS:
            self.status.setText(f"At most {editing.MAX_SLOTS} slots per menu.")
            return
        menu["slots"].insert(self._slot_row + 1, copy.deepcopy(slot))
        self._mark_dirty()
        self._fill_slots(self._slot_row + 1)

    def _remove_slot(self) -> None:
        menu = self._menu()
        if not self._slot():
            return
        if len(menu["slots"]) == 1:
            self.status.setText("A menu needs at least one slot.")
            return
        del menu["slots"][self._slot_row]
        self._mark_dirty()
        self._fill_slots(self._slot_row)

    def _move_slot(self, delta: int) -> None:
        menu = self._menu()
        if not self._slot():
            return
        new = editing.move_item(menu["slots"], self._slot_row, delta)
        self._mark_dirty()
        self._fill_slots(new)

    # --- save / close ------------------------------------------------------
    def _save(self) -> bool:
        error = editing.validate_menus(self._menus, self._cfg)
        if error:
            self.status.setText(error)
            return False
        for menu in self._menus:
            for slot in menu["slots"]:
                editing.clean_slot(slot)
        try:
            config_mod.save(self._cfg, self._path)
        except OSError as exc:
            self.status.setText(f"Could not write the config: {exc}")
            return False
        self._dirty = False
        self.status.setText("")
        self.saved.emit()
        return True

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self._dirty:
            answer = QMessageBox.question(
                self, "Unsaved changes", "Save changes before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if answer == QMessageBox.Cancel or (answer == QMessageBox.Save and not self._save()):
                event.ignore()
                return
        event.accept()
