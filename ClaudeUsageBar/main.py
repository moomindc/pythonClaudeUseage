# main.py
# Entry point and application wiring layer. Creates the Qt application, ties together
# the bar window, system tray, config, and background fetch thread, then starts the
# Qt event loop that keeps the app running until the user exits.

import ctypes
import ctypes.wintypes
import logging
import sys
import threading
from datetime import date, datetime, timedelta
from typing import Optional

from PyQt6.QtCore import QAbstractNativeEventFilter, QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog

import config as cfg_mod
import claude_client
from bar_window import BarWindow
from notifier import Notifier
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


# _PowerEventFilter
# Listens for Windows WM_POWERBROADCAST messages on the Qt message pump. When the OS
# signals PBT_APMRESUMEAUTOMATIC (automatic resume from sleep/hibernate), it calls the
# supplied callback on the main thread so the bar can be re-shown without locks.
class _PowerEventFilter(QAbstractNativeEventFilter):
    _WM_POWERBROADCAST = 0x0218
    _PBT_APMRESUMEAUTOMATIC = 0x0012

    def __init__(self, callback) -> None:
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type, message):  # noqa: N802
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == self._WM_POWERBROADCAST and msg.wParam == self._PBT_APMRESUMEAUTOMATIC:
                self._callback()
        return False, 0


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
        self._sched_timer: Optional[QTimer] = None
        self._triggered_today: dict[int, date] = {}
        self._alive = True
        self._current_interval_ms: int = 0
        self._power_filter: Optional[_PowerEventFilter] = None
        self._notifier: Optional[Notifier] = None

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
        self._notifier = Notifier(self._cfg)
        self._bridge.data_ready.connect(self._on_data)
        self._start_polling()
        self._start_session_scheduler()
        self._update_tray_triple()
        self._install_power_filter()

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
        self._bar.settings_requested.connect(self._on_settings)
        self._bar.show()
        self._bar.apply_config()

    # _start_tray
    # Creates the system tray icon, connects each tray menu action (toggle, reconfigure,
    # exit) to the appropriate handler, then starts the tray's background thread.
    def _start_tray(self) -> None:
        self._tray = TrayIcon()
        self._tray.signals.toggle.connect(self._on_toggle)
        self._tray.signals.reconfigure.connect(self._on_reconfigure)
        self._tray.signals.exit.connect(self._on_exit)
        self._tray.signals.toggle_triple.connect(self._on_toggle_triple)
        self._tray.signals.settings.connect(self._on_settings)
        self._tray.start()

    # _start_polling
    # Reads the configured polling interval (default 5 minutes), creates or resets the
    # QTimer that triggers fetch jobs, and fires an immediate first fetch so data
    # appears right away rather than waiting for the first interval to elapse.
    def _start_polling(self) -> None:
        interval_ms = self._base_interval_ms()
        if self._timer:
            self._timer.stop()
        self._timer = QTimer()
        self._timer.timeout.connect(self._spawn_fetch)
        self._timer.start(interval_ms)
        self._current_interval_ms = interval_ms
        self._spawn_fetch()   # immediate first fetch

    # _base_interval_ms
    # Returns the configured polling interval in milliseconds.
    def _base_interval_ms(self) -> int:
        return int(self._cfg.get("poll_interval_minutes", 5) * 60_000)

    # _desired_interval_ms
    # Returns the adaptive polling interval for a given usage percentage:
    # 90%+  → every 90 seconds; 80–90% → half the base interval; below 80% → base interval.
    def _desired_interval_ms(self, pct: float) -> int:
        base = self._base_interval_ms()
        if pct >= 90.0:
            return 90_000
        if pct >= 80.0:
            return max(base // 2, 90_000)
        return base

    # _maybe_adjust_poll
    # Called after each data update. If the desired polling interval differs from the
    # current one, restarts the timer with the new interval.
    def _maybe_adjust_poll(self, pct: float) -> None:
        if pct < 0:
            return
        desired = self._desired_interval_ms(pct)
        if desired != self._current_interval_ms and self._timer:
            self._timer.stop()
            self._timer.start(desired)
            self._current_interval_ms = desired
            log.info("Poll interval adjusted to %ds (pct=%.1f%%)", desired // 1000, pct)

    # _start_session_scheduler
    # Creates (or resets) the 60-second QTimer that checks whether a triple-session
    # trigger is due. Fires an immediate check on start so the app catches a trigger
    # that falls within 2 minutes of startup.
    def _start_session_scheduler(self) -> None:
        if self._sched_timer:
            self._sched_timer.stop()
        self._sched_timer = QTimer()
        self._sched_timer.timeout.connect(self._check_session_schedule)
        self._sched_timer.start(60_000)
        self._check_session_schedule()

    # _session_times
    # Returns the four daily trigger datetimes derived from the configured work_start
    # time (spaced 5 hours apart). Returns an empty list when triple session is off.
    def _session_times(self) -> list:
        ts_cfg = self._cfg.get("triple_session", {})
        if not ts_cfg.get("enabled", False):
            return []
        h, m = map(int, ts_cfg.get("work_start", "07:00").split(":"))
        today = datetime.now().date()
        base = datetime(today.year, today.month, today.day, h, m)
        return [base + timedelta(hours=5 * i) for i in range(4)]

    # _check_session_schedule
    # Called every 60 seconds. For each scheduled session time that has not yet been
    # triggered today, fires a background trigger if now is within the 2-minute window.
    def _check_session_schedule(self) -> None:
        now = datetime.now()
        today = now.date()
        for i, t in enumerate(self._session_times()):
            if self._triggered_today.get(i) == today:
                continue
            diff = (now - t).total_seconds()
            if 0 <= diff < 120:
                self._triggered_today[i] = today
                log.info("Triggering triple session %d", i + 1)
                threading.Thread(target=self._do_trigger, daemon=True).start()

    # _do_trigger
    # Background thread: sends the configured prompt to claude.ai to activate the
    # next 5-hour session window. The conversation is deleted automatically after sending
    # so it never appears in chat history.
    def _do_trigger(self) -> None:
        key = self._cfg.get("session_key", "")
        org = self._cfg.get("org_id", "")
        prompt = self._cfg.get("triple_session", {}).get("prompt", "Hi")
        try:
            claude_client.send_session_trigger(key, org, prompt)
            log.info("Triple session trigger sent successfully")
        except Exception as exc:
            log.warning("Triple session trigger failed: %s", exc)

    # _triple_times_str
    # Formats the day's session trigger times as a readable string for the tray menu,
    # e.g. "7:00 AM · 12:00 PM · 5:00 PM · 10:00 PM".
    def _triple_times_str(self) -> str:
        times = self._session_times()
        if not times:
            ts_cfg = self._cfg.get("triple_session", {})
            h, m = map(int, ts_cfg.get("work_start", "07:00").split(":"))
            today = datetime.now().date()
            base = datetime(today.year, today.month, today.day, h, m)
            times = [base + timedelta(hours=5 * i) for i in range(4)]

        def _fmt(t: datetime) -> str:
            hour = t.hour % 12 or 12
            ampm = "AM" if t.hour < 12 else "PM"
            return f"{hour}:{t.minute:02d} {ampm}"

        return " · ".join(_fmt(t) for t in times)

    # _update_tray_triple
    # Pushes the current triple-session state and session-times string to the tray so
    # the menu label and info item stay in sync after config changes.
    def _update_tray_triple(self) -> None:
        if self._tray:
            enabled = self._cfg.get("triple_session", {}).get("enabled", False)
            self._tray.set_triple_session(enabled, self._triple_times_str())

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
        if self._notifier:
            self._notifier.check(pct, reset_at)
        self._maybe_adjust_poll(pct)

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
            if self._notifier:
                self._notifier._cfg = self._cfg
            self._start_polling()
            self._start_session_scheduler()
            self._update_tray_triple()

    # _on_settings
    # Opens the settings dialog. On save, reloads config from disk, resizes and
    # repositions the bar, and restarts the polling and session-schedule timers.
    def _on_settings(self) -> None:
        from settings_dialog import SettingsDialog
        dlg = SettingsDialog(self._cfg)
        if dlg.exec() == _ACCEPTED:
            self._cfg = cfg_mod.load()
            if self._bar:
                self._bar._cfg = self._cfg
                w = self._cfg.get("window", {}).get("width", 123)
                self._bar.setFixedSize(w, 27)
                self._bar.apply_config()
                self._bar.update()
            if self._notifier:
                self._notifier._cfg = self._cfg
            self._start_polling()
            self._start_session_scheduler()
            self._update_tray_triple()

    # _on_toggle_triple
    # Flips the triple_session.enabled flag in config, saves it, and restarts the
    # scheduler so the change takes effect immediately.
    def _on_toggle_triple(self) -> None:
        ts = self._cfg.setdefault("triple_session", {})
        ts["enabled"] = not ts.get("enabled", False)
        cfg_mod.save(self._cfg)
        self._start_session_scheduler()
        self._update_tray_triple()
        log.info("Triple session %s", "enabled" if ts["enabled"] else "disabled")

    # _install_power_filter
    # Registers the native Windows power-event filter with the Qt application so that
    # sleep/resume cycles can be detected and the bar re-shown automatically.
    def _install_power_filter(self) -> None:
        self._power_filter = _PowerEventFilter(self._on_resume)
        self._qt.installNativeEventFilter(self._power_filter)

    # _on_resume
    # Called on the main thread when Windows signals a resume from sleep or hibernate.
    # Re-shows the bar (Windows can suppress it during session transitions), re-checks
    # its position in case display geometry changed, and triggers an immediate fetch.
    def _on_resume(self) -> None:
        log.info("System resumed from sleep — re-showing bar")
        if self._bar:
            self._bar.show()
            self._bar.raise_()
            self._bar._place_window()
        self._spawn_fetch()

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
