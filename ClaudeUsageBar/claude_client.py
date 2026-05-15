# claude_client.py
# Handles all HTTP communication with the claude.ai website. Provides stateless helper
# functions to fetch the user's organisation list and current usage data, using the
# browser session cookie for authentication.

import uuid as _uuid

import requests
from datetime import datetime
from typing import Optional, Tuple

# BASE and _HEADERS
# The root URL and HTTP request headers that mimic a real browser visit. Claude.ai
# checks these headers, so they must look like a normal Chrome browser request.
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


# AuthError
# A custom exception raised whenever the server returns a 401 or 403 status code,
# signalling that the session key is missing, wrong, or has expired.
class AuthError(Exception):
    pass


# _session
# Builds a pre-configured requests.Session that carries the browser-like headers and
# injects the sessionKey cookie so every request is authenticated automatically.
def _session(session_key: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    s.cookies.set("sessionKey", session_key, domain="claude.ai")
    return s


# get_organizations
# Calls the claude.ai organisations endpoint and returns the list of organisations the
# session key has access to. Raises AuthError if the key is invalid, or a standard
# requests exception if the network call fails.
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


# get_usage
# Fetches the raw usage JSON for the given organisation from the claude.ai API. The
# returned dict contains the five-hour window data that parse_usage then extracts.
def get_usage(session_key: str, org_id: str) -> dict:
    r = _session(session_key).get(
        f"{BASE}/api/organizations/{org_id}/usage", timeout=10
    )
    if r.status_code in (401, 403):
        raise AuthError("Session key invalid or expired")
    r.raise_for_status()
    return r.json()


def create_conversation(session_key: str, org_id: str) -> str:
    """Creates a new claude.ai conversation and returns its UUID."""
    conv_id = str(_uuid.uuid4())
    r = _session(session_key).post(
        f"{BASE}/api/organizations/{org_id}/chat_conversations",
        json={"uuid": conv_id, "name": ""},
        timeout=30,
    )
    if r.status_code in (401, 403):
        raise AuthError("Session key invalid or expired")
    r.raise_for_status()
    return conv_id


def delete_conversation(session_key: str, org_id: str, conv_id: str) -> None:
    """Deletes a conversation so session-trigger chats don't appear in history."""
    r = _session(session_key).delete(
        f"{BASE}/api/organizations/{org_id}/chat_conversations/{conv_id}",
        timeout=30,
    )
    r.raise_for_status()


def send_session_trigger(session_key: str, org_id: str, prompt: str = "Hi") -> None:
    """Creates a conversation, sends prompt to activate the 5-hour session, then deletes it."""
    conv_id = create_conversation(session_key, org_id)
    try:
        r = _session(session_key).post(
            f"{BASE}/api/organizations/{org_id}/chat_conversations/{conv_id}/completion",
            json={
                "prompt": prompt,
                "timezone": "Europe/London",
                "attachments": [],
                "files": [],
            },
            headers={"accept": "text/event-stream"},
            stream=True,
            timeout=30,
        )
        if r.status_code in (401, 403):
            raise AuthError("Session key invalid or expired")
        r.raise_for_status()
        r.raw.read(2048)
        r.close()
    finally:
        try:
            delete_conversation(session_key, org_id, conv_id)
        except Exception:
            pass


# parse_usage
# Extracts the two values the app actually needs from the raw usage dictionary:
# the current utilisation as a 0–100 float, and the UTC datetime when the five-hour
# window resets. Returns None for reset_at if the value is absent or unparseable.
def parse_usage(usage: dict) -> Tuple[float, Optional[datetime]]:
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
