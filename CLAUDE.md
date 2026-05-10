# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```powershell
cd ClaudeUsageBar
py main.py
```

Install dependencies first (one-time, requires Python 3.11+):
```powershell
py -m pip install -r ClaudeUsageBar/requirements.txt
```

There are no tests or linting configured. The app runs directly — manual testing against the live `claude.ai` API is the verification path (see PRD checklist in `claude-usage-bar-prd.md`).

## Architecture

The app is a Windows-only floating progress bar showing Claude.ai 5-hour session usage. It has no build step — run `main.py` directly.

**Component roles:**

- `main.py` — `App` class is the wiring layer. Owns the `QApplication`, config, polling timer, and all inter-component connections. `_Bridge(QObject)` is the thread-safe channel between the background fetch thread and the Qt main thread (via `pyqtSignal`).
- `bar_window.py` — `BarWindow(QWidget)` is a 27px-tall frameless always-on-top window. Renders entirely in `paintEvent` (no child widgets). A 1-second `QTimer` drives the countdown tick without network calls. Drag-to-reposition writes updated `x`/`y` to config on mouse release.
- `wizard.py` — `WizardDialog(QDialog)` with `QStackedWidget` (3 pages). Called both on first run and from Reconfigure. Writes `session_key` and `org_id` to config on successful connection test.
- `tray.py` — `TrayIcon` wraps `pystray` (runs in its own thread). A `_Signals(QObject)` bridge passes tray events back to the Qt thread safely.
- `claude_client.py` — Stateless HTTP functions. `get_organizations()` discovers the org UUID. `get_usage()` fetches `five_hour.utilization_pct` and `five_hour.reset_at`. Raises `AuthError` on 401/403.
- `config.py` — Reads/writes `%APPDATA%\ClaudeUsageBar\config.json`. `load()` deep-merges with defaults so missing keys never cause KeyErrors.

**Thread safety pattern:** Background threads never touch Qt widgets. They call `_Bridge.data_ready.emit(...)`, which Qt automatically queues to the main thread.

**Error signalling:** `_fetch()` in `main.py` emits `pct=-1` for network errors (bar retains last fill) and `pct=0` with error text for auth errors.

## Key Files

| File | Purpose |
|------|---------|
| `ClaudeUsageBar/main.py` | Entry point, `App` class, `_Bridge` signal |
| `ClaudeUsageBar/bar_window.py` | Floating bar UI and drag logic |
| `ClaudeUsageBar/claude_client.py` | `claude.ai` API calls and `AuthError` |
| `ClaudeUsageBar/config.py` | Config file path (`%APPDATA%\ClaudeUsageBar\`) |
| `claude-usage-bar-prd.md` | Full PRD including API endpoint details and visual spec |

## API Details

The app uses `claude.ai` internal endpoints (not the Anthropic API):
- `GET https://claude.ai/api/organizations` — discover `org_id`
- `GET https://claude.ai/api/organizations/{org_id}/usage` — fetch `five_hour.utilization` (0–100 float) and `five_hour.resets_at` (ISO 8601)

Authentication is via the `sessionKey` browser cookie (`sk-ant-sid01-…`). No CSRF token needed.

## Config File

`%APPDATA%\ClaudeUsageBar\config.json` — created by the wizard, updated on drag. Edit manually to change `poll_interval_minutes` (default: 5) or `window.width` (default: 153).

Logs at `%APPDATA%\ClaudeUsageBar\app.log`.
