# Claude Usage Bar — Product Requirements Document

## Overview

A lightweight Windows desktop utility that displays a compact, floating, always-on-top progress
bar showing the current Claude.ai subscription usage and time until the next reset.
The window is frameless and draggable — visible at a glance without obstructing the user's workflow.

## Goals

- Provide at-a-glance awareness of Claude.ai session consumption without switching to a browser
- Stay out of the way: compact, unobtrusive, and dismissable to the system tray
- Simple one-time setup requiring only a session cookie paste — no developer knowledge needed

## Non-Goals (v1)

- Tracking Anthropic API key usage
- Browser extension
- Mobile or cross-platform support (Windows only for v1)
- Toast / threshold notifications (deferred to v2)
- Auto-start with Windows (deferred to v2)

---

## Technical Stack

| Component       | Choice                                                         |
|-----------------|----------------------------------------------------------------|
| Language        | Python 3.11+ (tested on 3.14.2)                               |
| GUI framework   | PyQt6 — frameless window, custom `paintEvent`, drag           |
| HTTP client     | `requests`                                                     |
| System tray     | `pystray` + `Pillow` (icon generated programmatically)        |
| Config storage  | JSON at `%APPDATA%\ClaudeUsageBar\config.json`                 |
| Logging         | stdlib `logging` → `%APPDATA%\ClaudeUsageBar\app.log`         |
| Packaging       | PyInstaller — single `.exe` (future; not yet implemented)      |

**Why PyQt6 over tkinter:** Custom-coloured frameless windows with smooth progress bars require
painting on a canvas. PyQt6's `QWidget` + `paintEvent` gives pixel-level control; tkinter's
`Canvas` can achieve this but with more friction and poorer HiDPI support on Windows.

**Thread safety:** Network polling runs in Python `threading.Thread`. A `_Bridge(QObject)` with
a `pyqtSignal` is used to pass results back to the Qt main thread safely — PyQt6 automatically
queues cross-thread signal emissions.

---

## Window Specification

| Property      | Value                                                |
|---------------|------------------------------------------------------|
| Width         | 450 px (user-configurable via `config.json`)         |
| Height        | 22 px (fixed)                                        |
| Decorations   | None — `Qt.FramelessWindowHint`                      |
| Z-order       | Always on top — `Qt.WindowStaysOnTopHint`            |
| Taskbar       | Hidden — `Qt.Tool` window type                       |
| Default pos   | Top-right corner of primary monitor                  |
| Drag          | Left-click-drag anywhere on the bar to reposition    |
| Position save | Written to `config.json` on mouse release            |

---

## Visual Design

```
┌──────────────────────────────────────────────┐
│████████████████████░░░░░░░  resets in 3h 22m │
└──────────────────────────────────────────────┘
```

| Element         | Colour    | Notes                                              |
|-----------------|-----------|----------------------------------------------------|
| Used portion    | `#001F5B` | Dark navy blue                                     |
| Unused portion  | `#050A14` | Near-black dark blue                               |
| Text (normal)   | `#FFFFFF` | Segoe UI 8pt, right-aligned, vertically centred    |
| Text (error)    | `#888888` | Grey — shown for Offline / Auth error states       |

Text content states:

| State             | Text shown                          |
|-------------------|-------------------------------------|
| Normal            | `resets in Xh XXm`                  |
| No session window | `—`                                 |
| Auth error        | `Auth error · right-click to fix`   |
| Network error     | `Offline` (last known fill retained)|
| Resetting now     | `resetting…`                        |

The countdown ticks every second from the cached `reset_at` timestamp — no extra network
call is needed between polls.

---

## Data Source

Claude.ai does not expose an official public API for subscription usage. The app uses internal
`claude.ai` endpoints, authenticated via the user's browser session cookie.

### Confirmed API Endpoints

These endpoints were identified by examining open-source Claude trackers and network traffic:

**1. Discover organisation ID**
```
GET https://claude.ai/api/organizations
Cookie: sessionKey=sk-ant-sid01-…
```
Returns a JSON array. Each element contains a `uuid` field which is the organisation ID.

**2. Fetch usage**
```
GET https://claude.ai/api/organizations/{org_id}/usage
Cookie: sessionKey=sk-ant-sid01-…
```
Returns a JSON object. The relevant portion:
```json
{
  "five_hour": {
    "utilization_pct": 74.5,
    "reset_at": "2026-05-09T18:30:00Z"
  },
  "seven_day": { "utilization_pct": 23.1 },
  "seven_day_opus": { "utilization_pct": 5.2 }
}
```
The app displays `five_hour.utilization_pct` as the bar fill and computes the countdown
from `five_hour.reset_at`.

### Authentication

- The `sessionKey` cookie starts with `sk-ant-sid01-`
- No CSRF token or additional headers are required beyond a realistic `User-Agent`
- The `org_id` is discovered automatically during the first test connection in the wizard;
  the user never needs to find or enter it manually

### Polling

| Parameter       | Default | Configurable          |
|-----------------|---------|-----------------------|
| Poll interval   | 5 min   | Yes — `poll_interval_minutes` in config |
| On app launch   | Immediate fetch, then on interval      |
| On auth failure | Show error text; keep polling (re-tries each interval) |
| On network error| Retain last known fill; show "Offline" |

---

## Configuration File

Location: `%APPDATA%\ClaudeUsageBar\config.json`

```json
{
  "session_key": "sk-ant-sid01-…",
  "org_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "poll_interval_minutes": 5,
  "window": {
    "x": 1200,
    "y": 10,
    "width": 450
  }
}
```

The directory is created automatically. The file is written by the wizard on successful
connection and updated on every drag-to-reposition.

---

## Setup Wizard

Triggered automatically when no valid config exists, or manually via right-click → Reconfigure.
Implemented as a fixed-width (500 px) `QDialog` modal, separate from the floating bar.

### Pages

1. **Welcome** — brief description; "Get Started" button
2. **Session Key** — numbered instructions for extracting `sessionKey` from browser DevTools;
   paste field (password echo); "Test & Connect" button calls both API endpoints and shows
   success/failure inline; on success, saves `session_key` and `org_id` to config
3. **Done** — confirmation message; "Start Monitoring" button accepts the dialog

---

## System Tray

The app runs in the system tray. The floating bar can be hidden without exiting.

| Action              | Behaviour                                   |
|---------------------|---------------------------------------------|
| Left-click tray icon | Toggle bar visibility                      |
| Right-click tray icon | Context menu                              |
| Right-click bar      | Context menu                              |

### Tray Context Menu

```
Hide bar   (or "Show bar" when hidden)
──────────────────────────────────────
Reconfigure…
──────────────────────────────────────
Exit
```

### Bar Context Menu

```
Reconfigure…
──────────────
Exit
```

---

## Error States

| Condition                 | Bar text                          | Log level |
|---------------------------|-----------------------------------|-----------|
| No config / first run     | Wizard opens automatically        | INFO      |
| Invalid / expired cookie  | `Auth error · right-click to fix` | WARNING   |
| Network / connection error | `Offline` (fill retained)        | WARNING   |
| Unexpected API response   | `Offline` (fill retained)         | WARNING   |

All errors are logged to `%APPDATA%\ClaudeUsageBar\app.log`.

---

## Project Structure

```
ClaudeUsageBar/
├── main.py           Entry point; App class; _Bridge QObject for thread-safe UI updates
├── bar_window.py     Frameless PyQt6 QWidget; custom paintEvent; drag; context menu
├── wizard.py         QDialog with QStackedWidget (3 pages)
├── tray.py           pystray Icon; _Signals QObject for thread-safe callbacks to Qt
├── claude_client.py  get_organizations(), get_usage(), parse_usage(); AuthError exception
├── config.py         load(), save(), is_configured(); defaults; %APPDATA% path
└── requirements.txt  PyQt6, requests, pystray, Pillow
```

The tray icon is generated at runtime using Pillow — no image assets are needed.

---

## Resolved Development Questions

The following were open questions in v1.0 of this document; all have been resolved:

1. **API endpoints confirmed** — `GET /api/organizations` then `GET /api/organizations/{id}/usage`
2. **No CSRF token needed** — session cookie + User-Agent header is sufficient
3. **Cookie lifetime** — not yet measured in production; wizard "Reconfigure" path makes
   re-entry frictionless when the cookie expires
4. **Usage unit** — `utilization_pct` (0–100 float) is returned directly; no token counting
   required in the client

---

## Verification Checklist

- [ ] Wizard opens on first run and accepts a valid session key
- [ ] Wizard auto-discovers `org_id` and saves config without user interaction
- [ ] Bar appears after wizard, positioned top-right of primary monitor by default
- [ ] Progress fill reflects `five_hour.utilization_pct` from the API response
- [ ] Countdown text ticks every second without a network call
- [ ] Dragging the bar saves position to config; position restores on next launch
- [ ] Right-click bar → Reconfigure re-opens the wizard
- [ ] Right-click bar → Exit removes tray icon and quits cleanly
- [ ] Left-click tray → toggles bar visibility
- [ ] Right-click tray → Reconfigure re-opens wizard
- [ ] Right-click tray → Exit quits cleanly
- [ ] Expired/invalid cookie shows `Auth error · right-click to fix`
- [ ] Network error shows `Offline`; fill stays at last known level
- [ ] App recovers automatically on next successful poll after an error

---

*Document version: 1.1 — 2026-05-09 (updated post-implementation)*
