# main.py
# Entry point and application wiring layer. Creates the Qt application, ties together
# the bar window, system tray, config, and background fetch thread, then starts the
# Qt event loop that keeps the app running until the user exits.

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


# _setup_logging
# Creates the log directory if it does not exist, then configures the Python logging
# system to write timestamped INFO-level messages to both a log file and the console.
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


# _Bridge
# A thread-safe signal carrier. Background worker threads call data_ready.emit() to
# pass new usage data to the Qt main thread. Qt automatically queues the delivery so
# the main thread processes it safely — no locks needed.
class _Bridge(QObject):
    data_ready = pyqtSignal(float, object, object)  # pct, reset_at, error_text


# App
# The central wiring class that owns every major component of the application: the
# Qt event loop, config, polling timer, bar window, tray icon, and the bridge between
# the background fetch thread and the UI.
class App:
    # __init__
    # Initialises the Qt application object and sets up empty slots for each component.
    # Nothing is shown to the user yet — that happens in run().
    def __init__(self) -> None:
        self._qt = QApplication(sys.argv)
        self._qt.setQuitOnLastWindowClosed(False)
        self._cfg = cfg_mod.load()
        self._bridge = _Bridge()
        self._bar: Optional[BarWindow] = None
        self._tray: Optional[TrayIcon] = None
        self._timer: Optional[QTimer] = None
        self._alive = True

    # run
    # The main startup sequence. Shows the setup wizard if credentials are missing,
    # then creates the bar and tray, connects the data signal, starts the polling timer,
    # and hands control to the Qt event loop (which blocks until the user quits).
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

    # _show_wizard
    # Opens the setup wizard as a modal dialog and returns True if the user completed
    # it successfully, or False if they closed it without finishing.
    def _show_wizard(self) -> bool:
        dlg = WizardDialog(self._cfg)
        return dlg.exec() == _ACCEPTED

    # _start_bar
    # Creates the floating bar window, connects its reconfigure signal so right-clicking
    # the bar can open the wizard, then makes the window visible.
    def _start_bar(self) -> None:
        self._bar = BarWindow(self._cfg)
        self._bar.reconfigure_requested.connect(self._on_reconfigure)
        self._bar.show()

    # _start_tray
    # Creates the system tray icon, connects each tray menu action (toggle, reconfigure,
    # exit) to the appropriate handler, then starts the tray's background thread.
    def _start_tray(self) -> None:
        self._tray = TrayIcon()
        self._tray.signals.toggle.connect(self._on_toggle)
        self._tray.signals.reconfigure.connect(self._on_reconfigure)
        self._tray.signals.exit.connect(self._on_exit)
        self._tray.start()

    # _start_polling
    # Reads the configured polling interval (default 5 minutes), creates or resets the
    # QTimer that triggers fetch jobs, and fires an immediate first fetch so data
    # appears right away rather than waiting for the first interval to elapse.
    def _start_polling(self) -> None:
        interval_ms = int(self._cfg.get("poll_interval_minutes", 5) * 60_000)
        if self._timer:
            self._timer.stop()
        self._timer = QTimer()
        self._timer.timeout.connect(self._spawn_fetch)
        self._timer.start(interval_ms)
        self._spawn_fetch()   # immediate first fetch

    # _spawn_fetch
    # Launches _fetch in a new daemon thread so the network call never freezes the
    # Qt main thread or the UI. Daemon threads are automatically killed when the app exits.
    def _spawn_fetch(self) -> None:
        threading.Thread(target=self._fetch, daemon=True).start()

    # _fetch
    # Runs in a background thread. Reads the saved credentials and calls the claude.ai
    # API for the latest usage data. On success it emits the percentage and reset time
    # via the bridge. On auth failure it emits an error message. On any other network
    # error it emits pct=-1 so the bar retains its last known fill level.
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

    # _on_data
    # Receives fresh usage data from the _Bridge signal and forwards it to the bar
    # window so it can repaint with the updated percentage and countdown.
    def _on_data(self, pct: float, reset_at, error_text) -> None:
        if self._bar:
            self._bar.set_data(pct, reset_at, error_text)

    # _on_toggle
    # Shows or hides the floating bar window in response to the "Show bar" / "Hide bar"
    # menu item in the system tray.
    def _on_toggle(self, visible: bool) -> None:
        if self._bar:
            self._bar.setVisible(visible)

    # _on_reconfigure
    # Opens the setup wizard so the user can update their session key. If they complete
    # it successfully the config is reloaded and the polling timer is restarted so the
    # new credentials take effect immediately.
    def _on_reconfigure(self) -> None:
        dlg = WizardDialog(self._cfg)
        if dlg.exec() == _ACCEPTED:
            self._cfg = cfg_mod.load()
            if self._bar:
                self._bar._cfg = self._cfg
            self._start_polling()

    # _on_exit
    # Handles the Exit action from the tray or context menu. Sets the alive flag to
    # False so any in-flight fetch thread exits cleanly, stops the tray icon, and
    # asks Qt to shut down the event loop.
    def _on_exit(self) -> None:
        log.info("Exiting")
        self._alive = False
        if self._tray:
            self._tray.stop()
        self._qt.quit()


if __name__ == "__main__":
    _setup_logging()
    App().run()
