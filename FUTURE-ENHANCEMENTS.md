# Claude Usage Bar — Future Enhancements

A living backlog of features, tools, and utilities for the Claude Usage Bar ecosystem and broader Claude-adjacent automation ideas.

---

## Completed Features ✓

These items have been shipped and are live in the current release:

- **Toast notifications** — Fire Windows toast notifications when usage crosses configurable thresholds (80%, 90%)
- **Configurable RAG thresholds** — Adjust amber (default 80%) and red (default 90%) thresholds from the settings dialog
- **Adaptive polling frequency** — When usage enters amber (≥80%) or red (≥90%), polling frequency automatically increases for real-time updates
- **Tray tooltip with reset time** — Hover the tray icon to see current usage percentage and time until session resets
- **Settings dialog** — Full in-app settings UI for poll interval, bar width, colours, RAG thresholds, notifications, and triple session configuration
- **Right-click context menu** — Access Settings, Reconfigure, and Exit from the bar itself
- **Suspend/resume handling** — Bar re-shows automatically when system resumes from sleep
- **Click-through mode** — Windows pass-through input so the bar doesn't interfere with interactions beneath it
- **Opacity control** — Adjustable bar opacity (30–100%) for better desktop blending
- **Triple Session scheduler** — Automatically activate four staggered 5-hour sessions aligned to your working hours
- **Multiple colour profiles** — Fully customizable fill, background, and text colours

---

## Tier 1 — High Value, Low Complexity

### 1. Auto-Start with Windows
**What:** Register the app in Windows startup registry so it launches on login.  
**Why:** Users shouldn't need to manually start the app each day.  
**How:** Write/delete `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\ClaudeUsageBar` pointing to the Python entry point. Toggle via tray menu item ("Start with Windows ✓").  
**Config:** `"start_with_windows": false` in `config.json`.

---

### 2. Tray Icon Reflects RAG State
**What:** The tray icon shifts colour to match RAG state — amber at 80%, red at 90%.  
**Why:** The bar may be hidden; the tray icon is always visible.  
**How:** `tray.py` regenerates the PIL icon with the current RAG colour and updates it live via `pystray.Icon.icon =`.  
**No config needed** — follows `rag_mode` setting automatically.

---

### 3. Force-Refresh on Right-Click
**What:** Add "Refresh now" to the right-click context menu to trigger an immediate poll.  
**Why:** After idle periods or heavy usage, waiting 5 minutes for an update is frustrating.  
**How:** Call `_fetch()` directly and restart the polling timer.

---

### 4. Session Reset Notification
**What:** Fire a toast when usage resets — "Claude session refreshed — you're back to 0%."  
**Why:** The reset is the most important event for workflow.  
**How:** Detect when `_pct` drops from >0 to near-0 and emit a one-shot notification.

---

### 5. Snap to Screen Edges When Dragging
**What:** While dragging the bar, snap it to the nearest screen edge or corner when within ~20px.  
**Why:** Positions the bar neatly without pixel-perfect dragging.  
**How:** In `mouseMoveEvent`, check proximity to each screen edge and clamp accordingly.

---

## Tier 2 — Medium Complexity, High Reward

### 6. Multi-Monitor Awareness
**What:** Remember bar position per monitor configuration. Snap to valid position if monitors change.  
**How:** In `_place_window()`, clamp `(x, y)` to the union of all screen geometries. Optionally store per-monitor positions keyed by screen geometry hash.

---

### 7. Session Key Expiry Detection
**What:** After N consecutive auth errors, show a specific tray notification and optionally open the wizard.  
**Why:** Current "Auth error · right-click to fix" is vague; most auth errors are expiry.  
**How:** Track `_consecutive_auth_errors` in `main.py`; after threshold (e.g., 3), fire a toast.

---

### 8. Usage History & Mini Sparkline
**What:** Log each polled percentage with timestamp to SQLite. Show a 24-hour or 7-day sparkline overlay.  
**Why:** Visibility into usage patterns — are you consistently hitting 90% at the same time?  
**How:** New `history.py` module; render sparkline in `paintEvent` or a separate small window.

---

### 9. Usage Rate + "Safe to Go" Estimate
**What:** Track percentage over time and display estimated remaining productive time — e.g., "~45 min left at this rate."  
**Why:** Knowing you're at 70% is less useful than knowing you'll hit 90% in 20 minutes.  
**How:** Store last 3–5 `(timestamp, pct)` samples; compute linear rate; project to 90% threshold. Show in hover tooltip or tray tooltip.

---

### 10. Session Count Today
**What:** Track how many 5-hour windows consumed today. Show in tooltip — e.g., "3rd session today · 42% used."  
**Why:** Knowing you're on your 3rd window is materially different from 42% — gives sense of daily workload.  
**How:** Depends on item 8 (history). Increment daily counter on each reset event.

---

### 11. Plan / Limit Auto-Detection
**What:** Read plan metadata from the usage API response to detect whether user is on Pro, Team, or Max.  
**Why:** Different plans have different capacities; surfacing the plan makes the percentage more meaningful.  
**How:** Inspect the full usage API response for `plan` or `subscription` field; store and display in tooltip.  
**Config:** `"detected_plan": ""` (auto-populated, not user-editable).

---

### 12. Webhook / HTTP Callback on Threshold
**What:** POST to a user-defined URL when a RAG threshold is crossed.  
**Why:** Enables automation — trigger a Slack message, Home Assistant event, or custom script.  
**How:** Fire a background `requests.post()` thread on threshold crossing. Include deduplication logic to avoid spam.  
**Config:** `"webhook": {"url": "", "thresholds": [80, 90]}`.

---

### 13. Update Checker
**What:** Check GitHub releases endpoint on startup for a newer version and show a tray notification.  
**Why:** No auto-update mechanism; users may run stale versions indefinitely.  
**How:** Background thread fetches `version.json` or GitHub API `/releases/latest`; compare against hardcoded `__version__` in `main.py`.  
**Config:** `"check_for_updates": true`.

---

## Tier 3 — Ambitious, Longer-Term

### 14. Anthropic API Usage Tracking
**What:** A second bar or segmented overlay tracking API token consumption for users who also use the Anthropic API.  
**Why:** Different usage bucket from claude.ai sessions.  
**How:** New `anthropic_client.py`; second `BarWindow` or segmented single bar. Requires additional setup for API key.

---

### 15. Poll on Network Reconnect
**What:** Trigger immediate poll when coming back online instead of waiting for next timer tick.  
**Why:** After outages the bar shows stale data until next 5-minute tick.  
**How:** `QNetworkAccessManager` reachability signals or lightweight socket probe in fetch thread.

---

### 16. Adjustable Bar Height
**What:** Let users set bar height (currently 27px) via config, between 16px and 48px.  
**Why:** High-DPI displays or personal preference — thinner bar is less intrusive, taller is easier to read.  
**How:** Replace hardcoded `27` in `_setup_window()` with `self._cfg.get("window", {}).get("height", 27)`. Scale font proportionally.  
**Config:** `"window": {"height": 27}`.

---

### 17. Exportable Usage Report
**What:** Right-click menu item — "Export usage log…" — saves history to CSV.  
**Why:** Useful for understanding patterns or sharing with team to justify Claude Pro seats.  
**How:** Reads SQLite history DB; writes `timestamp,pct` rows to user-chosen path via `QFileDialog`. Depends on item 8.

---

### 18. Second Bar for Message Count
**What:** Show a second bar (or split segment) for message-count limit if the API exposes it separately.  
**Why:** Some users hit message limits before utilisation % is high. Future-proofs for granular quota data.  
**How:** Extend `claude_client.get_usage()` to return additional quota fields; render second `BarWindow` stacked below the primary.

---

### 19. Adaptive (P90) Threshold Suggestion
**What:** After accumulating history, compute 90th-percentile peak usage from last 8 days. If materially lower than amber threshold, surface a notification: "Your typical peak is 65% — consider lowering the amber threshold."  
**Why:** Fixed 80/90% thresholds are poorly calibrated for users who consistently stay below or breach them — personalised thresholds mean warnings signal something unusual.  
**How:** New function in `history.py` queries DB for p90 max-per-session over last 192 hours. Run once daily; compare against `rag_thresholds.amber`. Fire one-shot notification if gap > 15pp.  
**Config:** `"adaptive_thresholds": {"enabled": true, "notify_gap": 15}`. Depends on items 8, 9, 19.

---

### 20. Multiple Account Profiles
**What:** Store multiple `(session_key, org_id)` pairs and switch between them from the tray menu.  
**Why:** Users managing multiple Claude.ai accounts (personal + work) currently need to re-run the wizard each time.  
**How:** Config gains `"profiles": [{"name": "Work", "session_key": "...", "org_id": "..."}]` with `"active_profile"` index. Tray menu shows "Switch account" submenu.  
**Config:** `"active_profile": 0` in `config.json`.

---

### 21. Smooth Fill Animation
**What:** Animate the fill bar smoothly when usage changes instead of jumping instantly.  
**Why:** Smoother, more polished feel; easier to see the change visually.  
**How:** Tween `_pct` from current to new value over 500–800ms using a `QPropertyAnimation`.

---

### 22. Hover Tooltip on Bar
**What:** When hovering over the bar, show a rich tooltip with usage%, reset time, plan info, and usage rate estimate.  
**Why:** All key info in one glance without switching windows.  
**How:** Override `enterEvent` / `leaveEvent`; show a styled QToolTip or custom frameless window with formatted text.

---

### 23. Global Hotkey Show/Hide
**What:** Register a global hotkey (e.g., `Win+Shift+C`) to toggle bar visibility without using tray menu.  
**Why:** Power users appreciate keyboard shortcuts.  
**How:** `keyboard` library or native Win32 hotkey registration via `RegisterHotKey`.

---

---

## Broader Claude Utility Ideas

These are tools in the spirit of ClaudeUsageBar — small, focused Windows desktop utilities that smooth day-to-day Claude use. Each is a standalone app or system integration, not an enhancement to the bar itself.

---

### 24. Right-Click "Ask Claude" Context Menu

**What:** Select any text anywhere on Windows, right-click, choose "Ask Claude" → get response in a small floating dialog.  
**Why:** Removes friction of switching to browser, pasting, waiting.  
**How:** Shell context menu extension (registry under `HKCR\*\shell\AskClaude`). Launches lightweight PyQt window using Anthropic API (not claude.ai session cookie).  
**Variants:**
- "Ask Claude" — open-ended question
- "Summarise this" — fixed prompt
- "Fix grammar" — fixed prompt
- "Explain this code" — fixed prompt

---

### 25. Floating Quick-Ask Bar

**What:** Persistent single-line input box with global hotkey (`Win+Space`) — type question, get answer in popup. Like Spotlight on macOS but for Claude.  
**Why:** Faster than browser tab. Doesn't interrupt flow — dismiss and you're back where you were.  
**How:** PyQt6 frameless window, hidden by default. Global hotkey via `keyboard` library. Streams response token-by-token into expandable text area. Keeps local history of recent queries.

---

### 26. Claude Status Monitor

**What:** Tiny tray indicator showing whether claude.ai is up, degraded, or down — using Anthropic status page API.  
**Why:** When Claude feels slow, you waste time refreshing before realising there's an incident.  
**How:** Poll `https://status.anthropic.com/api/v2/status.json` every 60s. Green = all good, amber = degraded, red = outage. Toast on status change.  
**Standalone or bundled:** New tray icon, or overlay dot on usage bar.

---

### 27. Prompt Library Manager

**What:** Searchable local library of your best Claude prompts — save, tag, copy-to-clipboard, launch directly.  
**Why:** Power users accumulate go-to prompts (code review, email drafting, templates) in bookmarks/Notion/memory.  
**How:** PyQt6 app with searchable list, tag filter, "Copy & Open Claude" button. Stores in SQLite DB. Optional import/export to JSON for team sharing.  
**Extras:** Prompt variables (`{{name}}`, `{{date}}`) with fill-before-copy dialog.

---

### 28. Screenshot → Claude

**What:** Global hotkey captures region of screen and sends directly to Claude with configurable question.  
**Why:** Screenshot today → save → open browser → upload = 4 steps. This is 1 keypress.  
**How:** `mss` or `PIL.ImageGrab` for capture. Anthropic API messages endpoint with `image` content block (base64). Response shown in floating window.  
**Variants:** Full screen, active window, or drag-to-select region.

---

### 29. Token / Cost Estimator

**What:** Select text → right-click "Count tokens" → floating bubble shows `~1,840 tokens · ~$0.003 at Sonnet prices`.  
**Why:** API users frequently over/under-estimate prompt size and cost. Knowing before you send avoids surprise bills.  
**How:** Use `anthropic` SDK's `client.messages.count_tokens()` endpoint (or `tiktoken`-compatible tokeniser offline). Same context menu integration as item 24.  
**Modes:** Offline estimate (instant, no API call) or exact count (one lightweight API call).

---

### 30. Claude Conversation Exporter

**What:** Browser extension (or bookmarklet) that exports current Claude conversation to Markdown, PDF, or Word with one click.  
**Why:** Claude produces work worth keeping — architecture decisions, code reviews, research. Native UI has no export.  
**How:** Content script reads conversation DOM and serialises to structured Markdown. PDF via `wkhtmltopdf` or browser print.  
**Standalone:** Could also be local web scraper given a conversation URL.

---

### 31. Scheduled Claude Tasks

**What:** Define prompts that run on schedule (daily 9am, every Monday, etc.) and deliver to clipboard, local file, toast, or email.  
**Why:** "Summarise news", "Generate daily standup", "Draft weekly review" — prompts you want to run automatically.  
**How:** Windows Task Scheduler triggers Python script with prompt config. Uses Anthropic API. Results written to `%APPDATA%\ClaudeScheduler\outputs\`.  
**Config:** YAML job files with `schedule`, `prompt`, `output` fields.

---

### 32. API Usage & Cost Dashboard

**What:** Local web dashboard (or PyQt window) tracking Anthropic API spend by model, day, week, project — pulled from billing API.  
**Why:** Anthropic console shows spend but no breakdown by model or time-of-day pattern.  
**How:** Poll `https://api.anthropic.com/v1/usage` (or scrape console if no official endpoint). Store in SQLite. Render with PyQt chart or local `http.server` + Chart.js.  
**Companion to ClaudeUsageBar:** Bar = claude.ai session usage. Dashboard = API spend. Together cover both surfaces.

---

### 33. Clipboard AI Pipeline

**What:** Background tray utility that watches clipboard. When text matches trigger pattern (e.g. starts with `//ai:`), automatically sends to Claude and replaces clipboard with response.  
**Why:** Zero-friction AI transformation. Copy `//ai: summarise this` → [paste long article] → wait 2s → paste summary.  
**How:** `pyperclip` or `win32clipboard` for clipboard monitoring in background thread. Pattern match → API call → write response back to clipboard. Toast notification when ready.  
**Configurable trigger:** prefix string, regex, or keyboard chord.

---

### 34. Claude for Windows Notifications (Reply Tracker)

**What:** Browser extension or background script that detects when long-running Claude response finishes and fires a Windows toast.  
**Why:** For long coding tasks or research prompts you often switch away and forget to check back.  
**How:** Extension polls for "stop" signal in claude.ai SSE stream and calls Windows notification API via native messaging or local HTTP endpoint.

---

### 35. Team Usage Dashboard

**What:** Shared local web page (or hosted lightweight app) showing combined Claude API usage across team — per user, per project, per day.  
**Why:** Teams sharing an Anthropic API key have no visibility into who consumes what. Useful for cost allocation and spotting runaway usage.  
**How:** Each team member runs lightweight agent shipping usage data to central SQLite (or hosted Postgres). Dashboard renders it. Alternatively, single admin polls Anthropic billing API and distributes read-only dashboard URL.

---

## Priority Matrix

| # | Feature | Type | Complexity | Value | Status |
|---|---------|------|-----------|-------|--------|
| 1 | Auto-start with Windows | Bar | Low | High | Backlog |
| 2 | Tray icon RAG color | Bar | Low | Medium | Backlog |
| 3 | Force-refresh menu item | Bar | Low | High | Backlog |
| 4 | Session reset notification | Bar | Low | High | Backlog |
| 5 | Snap to screen edges | Bar | Low | Medium | Backlog |
| 6 | Multi-monitor awareness | Bar | Medium | High | Backlog |
| 7 | Session key expiry detection | Bar | Medium | High | Backlog |
| 8 | Usage history + sparkline | Bar | High | Medium | Backlog |
| 9 | Usage rate / "safe to go" | Bar | Medium | High | Backlog |
| 10 | Session count today | Bar | Medium | High | Backlog |
| 11 | Plan / limit auto-detection | Bar | Medium | Medium | Backlog |
| 12 | Webhook on threshold | Bar | Medium | Medium | Backlog |
| 13 | Update checker | Bar | Medium | Medium | Backlog |
| 14 | Anthropic API tracking | Bar | High | High | Backlog |
| 15 | Poll on network reconnect | Bar | Medium | Medium | Backlog |
| 16 | Adjustable bar height | Bar | Low | Low | Backlog |
| 17 | Exportable usage report | Bar | Medium | Low | Backlog |
| 18 | Second bar for message count | Bar | High | Medium | Backlog |
| 19 | Adaptive (P90) thresholds | Bar | High | Medium | Backlog |
| 20 | Multiple account profiles | Bar | Medium | High | Backlog |
| 21 | Smooth fill animation | Bar | Low | Low | Backlog |
| 22 | Hover tooltip on bar | Bar | Medium | High | Backlog |
| 23 | Global hotkey show/hide | Bar | Medium | Medium | Backlog |
| 24 | Right-click "Ask Claude" | Tool | Low | High | Standalone |
| 25 | Floating quick-ask bar | Tool | Low | High | Standalone |
| 26 | Claude status monitor | Tool | Low | High | Standalone |
| 27 | Prompt library manager | Tool | Medium | High | Standalone |
| 28 | Screenshot → Claude | Tool | Medium | High | Standalone |
| 29 | Token / cost estimator | Tool | Low | High | Standalone |
| 30 | Conversation exporter | Tool | Medium | Medium | Standalone |
| 31 | Scheduled Claude tasks | Tool | Medium | High | Standalone |
| 32 | API usage dashboard | Tool | Medium | High | Standalone |
| 33 | Clipboard AI pipeline | Tool | Medium | High | Standalone |
| 34 | Reply-finished notifier | Tool | Low | High | Standalone |
| 35 | Team usage dashboard | Tool | High | High | Standalone |

---

## Notes

- **Bar items** (1–23) are enhancements to the Claude Usage Bar itself.
- **Tool items** (24–35) are standalone utilities or integrations that live in the broader Claude ecosystem.
- Items marked **Completed** are live in the current release and documented in the README.
- The priority matrix weights **complexity** (dev effort) and **value** (user benefit). High value + low complexity = quick wins.
- Many Tier 2/3 items build on `history.py` (item 8); shipping that unlocks several downstream features.
