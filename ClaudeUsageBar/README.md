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
| **Right-click the bar** | Context menu: Reconfigure or Exit |
| **Left-click tray icon** | Toggle bar visibility (show / hide) |
| **Right-click tray icon** | Show/hide, Reconfigure, or Exit |

The bar updates every 5 minutes (configurable). The countdown text ticks every second
from the cached reset timestamp — no extra network call needed.

### Reading the bar

| Bar state | Meaning |
|-----------|---------|
| Navy fill + white countdown | Normal — shows % used and time to reset |
| `—` in grey | Connected but no active session window yet |
| `Auth error · right-click to fix` | Session key expired — reconfigure to paste a new one |
| `Offline` | Network error — last known fill is retained; recovers on next poll |

---

## Configuration

The config file lives at:

```
%APPDATA%\ClaudeUsageBar\config.json
```

You can edit it in any text editor. Changes take effect on next launch.

```json
{
  "session_key": "sk-ant-sid01-…",
  "org_id": "your-org-uuid",
  "poll_interval_minutes": 5,
  "window": {
    "x": 1200,
    "y": 10,
    "width": 450
  }
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `poll_interval_minutes` | `5` | How often to fetch usage from claude.ai |
| `window.width` | `450` | Bar width in pixels |
| `window.x` / `window.y` | top-right corner | Bar position (updated automatically on drag) |

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

---

## File Structure

```
ClaudeUsageBar/
├── main.py           Entry point — wires all components together
├── bar_window.py     Frameless PyQt6 window with custom paint
├── wizard.py         3-page setup wizard dialog
├── tray.py           System tray icon (pystray + Pillow)
├── claude_client.py  HTTP client for claude.ai internal API
├── config.py         Config file read/write
└── requirements.txt  Python dependencies
```
