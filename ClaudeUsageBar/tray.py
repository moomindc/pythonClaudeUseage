# tray.py
# Creates and manages the Windows system tray icon that lets the user show/hide the
# bar, open the setup wizard, or exit the app — all from a right-click context menu
# in the notification area.

import threading

import pystray
from PIL import Image, ImageDraw
from PyQt6.QtCore import QObject, pyqtSignal


# _build_icon
# Draws a 64×64 pixel icon in memory using Pillow: a dark-navy filled circle with a
# white arc that suggests the letter "C". This image is shown in the Windows system tray.
def _build_icon() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, size - 2, size - 2], fill=(0, 31, 91, 255))
    d.arc([12, 12, size - 12, size - 12], start=50, end=310,
          fill=(255, 255, 255, 255), width=6)
    return img


# _Signals
# A Qt signals container that lives in the main Qt thread. Tray menu callbacks run in
# pystray's own thread, so they emit these signals instead of touching Qt widgets
# directly — Qt automatically delivers the signals safely to the main thread.
class _Signals(QObject):
    toggle = pyqtSignal(bool)        # True = show, False = hide
    reconfigure = pyqtSignal()
    exit = pyqtSignal()


# TrayIcon
# Wraps the pystray icon and exposes a signals attribute that the rest of the app
# connects to. pystray runs its event loop in its own daemon thread so it does not
# block the Qt main thread.
class TrayIcon:
    # __init__
    # Creates the signals bridge and prepares internal state. The icon is not shown
    # until start() is called.
    def __init__(self) -> None:
        self.signals = _Signals()
        self._icon: pystray.Icon | None = None
        self._visible = True

    # visible (property)
    # Read-only property that reports whether the bar window is currently set to be
    # shown, so the tray menu label ("Show bar" / "Hide bar") stays accurate.
    @property
    def visible(self) -> bool:
        return self._visible

    # start
    # Builds the tray menu with toggle, reconfigure, and exit items, creates the
    # pystray Icon object, and launches it in a background daemon thread so the app
    # does not block waiting for tray events.
    def start(self) -> None:
        def _toggle(icon, item):
            self._visible = not self._visible
            self.signals.toggle.emit(self._visible)

        def _reconfig(icon, item):
            self.signals.reconfigure.emit()

        def _exit(icon, item):
            self.signals.exit.emit()

        menu = pystray.Menu(
            pystray.MenuItem(
                lambda _: "Hide bar" if self._visible else "Show bar",
                _toggle,
                default=True,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Reconfigure…", _reconfig),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", _exit),
        )
        self._icon = pystray.Icon(
            "ClaudeUsageBar", _build_icon(), "Claude Usage Bar", menu
        )
        threading.Thread(target=self._icon.run, daemon=True).start()

    # set_tooltip
    # Updates the tooltip text shown when the user hovers over the tray icon.
    # Typically called after each successful usage fetch to display the current
    # percentage, e.g. "Claude: 42% used".
    def set_tooltip(self, text: str) -> None:
        if self._icon:
            self._icon.title = text

    # stop
    # Cleanly shuts down the pystray icon and removes it from the system tray.
    # Called when the user chooses Exit so the icon does not linger after the app ends.
    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
