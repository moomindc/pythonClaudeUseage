# notifier.py
# Fires Windows toast notifications when Claude usage crosses configured thresholds
# or when a session window resets. Uses a hidden QSystemTrayIcon so no new packages
# are required — Qt maps showMessage() to native Windows Action Center toasts on Win10/11.

import logging
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from PIL import Image
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QSystemTrayIcon

log = logging.getLogger(__name__)


def _transparent_icon() -> QIcon:
    buf = BytesIO()
    Image.new("RGBA", (16, 16), (0, 0, 0, 0)).save(buf, "PNG")
    px = QPixmap()
    px.loadFromData(buf.getvalue())
    return QIcon(px)


class Notifier:
    # __init__
    # Creates a hidden (transparent) system tray icon solely to have a valid handle for
    # showMessage(). The icon occupies no visible space in the tray area.
    def __init__(self, cfg: dict) -> None:
        self._cfg = cfg
        self._fired: set[int] = set()
        self._prev_pct: float = -1.0          # -1 = no data received yet
        self._tray = QSystemTrayIcon(_transparent_icon())
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.show()

    # check
    # Called on the main thread after every successful usage fetch. Fires a notification
    # the first time each threshold is crossed upward and detects session resets.
    def check(self, pct: float, reset_at: Optional[datetime]) -> None:
        if not self._cfg.get("notifications", {}).get("enabled", True):
            return
        if pct < 0:
            return

        thresholds: list[int] = self._cfg.get("notifications", {}).get("thresholds", [80, 90])
        first_data = self._prev_pct < 0

        if first_data:
            # Silently mark already-crossed thresholds so startup doesn't spam.
            for t in thresholds:
                if pct >= t:
                    self._fired.add(t)
        else:
            for t in sorted(thresholds):
                if pct >= t and self._prev_pct < t and t not in self._fired:
                    self._fired.add(t)
                    msg = f"At {pct:.0f}%"
                    if reset_at is not None:
                        msg += f" — resets in {_fmt_remaining(reset_at)}"
                    self._toast(f"Claude usage: {t}%+", msg)

            # Reset detection: pct dropped sharply, meaning the window rolled over.
            if self._prev_pct >= 50 and pct < 20:
                self._fired.clear()
                self._toast("Claude session reset", "New 5-hour window has started")

        self._prev_pct = pct

    def _toast(self, title: str, message: str) -> None:
        log.info("Notification: %s — %s", title, message)
        self._tray.showMessage(
            title, message, QSystemTrayIcon.MessageIcon.Information, 8000
        )


def _fmt_remaining(reset_at: datetime) -> str:
    remaining = (reset_at - datetime.now(timezone.utc)).total_seconds()
    if remaining <= 0:
        return "soon"
    hh = int(remaining) // 3600
    mm = (int(remaining) % 3600) // 60
    return f"{hh}h {mm:02d}m"
