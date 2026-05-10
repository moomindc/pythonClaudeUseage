import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "ClaudeUsageBar"
CONFIG_FILE = CONFIG_DIR / "config.json"

_DEFAULTS: dict = {
    "session_key": None,
    "org_id": None,
    "poll_interval_minutes": 5,
    "window": {"x": None, "y": 10, "width": 153},
    "colors": {
        "fill": "#14532D",       # used-tokens portion of bar
        "background": "#030A05", # unused-tokens portion of bar
        "text": "#86EFAC",       # countdown and percentage text
    },
}


def load() -> dict:
    if not CONFIG_FILE.exists():
        return _deep_copy_defaults()
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        merged = _deep_copy_defaults()
        merged.update({k: v for k, v in data.items() if k not in ("window", "colors")})
        merged["window"] = {**_DEFAULTS["window"], **data.get("window", {})}
        merged["colors"] = {**_DEFAULTS["colors"], **data.get("colors", {})}
        return merged
    except Exception:
        return _deep_copy_defaults()


def save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def is_configured(cfg: dict) -> bool:
    return bool(cfg.get("session_key") and cfg.get("org_id"))


def _deep_copy_defaults() -> dict:
    d = dict(_DEFAULTS)
    d["window"] = dict(_DEFAULTS["window"])
    d["colors"] = dict(_DEFAULTS["colors"])
    return d
