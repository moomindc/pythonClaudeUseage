# bar_window.py
# Defines the thin floating progress bar that sits on screen at all times. The bar
# is drawn entirely by hand in paintEvent — there are no child widgets. A one-second
# timer ticks the countdown display without making any network calls.

from datetime import datetime, timezone
from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

import config as cfg_mod

# _GREY
# A muted grey colour used for text when no live data is available yet, or when an
# error message is being displayed instead of the normal countdown.
_GREY = QColor("#888888")


# BarWindow
# The main visible widget: a 27-pixel-tall frameless, always-on-top window that fills
# from left to right as Claude token usage increases. Emits reconfigure_requested when
# the user chooses "Reconfigure" from the right-click menu.
class BarWindow(QWidget):
    reconfigure_requested = pyqtSignal()

    # __init__
    # Sets up the internal state variables, applies the window style, positions the
    # bar on screen, and starts the one-second repaint timer that keeps the countdown
    # text ticking without hitting the network.
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

    # _setup_window
    # Removes the normal title bar and border, forces the window to stay on top of all
    # other applications, hides it from the taskbar, and sets the fixed pixel size.
    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool          # keeps bar off the taskbar
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        w = self._cfg.get("window", {}).get("width", 450)
        self.setFixedSize(w, 27)

    # _place_window
    # Moves the bar to the saved x/y position from the config. If no x position has
    # been saved yet the bar is placed 10 pixels from the right edge of the main screen.
    def _place_window(self) -> None:
        win = self._cfg.get("window", {})
        x = win.get("x")
        y = win.get("y", 10)
        if x is None:
            screen = QApplication.primaryScreen().geometry()
            x = screen.width() - self.width() - 10
        self.move(x, y)

    # _color
    # Looks up a named colour (e.g. "fill", "background", "text") from the config's
    # colors section and returns it as a QColor. Falls back to the given hex string if
    # the key is not present in the config.
    def _color(self, key: str, fallback: str) -> QColor:
        return QColor(self._cfg.get("colors", {}).get(key, fallback))

    # set_data
    # Receives fresh usage data from the main thread signal and stores it for the next
    # paint. A pct value below zero means "keep the last known fill level" — used when
    # a network error occurs and we don't want to reset the bar to empty.
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

    # paintEvent
    # Draws the entire bar from scratch every time Qt asks for a repaint. Paints the
    # dark background, then the coloured fill rectangle, then overlays the text on the
    # right (countdown or error) and the percentage on the left.
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

    # mousePressEvent
    # Records the offset between the mouse cursor and the window's top-left corner when
    # the user first clicks on the bar, so subsequent mouse-move events can reposition
    # the window correctly relative to where it was grabbed.
    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = (
                e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    # mouseMoveEvent
    # Moves the bar window to follow the mouse cursor while the left button is held
    # down, subtracting the original grab offset so the bar doesn't jump.
    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        if self._drag_origin and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_origin)

    # mouseReleaseEvent
    # Clears the drag state when the mouse button is released, then saves the new
    # window position to the config file so it is restored the next time the app starts.
    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            pos = self.pos()
            self._cfg.setdefault("window", {})
            self._cfg["window"]["x"] = pos.x()
            self._cfg["window"]["y"] = pos.y()
            cfg_mod.save(self._cfg)

    # --- Right-click context menu ---

    # contextMenuEvent
    # Shows a small pop-up menu when the user right-clicks the bar, offering options
    # to open the setup wizard again or to quit the application entirely.
    def contextMenuEvent(self, e) -> None:  # noqa: N802
        menu = QMenu(self)
        menu.addAction("Reconfigure…", self.reconfigure_requested.emit)
        menu.addSeparator()
        menu.addAction("Exit", QApplication.quit)
        menu.exec(e.globalPos())
