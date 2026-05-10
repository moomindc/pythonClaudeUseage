import requests
from datetime import datetime
from typing import Optional, Tuple

BASE = "https://claude.ai"

_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "accept": "application/json",
    "referer": "https://claude.ai/",
    "origin": "https://claude.ai",
}


class AuthError(Exception):
    pass


def _session(session_key: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    s.cookies.set("sessionKey", session_key, domain="claude.ai")
    return s


def get_organizations(session_key: str) -> list:
    r = _session(session_key).get(f"{BASE}/api/organizations", timeout=10)
    if r.status_code in (401, 403):
        raise AuthError("Session key invalid or expired")
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("organizations", "data", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def get_usage(session_key: str, org_id: str) -> dict:
    r = _session(session_key).get(
        f"{BASE}/api/organizations/{org_id}/usage", timeout=10
    )
    if r.status_code in (401, 403):
        raise AuthError("Session key invalid or expired")
    r.raise_for_status()
    return r.json()


def parse_usage(usage: dict) -> Tuple[float, Optional[datetime]]:
    """Return (utilization_pct 0–100, reset_at UTC datetime or None)."""
    five_hour = usage.get("five_hour") or {}
    pct = float(five_hour.get("utilization") or 0.0)
    reset_at: Optional[datetime] = None
    reset_str = five_hour.get("resets_at")
    if reset_str:
        try:
            reset_at = datetime.fromisoformat(reset_str)
        except ValueError:
            pass
    return pct, reset_at
