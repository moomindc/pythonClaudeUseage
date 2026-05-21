# Security Review Report
## Claude Usage Bar Application

**Review Date:** 2026-05-20  
**Scope:** Python source code for Claude Usage Bar (Windows desktop application)  
**Severity Levels:** Critical, High, Medium, Low

---

## Executive Summary

The Claude Usage Bar application handles sensitive authentication credentials (Claude.ai session keys) but stores and manages them with insufficient security protections. **The primary concern is plaintext credential storage**, which could allow local attackers to extract session keys. Additionally, several supporting security issues increase the risk surface.

**Overall Risk Level:** **HIGH** — Immediate action required for credential storage.

---

## Critical Issues

### 1. **Plaintext Session Key Storage**
**Severity:** CRITICAL  
**Location:** `config.py:13-14`, `config.json` in `%APPDATA%\ClaudeUsageBar\`  
**Description:**  
The session key (e.g., `sk-ant-sid01-...`) is stored unencrypted in `config.json`, a plaintext JSON file in the AppData folder. Any process running with user privileges can read this file and extract the credential.

**Risk Impact:**
- Local privilege escalation/lateral movement attacks
- Credential theft by malware or other user-installed software
- Session key exposed if the AppData folder is backed up or synced unencrypted
- No protection if the user's computer is compromised

**Recommendation:**
1. **Encrypt the session key** using Windows DPAPI (`cryptography.fernet` or `win32crypt`) or a similar mechanism
2. **Store only encrypted credentials** in the config file
3. **Never log the session key** (currently OK — not found in logs, but verify)
4. Consider using Windows Credential Manager (`python-keyring`) for credential storage:
   ```python
   import keyring
   keyring.set_password("ClaudeUsageBar", "session_key", session_key)
   session_key = keyring.get_password("ClaudeUsageBar", "session_key")
   ```

---

### 2. **No Validation of Session Key Format**
**Severity:** CRITICAL (Chained with Issue #1)  
**Location:** `wizard.py:148-175`  
**Description:**  
The wizard accepts any string as a session key without validating format. While this allows flexibility, combined with plaintext storage, it means invalid/corrupted credentials are stored unencrypted.

**Recommendation:**
1. Validate that the session key matches the expected format (`sk-ant-sid01-.*`) before saving:
   ```python
   if not key.startswith("sk-ant-sid01-"):
       self._status.setText("Invalid session key format. Must start with 'sk-ant-sid01-'")
       self._test_btn.setEnabled(True)
       return
   ```
2. This provides early detection of user error and prevents storage of garbage data.

---

## High Issues

### 3. **Missing File Permissions on Config File**
**Severity:** HIGH  
**Location:** `config.py:72-75`  
**Description:**  
The config file is created with default permissions, which on Windows may allow other users on the system (depending on NTFS ACLs) or processes with user privileges to read it.

**Recommendation:**
1. Set restrictive file permissions after creating the config file:
   ```python
   import os
   import stat
   
   def save(cfg: dict) -> None:
       CONFIG_DIR.mkdir(parents=True, exist_ok=True)
       with open(CONFIG_FILE, "w", encoding="utf-8") as f:
           json.dump(cfg, f, indent=2)
       # Restrict to owner only (Windows: remove inheritance, grant owner Full Control only)
       os.chmod(CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)
   ```

2. On Windows, consider using `os.chmod()` with restricted mode, or use the `win32security` module to explicitly set ACLs.

---

### 4. **No Certificate Pinning or Hostname Verification Override**
**Severity:** HIGH  
**Location:** `claude_client.py:39-75`  
**Description:**  
The `requests.Session` relies on the standard certificate chain validation. While Python's `requests` library validates HTTPS by default, there is no additional protection against:
- Man-in-the-middle (MITM) attacks on networks with compromised CAs
- DNS hijacking that resolves `claude.ai` to an attacker-controlled IP
- Downgrade attacks (though HTTPS Strict-Transport-Security headers help)

**Recommendation:**
1. Implement certificate pinning for `claude.ai`:
   ```python
   import requests
   from requests.adapters import HTTPAdapter
   from urllib3.util.ssl_ import create_urllib3_context
   
   class PinningAdapter(HTTPAdapter):
       def init_poolmanager(self, *args, **kwargs):
           ctx = create_urllib3_context()
           ctx.check_hostname = True
           # Pin the public key hash of claude.ai's certificate
           super().init_poolmanager(*args, **kwargs)
   
   s = requests.Session()
   s.mount("https://", PinningAdapter())
   ```

2. Or use a library like `certifi` with pinning:
   - Monitor claude.ai's certificate changes
   - Update pinning logic when certificates rotate

---

### 5. **Detailed Error Messages Disclosing Sensitive Information**
**Severity:** HIGH  
**Location:** `wizard.py:160-186`, `claude_client.py:50-75`  
**Description:**  
Error messages returned to the user may leak sensitive details:
- The response structure from the organizations endpoint is shown in line 170
- Exception tracebacks could expose internal paths or API response bodies

**Example (wizard.py:170):**
```python
f"Got: {list(org.keys())}"  # Exposes API response structure
```

**Recommendation:**
1. Log detailed errors server-side only; show generic messages to users:
   ```python
   try:
       # ... API call ...
   except Exception as exc:
       log.error("Org lookup failed: %s", exc, exc_info=True)  # Log details
       raise ValueError("Unable to retrieve organization. Please check your session key.")  # Generic user message
   ```

2. Never include API response structures or full exception details in user-facing dialogs.

---

### 6. **No Rate Limiting on Polling Requests**
**Severity:** HIGH  
**Location:** `main.py:154-192`, `claude_client.py:50-75`  
**Description:**  
The polling mechanism (`_spawn_fetch`) makes unprotected requests to `claude.ai` at user-configurable intervals. There is no:
- Exponential backoff on repeated failures
- Rate limit detection (HTTP 429 responses are not handled)
- Throttling if the network is unavailable

An attacker could modify the app or the config to hammer the claude.ai API, potentially:
- Triggering account lockout
- Getting the session key rate-limited or revoked
- Causing a denial of service

**Recommendation:**
1. Implement exponential backoff:
   ```python
   def _spawn_fetch(self) -> None:
       # On auth error or repeated failures, increase interval
       # Reset interval on success
   ```

2. Handle HTTP 429 (Too Many Requests) responses:
   ```python
   if r.status_code == 429:
       retry_after = int(r.headers.get("Retry-After", 60))
       log.warning("Rate limited. Retrying after %ds", retry_after)
       # Pause polling
   ```

3. Set a minimum polling interval to prevent hammering (already hardcoded to 90 seconds at 90%+ usage, which is good).

---

## Medium Issues

### 7. **Insecure Handling of Triple Session Trigger Prompt**
**Severity:** MEDIUM  
**Location:** `main.py:236-244`, `settings_dialog.py:152-180`  
**Description:**  
The "triple session" feature sends a user-supplied prompt to claude.ai to trigger a new session. The prompt is:
- Stored unencrypted in config alongside the session key
- Not validated for length, format, or content
- Could be exploited if an attacker modifies the config file to:
  - Send malicious prompts
  - Exfiltrate data via the prompt text
  - Cause unintended side effects in the Claude.ai session

**Example vulnerability:**
```python
# In settings_dialog.py, prompt is stored as-is:
ts["prompt"] = self._triple_prompt.text().strip() or "Hi"

# Then sent to claude.ai without validation in main.py:
claude_client.send_session_trigger(key, org, prompt)
```

**Recommendation:**
1. Add length and content validation:
   ```python
   def _save(self) -> None:
       prompt = self._triple_prompt.text().strip() or "Hi"
       if len(prompt) > 100:
           # Show error
           return
       if any(char in prompt for char in ["\x00", "\r", "\n"]):
           # Reject control characters
           return
       ts["prompt"] = prompt
   ```

2. Consider disallowing the feature entirely if the prompt can be exploited (e.g., used to send PII).

3. Log all prompts sent (without storing them permanently) for audit purposes.

---

### 8. **No Timeout on Session Trigger Request**
**Severity:** MEDIUM  
**Location:** `claude_client.py:101-126`  
**Description:**  
The `send_session_trigger` function sets `timeout=30`, which is reasonable, but:
- The streaming response (`stream=True, headers={"accept": "text/event-stream"}`) reads only 2048 bytes and closes
- If the stream never provides data, the 30-second timeout will hang the background thread
- The `finally` block silently swallows all exceptions from `delete_conversation`, including timeouts

**Example issue:**
```python
try:
    # ... streaming request ...
    r.raw.read(2048)  # May hang if server never sends 2048 bytes
finally:
    try:
        delete_conversation(...)  # Silently fails if timeout occurs
    except Exception:
        pass
```

**Recommendation:**
1. Add per-operation timeouts:
   ```python
   r.raw.read(2048) if r.raw else None  # Check if stream exists
   ```

2. Log skipped deletions:
   ```python
   except Exception as exc:
       log.warning("Failed to delete conversation %s: %s", conv_id, exc)
   ```

3. Consider using `requests.Response.iter_bytes()` with explicit timeout:
   ```python
   for chunk in r.iter_bytes(chunk_size=2048):
       break  # Read first chunk and stop
   ```

---

### 9. **No HTTPS Strict-Transport-Security Validation**
**Severity:** MEDIUM  
**Location:** `claude_client.py:39-75`  
**Description:**  
The app does not verify or enforce HSTS (HTTP Strict-Transport-Security) headers from claude.ai responses. A network-level attacker could potentially downgrade the first request to HTTP (though modern browsers and libraries block this).

**Recommendation:**
1. Validate HSTS header in responses:
   ```python
   hsts = r.headers.get("Strict-Transport-Security")
   if not hsts or "max-age" not in hsts:
       log.warning("Missing or weak HSTS header from claude.ai")
   ```

2. Consider failing requests without HSTS if security requirements demand it.

---

### 10. **Unprotected Background Thread Access to Config**
**Severity:** MEDIUM  
**Location:** `main.py:284-303`, `bar_window.py:269-276`  
**Description:**  
Multiple threads access the `self._cfg` dictionary:
- `_fetch()` reads `session_key` and `org_id` in a background thread
- `mouseReleaseEvent()` in the UI thread writes to `window` config
- `_on_reconfigure()` reloads config in the UI thread

While Python's GIL provides some protection for dict operations, there's no explicit synchronization. If the config is being read by the fetch thread while being written, the behavior is undefined.

**Recommendation:**
1. Add a threading lock:
   ```python
   import threading
   
   class App:
       def __init__(self):
           self._cfg_lock = threading.RLock()
           self._cfg = cfg_mod.load()
       
       def _fetch(self):
           with self._cfg_lock:
               key = self._cfg.get("session_key", "")
               org = self._cfg.get("org_id", "")
       
       def _on_data(self, ...):
           with self._cfg_lock:
               if self._bar:
                   self._bar.set_data(...)
   ```

---

## Low Issues

### 11. **Bare Exception Handlers**
**Severity:** LOW  
**Location:** `claude_client.py:123-126`, `notifier.py` (no logging on failure)  
**Description:**  
Some exception handlers catch `Exception` or bare `except:` without logging, making debugging harder:

```python
finally:
    try:
        delete_conversation(session_key, org_id, conv_id)
    except Exception:
        pass  # Silently fails — no logging
```

**Recommendation:**
Log failures:
```python
except Exception as exc:
    log.warning("Failed to clean up conversation: %s", exc)
```

---

### 12. **No Metadata on Session Key Cookie**
**Severity:** LOW  
**Location:** `claude_client.py:39-43`  
**Description:**  
The session key is injected as a cookie manually:
```python
s.cookies.set("sessionKey", session_key, domain="claude.ai")
```

This works, but doesn't explicitly set `secure=True` or other cookie attributes. While the library defaults are reasonable, explicit settings improve clarity and defensive programming.

**Recommendation:**
```python
s.cookies.set(
    "sessionKey", session_key, 
    domain="claude.ai",
    secure=True,  # Only send over HTTPS
    httponly=True,  # Not accessible to JavaScript (N/A for desktop, but good practice)
)
```

---

### 13. **Magic Numbers in Power Event Filter**
**Severity:** LOW (Code quality)  
**Location:** `main.py:59-70`  
**Description:**  
Windows event constants are defined but not sourced or verified:
```python
_WM_POWERBROADCAST = 0x0218
_PBT_APMRESUMEAUTOMATIC = 0x0012
```

These are correct per Windows API docs, but no comment or source is provided. If incorrect, the power filter silently fails to detect resume events.

**Recommendation:**
Add a comment with the Windows API reference:
```python
# Windows API constants (https://docs.microsoft.com/en-us/windows/win32/power/power-management-best-practices)
_WM_POWERBROADCAST = 0x0218  # WM_POWERBROADCAST
_PBT_APMRESUMEAUTOMATIC = 0x0012  # PBT_APMRESUMEAUTOMATIC
```

---

## Summary Table

| Issue | Severity | Category | Effort to Fix |
|-------|----------|----------|---|
| Plaintext session key storage | CRITICAL | Cryptography | Medium |
| No session key format validation | CRITICAL | Input validation | Low |
| Missing file permissions on config | HIGH | File security | Low |
| No certificate pinning | HIGH | TLS/HTTPS | Medium |
| Detailed error messages | HIGH | Information disclosure | Low |
| No rate limiting | HIGH | API security | Medium |
| Insecure triple session prompt | MEDIUM | Data validation | Low |
| No timeout on streaming response | MEDIUM | Resource management | Low |
| No HSTS validation | MEDIUM | HTTPS hardening | Low |
| Unprotected multi-thread config access | MEDIUM | Thread safety | Medium |
| Bare exception handlers | LOW | Logging | Low |
| No explicit cookie attributes | LOW | Code clarity | Low |
| Magic numbers in constants | LOW | Code documentation | Low |

---

## Recommended Implementation Order

1. **Immediate (Week 1):**
   - Encrypt session key using Windows DPAPI or keyring (Issue #1)
   - Add session key format validation (Issue #2)
   - Set restrictive file permissions on config (Issue #3)

2. **Short-term (Week 2-3):**
   - Improve error messages and logging (Issue #5)
   - Add rate limiting and backoff (Issue #6)
   - Add thread safety to config access (Issue #10)

3. **Medium-term (Week 4-6):**
   - Implement certificate pinning (Issue #4)
   - Add input validation for triple session prompt (Issue #7)
   - Improve exception handling (Issue #11)

4. **Long-term:**
   - Add explicit cookie attributes (Issue #12)
   - Improve code documentation (Issue #13)

---

## Testing Recommendations

After fixing these issues, perform:
1. **Security testing:**
   - Verify encrypted credentials are not readable with standard tools
   - Confirm file permissions prevent other users from accessing config
   - Test certificate pinning blocks invalid certificates

2. **Functional testing:**
   - Ensure session key validation doesn't reject valid keys
   - Verify rate limiting doesn't interrupt normal polling
   - Test thread safety with concurrent config reads/writes

3. **Log review:**
   - Audit logs to ensure no session keys or sensitive data is logged
   - Verify error messages are user-friendly but don't expose internals

---

## Conclusion

The Claude Usage Bar application handles sensitive credentials with insufficient protection. The **critical finding of plaintext session key storage** must be addressed immediately, as it defeats all other security measures. Implementing credential encryption and validation, file permissions, and improved error handling will substantially improve the security posture.

**Estimated effort:** 4-6 weeks of development and testing for all recommendations.
