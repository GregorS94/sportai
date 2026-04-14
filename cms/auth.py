"""Minimal session auth for the CMS admin interface.

Uses an HMAC-signed cookie holding ``<username>:<issued_ts>``. Credentials are
read from environment variables so no user table is needed.
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Request, status

COOKIE_NAME = "cms_session"
SESSION_TTL = timedelta(hours=12)


def _secret_key() -> bytes:
    key = os.environ.get("CMS_SECRET_KEY", "")
    if not key:
        # Derive a deterministic fallback so dev mode still works, but warn.
        key = "insecure-default-change-me"
    return key.encode("utf-8")


def _admin_credentials() -> tuple[str, str]:
    user = os.environ.get("CMS_ADMIN_USER", "admin")
    password = os.environ.get("CMS_ADMIN_PASSWORD", "")
    return user, password


def verify_credentials(username: str, password: str) -> bool:
    admin_user, admin_pw = _admin_credentials()
    if not admin_pw:
        return False
    # Constant-time comparison to avoid timing leaks
    user_ok = hmac.compare_digest(username or "", admin_user)
    pw_ok = hmac.compare_digest(password or "", admin_pw)
    return user_ok and pw_ok


def _sign(payload: str) -> str:
    sig = hmac.new(_secret_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _unsign(token: str) -> Optional[str]:
    if not token or "." not in token:
        return None
    payload, _, sig = token.rpartition(".")
    expected = hmac.new(_secret_key(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return payload


def make_session_token(username: str) -> str:
    issued = int(datetime.utcnow().timestamp())
    nonce = secrets.token_hex(8)
    return _sign(f"{username}:{issued}:{nonce}")


def parse_session_token(token: str) -> Optional[str]:
    payload = _unsign(token or "")
    if not payload:
        return None
    try:
        username, issued_str, _nonce = payload.split(":", 2)
        issued_ts = int(issued_str)
    except (ValueError, TypeError):
        return None
    issued_at = datetime.utcfromtimestamp(issued_ts)
    if datetime.utcnow() - issued_at > SESSION_TTL:
        return None
    return username


def require_admin(request: Request) -> str:
    """FastAPI dependency – raises 401 if the caller is not logged in."""
    token = request.cookies.get(COOKIE_NAME, "")
    username = parse_session_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht eingeloggt",
        )
    return username


def optional_admin(request: Request) -> Optional[str]:
    token = request.cookies.get(COOKIE_NAME, "")
    return parse_session_token(token)
