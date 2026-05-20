# Claude Usage Bar

A compact, floating Windows utility that shows your Claude.ai 5-hour session usage as a
slim always-on-top progress bar with a live countdown to the next reset.

```
┌──────────────────────────────────────────────┐
│████████████████████░░░░░░░  resets in 3h 22m │
└──────────────────────────────────────────────┘
```

- **Navy blue** = tokens used
- **Near-black** = tokens remaining
- **White text** = time until the usage window resets
- Bar is 22 px tall, ~450 px wide, always on top, draggable anywhere on screen

---

## Features

### Core
- **Floating progress bar** — Always-on-top 27px bar showing usage % with live countdown to reset
- **Drag-to-reposition** — Click and drag to move; position is saved automatically
- **System tray integration** — Control visibility, toggle Triple Session, access settings, and exit from the tray icon
- **Multiple colour profiles** — Fully customizable fill, background, and text colours via settings

### Monitoring
- **Adaptive polling** — Base interval (default 5 minutes) automatically increases when usage enters amber (≥80%) or red (≥90%)
- **RAG mode indicators** — Bar colour changes to amber at 80%, red at 90%; thresholds are configurable
- **Tray tooltip** — Hover the tray icon to see current usage percentage and time until session resets
- **Toast notifications** — Windows notifications fire when usage crosses configured thresholds
- **Network resilience** — On network error, bar retains last known fill level; recovers automatically on next poll

### Configuration
- **In-app settings dialog** — Adjust poll interval (1–60 min), bar width (50–400 px), colours, RAG thresholds, notifications, and triple session settings without touching config files
- **Opacity control** — Adjustable bar opacity (30–100%) for better desktop blending
- **Click-through mode** — Enable pass-through input so the bar doesn't interfere with interactions beneath it
- **Right-click context menu** — Quick access to Settings, Reconfigure, and Exit

### Session Management
- **Triple Session scheduler** — Automatically activate four staggered 5-hour sessions aligned to your working hours (default: 7 AM, 12 PM, 5 PM, 10 PM)
- **Automatic session reset detection** — Bar shows "resetting…" and resets to 0% when the 5-hour window resets
- **Setup wizard** — Three-page on-first-launch wizard for session key entry and automatic organisation discovery
- **Auth error recovery** — Clear error messaging when session key expires; quick path to reconfigure

### System Integration
- **Suspend/resume handling** — Bar re-shows automatically when system resumes from sleep
- **Always-on-top behaviour** — Never obscured by other windows unless they also use always-on-top (Windows limitation)
- **Taskbar integration** — System tray icon with menu; bar is hidden from taskbar

---

## Roadmap

See [`FUTURE-ENHANCEMENTS.md`](FUTURE-ENHANCEMENTS.md) for the complete backlog of planned features, including:
- **Tier 1** — High-value quick wins (auto-start, force-refresh, tray icon RAG colour, etc.)
- **Tier 2** — Medium-complexity features (multi-monitor support, usage history, session counting, etc.)
- **Tier 3** — Ambitious longer-term items (API tracking, sparkline visualisation, adaptive thresholds, etc.)
- **Broader tools** — Standalone utilities in the Claude ecosystem (quick-ask bar, screenshot-to-Claude, prompt library, etc.)

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Windows     | 10 or 11 |
| Python      | 3.11 or later (tested on 3.14) |
| Claude.ai account | Pro, Team, or Max subscription |

Install Python from [python.org](https://www.python.org/downloads/) if needed.
Make sure to tick **"Add Python to PATH"** during installation.

---

## Installation

```
cd ClaudeUsageBar
py -m pip install -r requirements.txt
```

---

## First-time Setup

### Step 1 — Get your session key from the browser

1. Open **https://claude.ai** in Chrome, Edge, or Firefox and make sure you're logged in
2. Press **F12** to open Developer Tools
3. Go to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox)
4. Expand **Cookies** in the left panel and click **https://claude.ai**
5. Find the cookie named **`sessionKey`** — its value starts with `sk-ant-sid01-`
6. Copy the entire value (it's long — use Ctrl+A to select all in the Value field)

### Step 2 — Run the app and paste the key

```
py main.py
```

The setup wizard opens automatically on first launch. Paste the session key and click
**Test & Connect**. The app will validate the key and discover your organisation ID
automatically. Click **Start Monitoring** when the test passes.

The floating bar appears immediately after the wizard closes.

---

## Daily Use

| Action | What happens |
|--------|-------------|
| **Drag the bar** | Click and drag to move it anywhere on screen — position is saved |
| **Right-click the bar** | Context menu: Settings, Reconfigure, or Exit |
| **Left-click tray icon** | Toggle bar visibility (show / hide) |
| **Right-click tray icon** | Show/hide, Triple Session toggle, Settings, Reconfigure, or Exit |

The bar updates every 5 minutes (configurable). The countdown text ticks every second
from the cached reset timestamp — no extra network call needed.

### Reading the bar

| Bar state | Meaning |
|-----------|---------|
| Navy fill + white countdown | Normal — shows % used and time to reset |
| `—` in grey | Connected but no active session window yet |
| `Auth error · right-click to fix` | Session key expired — reconfigure to paste a new one |
| `Offline` | Network error — last known fill is retained; recovers on next poll |

### RAG Red Amber Green

Ay 80% and 90% the colour of the bar will change to Amber / Red, and the frequency of the updates performed also incresees to present a more accurate picture to the user. 
---

## Triple Session

Claude.ai's usage resets on a rolling 5-hour window that starts when you first send a
message in that window. If you don't send anything at the start of a window, you lose that
time. The Triple Session feature solves this by automatically sending a short message to
claude.ai at each of your scheduled session times — activating the window on your behalf.
The trigger conversation is deleted immediately after sending so it never appears in your
chat history.

### How it works

Set a **work start time** (e.g. 7:00 AM) and the app computes four session slots spaced
5 hours apart for the day:

```
Session 1:  7:00 AM – 12:00 PM
Session 2: 12:00 PM –  5:00 PM
Session 3:  5:00 PM – 10:00 PM
Session 4: 10:00 PM –  3:00 AM  (optional bonus session)
```

At each slot time the app sends a configurable prompt (default: `Hi`) using your existing
session cookie, then deletes the conversation. The 5-hour clock starts ticking from that
moment, aligned to your schedule.

### Enabling Triple Session

Right-click the tray icon and click **Triple Session: OFF** to toggle it on. The menu
updates to show your four session times for the day:

```
Triple Session: ON ✓
  7:00 AM · 12:00 PM · 5:00 PM · 10:00 PM
```

The setting is saved to config immediately — no restart required. Toggle it off the same
way when you don't need it (e.g. weekends).

### Configuration

Open **Settings** from either right-click menu to configure triple session without touching any files:

- **Enabled** checkbox — same as the tray toggle
- **First session starts at** — 24-hour time picker
- **Trigger prompt** — the message sent to activate each session

Changes take effect immediately when you click **Save**.

You can also edit `config.json` directly:

```json
"triple_session": {
  "enabled": true,
  "work_start": "07:00",
  "prompt": "Hi"
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `false` | Turn the scheduler on or off (also togglable from tray or Settings) |
| `work_start` | `"07:00"` | Local time of session 1 — subsequent sessions are +5 h, +10 h, +15 h |
| `prompt` | `"Hi"` | Message sent to activate each session; any short text works |

> **Note:** Triple Session uses the same internal claude.ai API as the usage bar, so no
> extra API key is needed. It does consume one message from each 5-hour session window.

---

## Configuration

Most settings are accessible directly from the app via **Settings** (right-click the bar or
the tray icon):

| Setting | Range | Description |
|---------|-------|-------------|
| Poll interval | 1–60 min | How often to fetch usage from claude.ai |
| Bar width | 50–400 px | Width of the floating bar |
| Fill colour | colour picker | Colour of the used-tokens portion |
| Background colour | colour picker | Colour of the unused-tokens portion |
| Text colour | colour picker | Colour of the countdown and percentage text |
| Triple Session enabled | checkbox | Enable/disable the session scheduler |
| First session starts at | time picker | Work-start time for the session schedule |
| Trigger prompt | text field | Message sent to activate each session |

Changes take effect immediately when you click **Save** — no restart required.

The underlying config file is at:

```
%APPDATA%\ClaudeUsageBar\config.json
```

You can also edit it directly in any text editor (changes take effect on next launch):

```json
{
  "session_key": "sk-ant-sid01-…",
  "org_id": "your-org-uuid",
  "poll_interval_minutes": 5,
  "window": {
    "x": 1200,
    "y": 10,
    "width": 450
  },
  "colors": {
    "fill": "#14532D",
    "background": "#030A05",
    "text": "#86EFAC"
  }
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `poll_interval_minutes` | `5` | How often to fetch usage from claude.ai |
| `window.width` | `123` | Bar width in pixels |
| `window.x` / `window.y` | top-right corner | Bar position (updated automatically on drag) |
| `colors.fill` | `#14532D` | Used-tokens bar colour |
| `colors.background` | `#030A05` | Unused-tokens bar colour |
| `colors.text` | `#86EFAC` | Countdown and percentage text colour |

---

## Session Key Expiry

The `sessionKey` cookie is the same one your browser uses when you visit claude.ai.
It typically stays valid for weeks, but will expire if you:

- Log out of claude.ai in your browser
- Your browser clears cookies
- Anthropic rotates it for security reasons

When the key expires, the bar shows `Auth error · right-click to fix`. Open
**Reconfigure** from the bar or tray icon, go back through the wizard, and paste a fresh
`sessionKey` value from your browser.

---

## Logs

Application logs (info + errors) are written to:

```
%APPDATA%\ClaudeUsageBar\app.log
```

Useful for diagnosing network errors or unexpected API responses.

---

## Troubleshooting

**"Auth failed" on the Test & Connect step**
- Make sure you copied the *Value* of `sessionKey`, not the cookie name
- The value should start with `sk-ant-sid01-` and be several hundred characters long
- Try refreshing claude.ai and copying the cookie again — it may have just refreshed

**Bar appears but fill never changes / shows "—"**
- Claude.ai may not be showing a `five_hour` usage window for your account type
- Check `%APPDATA%\ClaudeUsageBar\app.log` for the raw API response

**Tray icon doesn't appear**
- Windows sometimes hides new tray icons — check the overflow area (arrow on taskbar)
- Right-click the taskbar → Taskbar settings → Other system tray icons to pin it

**Bar appears behind other always-on-top windows (e.g. Task Manager)**
- This is a Windows limitation; you can drag the bar to a less obstructed position

**Triple Session trigger not firing**
- Check `%APPDATA%\ClaudeUsageBar\app.log` for `Triple session trigger failed` and the error message
- The most likely cause is a change to the claude.ai internal API — look for the HTTP status code in the log
- Confirm Triple Session is enabled: right-click tray → the item should read `Triple Session: ON ✓`
- Make sure `work_start` in config.json is in `HH:MM` 24-hour format (e.g. `"07:00"`, not `"7:00 AM"`) — the Settings dialog enforces this automatically

---

## File Structure

```
ClaudeUsageBar/
├── main.py              Entry point — wires all components together
├── bar_window.py        Frameless PyQt6 window with custom paint
├── wizard.py            3-page setup wizard dialog
├── settings_dialog.py   Settings dialog (poll interval, width, colours, triple session)
├── tray.py              System tray icon (pystray + Pillow)
├── claude_client.py     HTTP client for claude.ai internal API
├── config.py            Config file read/write
└── requirements.txt     Python dependencies
```
