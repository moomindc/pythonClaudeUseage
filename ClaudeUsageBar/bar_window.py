from datetime import datetime, timezone
from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

import config as cfg_mod

_GREY = QColor("#888888")


class BarWindow(QWidget):
    reconfigure_requested = pyqtSignal()

    def __init__(self, cfg: dict) -> None:
        super().__init__()
        self._cfg = cfg
        self._pct: float = 0.0
        self._reset_at: Optional[datetime] = None
        self._error_text: Optional[str] = None
        self._drag_origin: Optional[QPoint] = None

        self._setup_window()
        self._place_window()

        # Repaint every second so the countdown ticks without a network call
        tick = QTimer(self)
        tick.timeout.connect(self.update)
        tick.start(1000)

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool          # keeps bar off the taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        w = self._cfg.get("window", {}).get("width", 450)
        self.setFixedSize(w, 27)

    def _place_window(self) -> None:
        win = self._cfg.get("window", {})
        x = win.get("x")
        y = win.get("y", 10)
        if x is None:
            screen = QApplication.primaryScreen().geometry()
            x = screen.width() - self.width() - 10
        self.move(x, y)

    def _color(self, key: str, fallback: str) -> QColor:
        return QColor(self._cfg.get("colors", {}).get(key, fallback))

    # Called from the main thread via signal connection
    def set_data(
        self,
        pct: float,
        reset_at: Optional[datetime],
        error_text: Optional[str],
    ) -> None:
        if pct >= 0:
            self._pct = min(100.0, max(0.0, pct))
        self._reset_at = reset_at
        self._error_text = error_text
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        w, h = self.width(), self.height()

        # Background (unused tokens)
        p.fillRect(0, 0, w, h, self._color("background", "#030A05"))

        # Foreground (used tokens)
        fill_px = int(w * self._pct / 100.0)
        if fill_px > 0:
            p.fillRect(0, 0, fill_px, h, self._color("fill", "#14532D"))

        # Overlay text
        font = QFont("Segoe UI", 8)
        p.setFont(font)
        fm = QFontMetrics(font)

        if self._error_text:
            text = self._error_text
            p.setPen(_GREY)
        elif self._reset_at is None:
            text = "—"
            p.setPen(_GREY)
        else:
            remaining = (self._reset_at - datetime.now(timezone.utc)).total_seconds()
            if remaining <= 0:
                text = "resetting…"
            else:
                hh = int(remaining) // 3600
                mm = (int(remaining) % 3600) // 60
                text = f"resets in {hh}h {mm:02d}m"
            p.setPen(self._color("text", "#86EFAC"))

        tw = fm.horizontalAdvance(text)
        # Baseline so text is vertically centred
        baseline = (h - fm.height()) // 2 + fm.ascent()
        p.drawText(w - tw - 6, baseline, text)

        # Centered percentage
        if not self._error_text:
            pct_text = f"{self._pct:.0f}%"
            ptw = fm.horizontalAdvance(pct_text)
            p.setPen(self._color("text", "#86EFAC"))
            p.drawText(6, baseline, pct_text)

    # --- Drag to reposition ---

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = (
                e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        if self._drag_origin and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_origin)

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            pos = self.pos()
            self._cfg.setdefault("window", {})
            self._cfg["window"]["x"] = pos.x()
            self._cfg["window"]["y"] = pos.y()
            cfg_mod.save(self._cfg)

    # --- Right-click context menu ---

    def contextMenuEvent(self, e) -> None:  # noqa: N802
        menu = QMenu(self)
        menu.addAction("Reconfigure…", self.reconfigure_requested.emit)
        menu.addSeparator()
        menu.addAction("Exit", QApplication.quit)
        menu.exec(e.globalPos())
