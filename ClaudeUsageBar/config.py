# config.py
# Handles reading and writing the application configuration stored in the Windows AppData
# folder. Provides sensible defaults and merges them with any saved user preferences so
# missing keys never cause errors.

import json
import os
from pathlib import Path

# CONFIG_DIR and CONFIG_FILE
# The folder and file where settings are persisted on disk, typically:
# C:\Users\YourName\AppData\Roaming\ClaudeUsageBar\config.json
CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "ClaudeUsageBar"
CONFIG_FILE = CONFIG_DIR / "config.json"

# _DEFAULTS
# Factory-fresh settings used when no config file exists yet, or as a fallback for any
# keys that are missing from a saved config. Contains window position, bar colours, and
# the polling interval.
_DEFAULTS: dict = {
    "session_key": None,
    "org_id": None,
    "poll_interval_minutes": 5,
    "rag_mode": False,
    "window": {"x": None, "y": 10, "width": 123},
    "colors": {
        "fill": "#14532D",       # used-tokens portion of bar
        "background": "#030A05", # unused-tokens portion of bar
        "text": "#86EFAC",       # countdown and percentage text
    },
    "triple_session": {
        "enabled": False,
        "work_start": "07:00",   # HH:MM local time — first session trigger of the day
        "prompt": "Hi",          # message sent to claude.ai to activate each session
    },
}


# load
# Reads the config file from disk and merges it with the defaults so every key is always
# present. If the file does not exist or cannot be read, the pure defaults are returned
# so the app always gets a usable dictionary.
def load() -> dict:
    if not CONFIG_FILE.exists():
        return _deep_copy_defaults()
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        merged = _deep_copy_defaults()
        merged.update({k: v for k, v in data.items() if k not in ("window", "colors", "triple_session")})
        merged["window"] = {**_DEFAULTS["window"], **data.get("window", {})}
        merged["colors"] = {**_DEFAULTS["colors"], **data.get("colors", {})}
        merged["triple_session"] = {**_DEFAULTS["triple_session"], **data.get("triple_session", {})}
        return merged
    except Exception:
        return _deep_copy_defaults()


# save
# Writes the in-memory config dictionary to the JSON file on disk, creating the folder
# first if it does not exist yet.
def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# is_configured
# Returns True only when both a session_key and an org_id have been saved, which means
# the user has completed the setup wizard at least once.
def is_configured(cfg: dict) -> bool:
    return bool(cfg.get("session_key") and cfg.get("org_id"))


# _deep_copy_defaults
# Creates a fresh independent copy of the default settings. The nested dicts for
# 'window' and 'colors' are copied separately so editing them later does not accidentally
# mutate the original _DEFAULTS template.
def _deep_copy_defaults() -> dict:
    d = dict(_DEFAULTS)
    d["window"] = dict(_DEFAULTS["window"])
    d["colors"] = dict(_DEFAULTS["colors"])
    d["triple_session"] = dict(_DEFAULTS["triple_session"])
    return d
