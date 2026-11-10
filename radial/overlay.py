"""A janela do menu radial.

- Sem borda, transparente, sempre por cima e SEM pegar foco: o ZBrush continua
  ativo e recebe as teclas que o app envia depois.
- O hover é calculado por polling do cursor (60 Hz), então funciona mesmo
  quando o mouse sai da janela (necessário para o flick).
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from . import geometry

PADDING = 24


class RadialOverlay(QWidget):
    selected = Signal(dict)   # o slot escolhido
    closed = Signal()

    def __init__(self, appearance: dict, selection: dict):
        super().__init__(None)
        self.app_cfg = appearance
        self.sel_cfg = selection
        self.menu: dict | None = None
        self.hovered: int | None = None
        self._hover_since = 0.0
        self._opened_at = 0.0
        self._icons: dict[str, QPixmap] = {}
        self._center_global = QPoint()

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)

        side = 2 * (self.app_cfg["radius"] + self.app_cfg["slot_size"]) + 2 * PADDING
        self.setFixedSize(side, side)

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    # --- abrir / fechar ------------------------------------------------
    @property
    def opened_ms(self) -> float:
        return (time.monotonic() - self._opened_at) * 1000.0

    def open_menu(self, menu: dict, center: QPoint) -> None:
        self.menu = menu
        self.hovered = None
        self._opened_at = time.monotonic()
        self._center_global = center
        self._load_icons(menu)
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)
        self.show()
        self.raise_()
        self._timer.start()
        self.update()

    def close_menu(self) -> None:
        if not self.isVisible():
            return
        self._timer.stop()
        self.hide()
        self.menu = None
        self.hovered = None
        self.closed.emit()

    def confirm_hovered(self) -> bool:
        """Seleciona o slot sob o cursor. Devolve False se não havia nenhum."""
        if self.menu is None or self.hovered is None:
            return False
        slot = self.menu["slots"][self.hovered]
        self.close_menu()
        self.selected.emit(slot)
        return True

    # --- entrada ----------------------------------------------------------
    def _rel_cursor(self) -> tuple[float, float]:
        p = QCursor.pos()
        return (p.x() - self._center_global.x(), p.y() - self._center_global.y())

    def _tick(self) -> None:
        if self.menu is None:
            return
        n = len(self.menu["slots"])
        dx, dy = self._rel_cursor()
        r = self.app_cfg["radius"]
        s = self.app_cfg["slot_size"]

        # Flick: passou do anel -> escolhe o slot naquela direção.
        flick_radius = r + s / 2 + self.sel_cfg["flick_margin"]
        if self.sel_cfg["flick"] and geometry.is_flick(dx, dy, flick_radius):
            self.hovered = geometry.angle_to_slot(dx, dy, n)
            self.confirm_hovered()
            return

        hit = geometry.hit_test(dx, dy, n, self.app_cfg["inner_radius"])
        if hit != self.hovered:
            self.hovered = hit
            self._hover_since = time.monotonic()
            self.update()

        dwell = self.sel_cfg["hover_dwell_ms"]
        if dwell and self.hovered is not None:
            if (time.monotonic() - self._hover_since) * 1000.0 >= dwell:
                self.confirm_hovered()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (API do Qt)
        if event.button() == Qt.LeftButton:
            if not self.confirm_hovered():
                self.close_menu()  # clique no centro fecha
        elif event.button() == Qt.RightButton:
            self.close_menu()

    # --- desenho ----------------------------------------------------------
    def _load_icons(self, menu: dict) -> None:
        for slot in menu["slots"]:
            icon = slot.get("icon")
            if icon and icon not in self._icons and Path(icon).is_file():
                pm = QPixmap(icon)
                if not pm.isNull():
                    self._icons[icon] = pm

    def paintEvent(self, event) -> None:  # noqa: N802
        if self.menu is None:
            return
        cfg = self.app_cfg
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(cfg["opacity"])

        c = QPointF(self.width() / 2, self.height() / 2)
        r = cfg["radius"]
        s = cfg["slot_size"]
        n = len(self.menu["slots"])
        ring = QColor(cfg["ring_color"])
        slot_col = QColor(cfg["slot_color"])
        accent = QColor(cfg["accent_color"])
        text_col = QColor(cfg["text_color"])

        # Anel de fundo
        pen = QPen(ring, s + 14)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, r, r)

        # Centro com o nome do menu
        p.setPen(Qt.NoPen)
        p.setBrush(ring)
        p.drawEllipse(c, cfg["inner_radius"], cfg["inner_radius"])
        font = QFont()
        font.setPointSize(cfg["font_size"])
        font.setBold(True)
        p.setFont(font)
        p.setPen(text_col)
        ir = cfg["inner_radius"]
        p.drawText(QRectF(c.x() - ir, c.y() - ir, 2 * ir, 2 * ir),
                   Qt.AlignCenter | Qt.TextWordWrap, self.menu["name"])

        # Slots
        font.setBold(False)
        p.setFont(font)
        for i, slot in enumerate(self.menu["slots"]):
            ox, oy = geometry.slot_position(i, n, r)
            sc = QPointF(c.x() + ox, c.y() + oy)
            is_hover = i == self.hovered
            base = QColor(slot.get("color", slot_col.name())) if slot.get("color") else slot_col

            p.setPen(QPen(accent, 3) if is_hover else Qt.NoPen)
            p.setBrush(base.lighter(130) if is_hover else base)
            size = s * (1.12 if is_hover else 1.0)
            p.drawEllipse(sc, size / 2, size / 2)

            rect = QRectF(sc.x() - size / 2, sc.y() - size / 2, size, size)
            pm = self._icons.get(slot.get("icon", ""))
            if pm is not None:
                icon_rect = rect.adjusted(size * 0.18, size * 0.18, -size * 0.18, -size * 0.18)
                p.drawPixmap(icon_rect.toRect(), pm)
            else:
                p.setPen(accent if is_hover else text_col)
                p.drawText(rect.adjusted(4, 4, -4, -4),
                           Qt.AlignCenter | Qt.TextWordWrap, slot["label"])
        p.end()


def screen_center_under_cursor() -> QPoint:
    """Posição do cursor (o menu abre centrado nele)."""
    pos = QCursor.pos()
    screen = QGuiApplication.screenAt(pos)
    return pos if screen else QPoint(0, 0)
