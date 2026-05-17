# ClaudeUsageBar — v2.0 Backlog

## What's already in v1.0
- Floating progress bar (fill + countdown + percentage text)
- Configurable colors (`fill`, `background`, `text`) via `config.json`
- RAG mode (amber ≥80%, red ≥90%) — hardcoded, non-overridable
- 5-minute polling with last-known-fill retention on network error
- Drag-to-reposition (saves to config on mouse release)
- System tray (toggle visibility, Reconfigure, Exit)
- Setup wizard (sessionKey entry + org auto-discovery)
- Auth error and offline error states
**get the frequency of bar updates to increse as we enter Amber and red**
**option resets in xh xm or a time**

---

## Tier 1 — High value, low complexity

### Dan
**as soon as a session reaches 100%  and a session ends it should trigger a new session - make it an option**

### 1. Windows Toast Notifications
**What:** Pop a native Windows notification when usage crosses a threshold (e.g., 80%, 90%, reset).
**Why:** The bar could be hidden — a toast ensures you don't miss a critical state.
**How:** `windows-toasts` or `win10toast-reborn` library; fire once per threshold crossing (track `_last_notified_threshold` in `main.py` to avoid repeat toasts).
**Config:** `"notifications": {"enabled": true, "thresholds": [80, 90]}` in `config.json`.

---

### 2. Auto-Start with Windows
**What:** Register the app in the Windows startup registry so it launches on login.
**Why:** Explicitly listed as a v2 goal in the PRD. Currently users must start it manually.
**How:** Write/delete `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\ClaudeUsageBar` pointing to a `start.bat` or the Python entry point. Toggle via tray menu item ("Start with Windows ✓").
**Config:** `"start_with_windows": false` in `config.json`.

---

### 3. Tray Icon Reflects RAG State
**What:** The tray icon (currently always dark navy) shifts color to match the RAG state — amber at 80%, red at 90%.
**Why:** The bar may be hidden; the tray icon is always visible in the corner.
**How:** `tray.py` generates a `PIL.Image` icon at startup. Regenerate it with the current RAG fill color and call `pystray.Icon.icon =` to update it live. Hook into the `data_ready` signal path in `main.py`.
**No config needed** — follows `rag_mode` setting automatically.

---

### 4. Configurable RAG Thresholds
**What:** Let users set the amber and red trigger percentages (currently hardcoded at 80/90).
**Why:** Power users may want earlier warnings (e.g., amber at 60%) or later ones.
**How:** Read from config: `"rag_thresholds": {"amber": 80, "red": 90}`. Update `_rag_override()` in `bar_window.py` to use these values. The colors themselves remain hardcoded.
**Config:** `"rag_thresholds": {"amber": 80, "red": 90}`.

---

### 5. Tray Tooltip Shows Reset Time
**What:** Tray tooltip currently shows only `"Claude: 42% used"`. Extend it to include reset time — `"Claude: 42% · resets in 2h 15m"`.
**Why:** Hovering the tray icon is quicker than reading the bar when it's off-screen.
**How:** Pass `reset_at` through to `TrayIcon.set_tooltip()` in `tray.py` and format it the same way `bar_window.py` does.

---

## Tier 2 — Medium complexity, high reward

### 8. Multi-Monitor Awareness
**What:** Remember bar position per monitor configuration. When the monitor layout changes (docking/undocking), snap the bar to a valid position rather than disappearing off-screen.
**How:** In `_place_window()`, check `QApplication.screens()` and clamp `(x, y)` to the union of all screen geometries. Optionally store per-monitor positions keyed by screen geometry hash.

---

### 10. Session Key Expiry Detection
**What:** After N consecutive auth errors, show a specific tray notification: "Session key expired — click to reconfigure."
**Why:** Current "Auth error · right-click to fix" is vague. Most auth errors in practice are expiry.
**How:** Track `_consecutive_auth_errors` in `main.py`; after threshold (e.g., 3), fire a toast and optionally open the wizard automatically.

---

## Tier 3 — Ambitious, longer-term

### 12. Usage History + Mini Sparkline
**What:** Log each polled percentage with a timestamp to a local SQLite file. Show a tiny sparkline (24-hour or 7-day) as an optional overlay or tray-click popup.
**Why:** Visibility into usage patterns — are you consistently hitting 90% at the same time each day?
**How:** New `history.py` module; write on each successful fetch. Render sparkline in `paintEvent` as a thin overlay line or separate small window.

---

### 13. Anthropic API Usage Tracking
**What:** A second bar or segmented overlay tracking API token consumption for users who also use the Anthropic API directly.
**Why:** Explicitly deferred to v2 in the PRD. Different usage bucket from claude.ai sessions.
**How:** New `anthropic_client.py`; second `BarWindow` or a segmented single bar. Requires additional setup step for the API key.

---

### 14. Poll on Network Reconnect
**What:** Trigger an immediate poll when coming back online instead of waiting for the next timer tick.
**Why:** After a network outage the bar shows stale data until the next 5-minute tick.
**How:** `QNetworkAccessManager` reachability signals or a lightweight socket probe in the fetch thread.

---

## Tier 1 additions

### 15. Force-Refresh on Right-Click
**What:** Add "Refresh now" to the right-click context menu to trigger an immediate API poll.
**Why:** After a long idle period or after you know you've just used Claude heavily, waiting up to 5 minutes for the bar to update is frustrating.
**How:** Call `_fetch()` directly from the menu action in `main.py`; cancel and restart the polling timer so the next automatic poll is 5 minutes from now.

---

### 16. Session Reset Notification
**What:** When the countdown hits zero and the bar resets to 0%, fire a toast — "Claude session refreshed — you're back to full capacity."
**Why:** The reset is the most important event; knowing immediately means you can dive back in rather than checking the bar periodically.
**How:** In `set_data()`, detect when `_pct` drops from >0 to near-0 after a reset and emit a one-shot notification.

---

### 17. Click-Through Mode
**What:** Make the bar invisible to mouse clicks so it can float over other windows without interfering with interaction beneath it.
**Why:** Useful when the bar is parked over a document or browser — currently it steals all click/drag events in its footprint.
**How:** Toggle `WS_EX_TRANSPARENT` extended window style via `win32api`. Disable drag-to-reposition while active. Toggle from tray menu ("Click-through ✓").
**Config:** `"click_through": false`.

CAN we also make it a tad transparent so this is usegul ? see below

---

### 18. Opacity Control
**What:** Make the bar semi-transparent (e.g., 60–100% opacity), configurable via `config.json`.
**Why:** At full opacity the bar can feel visually heavy; at lower opacity it blends into the desktop while remaining readable.
**How:** `self.setWindowOpacity(opacity)` in `bar_window.py` — single line. Slider in the config editor (item 9) if that ships.
**Config:** `"opacity": 1.0` (range 0.3–1.0).

---

### 19. Snap to Screen Edges When Dragging
**What:** While dragging the bar, snap it to the nearest screen edge or corner when within ~20px of one.
**Why:** Positions the bar neatly at a screen boundary without pixel-perfect dragging.
**How:** In `mouseMoveEvent`, after computing the new position check proximity to each screen edge geometry and clamp accordingly.

---


### 22. Usage Rate + "Safe to Go" Estimate
**What:** Track percentage over time and display an estimated remaining productive time — e.g., "~45 min left at this rate" — in the hover tooltip.
**Why:** Knowing you're at 70% is less useful than knowing you'll hit 90% in 20 minutes at your current burn rate.
**How:** Store the last 3–5 `(timestamp, pct)` samples in memory; compute a linear rate (pct/min); project to the 90% threshold. Show in the hover tooltip (item 7) or tray tooltip (item 5). No persistence needed — in-memory only.

---

### 23. Multiple Account Profiles
**What:** Store multiple `(session_key, org_id)` pairs and switch between them from the tray menu.
**Why:** Users who manage multiple Claude.ai accounts (personal + work) currently need to re-run the wizard and overwrite their config each time.
**How:** Config gains `"profiles": [{"name": "Work", "session_key": "...", "org_id": "..."}]` with an `"active_profile"` index. Tray menu shows a "Switch account" submenu. `main.py` reads the active profile at poll time.

---

### 24. Webhook / HTTP Callback on Threshold
**What:** POST to a user-defined URL when a RAG threshold is crossed (e.g., hitting 80% or 90%).
**Why:** Enables automation — trigger a Slack message, a Home Assistant event, or any custom script without keeping a separate polling service running.
**How:** Fire a background `requests.post(url, json={"pct": pct, "threshold": 80})` thread on threshold crossing. Same deduplication logic as toast notifications (item 1).
**Config:** `"webhook": {"url": "", "thresholds": [80, 90]}`.

---

### 25. Update Checker
**What:** On startup (or weekly), silently check a GitHub releases endpoint for a newer version and show a tray notification if one is available.
**Why:** The app has no auto-update mechanism; users may run stale versions indefinitely.
**How:** Background thread fetches a `version.json` or GitHub API `/releases/latest`; compare against a hardcoded `__version__` string in `main.py`. Notification links to the releases page.
**Config:** `"check_for_updates": true`.

---

## Tier 3 additions

### 26. Adjustable Bar Height
**What:** Let users set bar height (currently fixed at 27px) via config, between 16px and 48px.
**Why:** High-DPI displays or personal preference — a thinner bar is less intrusive, a taller one is easier to read at a glance.
**How:** Replace the hardcoded `27` in `_setup_window()` with `self._cfg.get("window", {}).get("height", 27)`. Font size should scale proportionally.
**Config:** `"window": {"height": 27}`.

---

### 27. Exportable Usage Report
**What:** Right-click menu item — "Export usage log…" — saves the history (item 12, if built) to a CSV file.
**Why:** Useful for understanding patterns across weeks, or sharing with a team to justify Claude Pro seats.
**How:** Reads the SQLite history DB; writes `timestamp,pct` rows to a user-chosen path via `QFileDialog`. Depends on item 12.

---

### 28. Second Bar for Message Count
**What:** Show a second, thinner bar (or a split segment) for the claude.ai message-count limit if/when the API exposes it separately from the 5-hour utilisation percentage.
**Why:** Some users hit message limits before the utilisation percentage is high. Future-proofing for when Anthropic exposes more granular quota data.
**How:** Extend `claude_client.get_usage()` to return additional quota fields if present; render a second `BarWindow` stacked below the primary one.

---

---

## Tier 2 additions (from community projects)

### 29. Session Count Today
**What:** Track how many 5-hour windows have been consumed today and show it in the hover tooltip — e.g., "3rd session today · 42% used".
**Why:** Knowing you're on your 3rd window is materially different from knowing you're at 42% — it gives a sense of overall daily workload that utilisation % alone doesn't. Inspired by ccusage's session grouping.
**How:** Depends on item 12 (history). On each reset event (detected via item 16 logic), increment a daily counter keyed by local date in the SQLite DB. Read in `bar_window.py` tooltip formatter.
**Config:** None needed.

---

### 30. Plan / Limit Auto-Detection
**What:** Read plan metadata from the `/api/organizations/{org_id}/usage` response (or `/api/account`) to detect whether the user is on Pro, Team, or Max and annotate the tray tooltip — e.g., "Pro · 42% used".
**Why:** Different plans have different session capacities; surfacing the plan makes the percentage more meaningful and avoids confusion when a user upgrades without reconfiguring.
**How:** Log and inspect the full usage API response for a `plan` or `subscription` field. If present, store in config on first successful fetch and display in tooltip. Gracefully omit if absent.
**Config:** `"detected_plan": ""` (auto-populated, not user-editable).

---

### 31. Adaptive (P90) Threshold Suggestion
**What:** After accumulating history (item 12), compute the 90th-percentile peak usage from the last 8 days of sessions. If it's materially lower than the current amber threshold (e.g., you never exceed 65%), surface a tray notification: "Your typical peak is 65% — consider lowering the amber threshold."
**Why:** Inspired by Claude Code Usage Monitor's P90 approach. Fixed 80/90% thresholds are poorly calibrated for users who consistently stay well below them or consistently breach them — personalised thresholds mean warnings actually signal something unusual.
**How:** New function in `history.py` (item 12) that queries the DB for the p90 max-per-session over the last 192 hours. Run once per day in the background and compare against `rag_thresholds.amber`. Fire a one-shot notification if the gap is > 15pp. No auto-change — user must confirm via config editor (item 9).
**Config:** `"adaptive_thresholds": {"enabled": true, "notify_gap": 15}`. Depends on items 4, 9, 12.

---

## Summary

| # | Feature | Complexity | Value |
|---|---------|------------|-------|
| 1 | Toast notifications | Low | High |
| 2 | Auto-start with Windows | Low | High |
| 3 | Tray icon RAG color | Low | Medium |
| 4 | Configurable RAG thresholds | Low | Medium |
| 5 | Tray tooltip + reset time | Low | Medium |
| 6 | Smooth fill animation | Low | Medium |
| 7 | Hover tooltip on bar | Low | Medium |
| 8 | Multi-monitor awareness | Medium | High |
| 9 | In-app config editor | Medium | High |
| 10 | Session key expiry detection | Medium | High |
| 11 | Resizable width via drag | Medium | Medium |
| 12 | Usage history + sparkline | High | Medium |
| 13 | Anthropic API tracking | High | High |
| 14 | Poll on network reconnect | Medium | Medium |
| 15 | Force-refresh on right-click | Low | High |
| 16 | Session reset notification | Low | High |
| 17 | Click-through mode | Low | Medium |
| 18 | Opacity control | Low | Medium |
| 19 | Snap to screen edges | Low | Medium |
| 20 | Paste button in wizard | Low | High |
| 21 | Global hotkey show/hide | Medium | Medium |
| 22 | Usage rate / "safe to go" | Medium | High |
| 23 | Multiple account profiles | Medium | High |
| 24 | Webhook on threshold | Medium | Medium |
| 25 | Update checker | Medium | Medium |
| 26 | Adjustable bar height | Low | Low |
| 27 | Exportable usage report | Medium | Low |
| 28 | Second bar for message count | High | Medium |
| 29 | Session count today | Medium | High |
| 30 | Plan / limit auto-detection | Medium | Medium |
| 31 | Adaptive (P90) threshold suggestion | High | Medium |
