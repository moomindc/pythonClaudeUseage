import logging
import sys
import threading
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog

import config as cfg_mod
import claude_client
from bar_window import BarWindow
from tray import TrayIcon
from wizard import WizardDialog

_ACCEPTED = QDialog.DialogCode.Accepted


def _setup_logging() -> None:
    cfg_mod.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = cfg_mod.CONFIG_DIR / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


log = logging.getLogger(__name__)


class _Bridge(QObject):
    """Thread-safe channel: worker threads emit here, main Qt thread receives."""
    data_ready = pyqtSignal(float, object, object)  # pct, reset_at, error_text


class App:
    def __init__(self) -> None:
        self._qt = QApplication(sys.argv)
        self._qt.setQuitOnLastWindowClosed(False)
        self._cfg = cfg_mod.load()
        self._bridge = _Bridge()
        self._bar: Optional[BarWindow] = None
        self._tray: Optional[TrayIcon] = None
        self._timer: Optional[QTimer] = None
        self._alive = True

    def run(self) -> None:
        if not cfg_mod.is_configured(self._cfg):
            if not self._show_wizard():
                sys.exit(0)
            self._cfg = cfg_mod.load()

        self._start_bar()
        self._start_tray()
        self._bridge.data_ready.connect(self._on_data)
        self._start_polling()

        log.info("Claude Usage Bar started")
        sys.exit(self._qt.exec())

    # ------------------------------------------------------------------ #

    def _show_wizard(self) -> bool:
        dlg = WizardDialog(self._cfg)
        return dlg.exec() == _ACCEPTED

    def _start_bar(self) -> None:
        self._bar = BarWindow(self._cfg)
        self._bar.reconfigure_requested.connect(self._on_reconfigure)
        self._bar.show()

    def _start_tray(self) -> None:
        self._tray = TrayIcon()
        self._tray.signals.toggle.connect(self._on_toggle)
        self._tray.signals.reconfigure.connect(self._on_reconfigure)
        self._tray.signals.exit.connect(self._on_exit)
        self._tray.start()

    def _start_polling(self) -> None:
        interval_ms = int(self._cfg.get("poll_interval_minutes", 5) * 60_000)
        if self._timer:
            self._timer.stop()
        self._timer = QTimer()
        self._timer.timeout.connect(self._spawn_fetch)
        self._timer.start(interval_ms)
        self._spawn_fetch()   # immediate first fetch

    def _spawn_fetch(self) -> None:
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self) -> None:
        if not self._alive:
            return
        key = self._cfg.get("session_key", "")
        org = self._cfg.get("org_id", "")
        try:
            raw = claude_client.get_usage(key, org)
            pct, reset_at = claude_client.parse_usage(raw)
            log.info("Usage: %.1f%% (reset_at=%s)", pct, reset_at)
            self._bridge.data_ready.emit(pct, reset_at, None)
            if self._tray:
                self._tray.set_tooltip(f"Claude: {pct:.0f}% used")
        except claude_client.AuthError as exc:
            log.warning("Auth error: %s", exc)
            self._bridge.data_ready.emit(0.0, None, "Auth error · right-click to fix")
        except Exception as exc:
            log.warning("Fetch error: %s", exc)
            # pct=-1 tells set_data to keep last known fill level
            self._bridge.data_ready.emit(-1.0, None, "Offline")

    # ------------------------------------------------------------------ #
    # Slot handlers — all run in the Qt main thread
    # ------------------------------------------------------------------ #

    def _on_data(self, pct: float, reset_at, error_text) -> None:
        if self._bar:
            self._bar.set_data(pct, reset_at, error_text)

    def _on_toggle(self, visible: bool) -> None:
        if self._bar:
            self._bar.setVisible(visible)

    def _on_reconfigure(self) -> None:
        dlg = WizardDialog(self._cfg)
        if dlg.exec() == _ACCEPTED:
            self._cfg = cfg_mod.load()
            if self._bar:
                self._bar._cfg = self._cfg
            self._start_polling()

    def _on_exit(self) -> None:
        log.info("Exiting")
        self._alive = False
        if self._tray:
            self._tray.stop()
        self._qt.quit()


if __name__ == "__main__":
    _setup_logging()
    App().run()
