import threading

import pystray
from PIL import Image, ImageDraw
from PyQt6.QtCore import QObject, pyqtSignal


def _build_icon() -> Image.Image:
    """Generate a simple 64×64 tray icon with a navy circle and white 'C' arc."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, size - 2, size - 2], fill=(0, 31, 91, 255))
    d.arc([12, 12, size - 12, size - 12], start=50, end=310,
          fill=(255, 255, 255, 255), width=6)
    return img


class _Signals(QObject):
    """Lives in the main Qt thread; emission from pystray threads is queue-safe."""
    toggle = pyqtSignal(bool)        # True = show, False = hide
    reconfigure = pyqtSignal()
    exit = pyqtSignal()


class TrayIcon:
    def __init__(self) -> None:
        self.signals = _Signals()
        self._icon: pystray.Icon | None = None
        self._visible = True

    @property
    def visible(self) -> bool:
        return self._visible

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

    def set_tooltip(self, text: str) -> None:
        if self._icon:
            self._icon.title = text

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
