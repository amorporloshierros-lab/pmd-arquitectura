"""
auth.py
-------
Sistema de autenticación para Mi Hogar PMD.

Provee:
  - hash_password / verify_password (bcrypt)
  - generate_random_token (URL-safe, para invites y password resets)
  - sign_session_token / verify_session_token (HMAC stateless)
  - extract_token_from_header (Authorization: Bearer ...)
"""

from __future__ import annotations

import base64
import hmac
import hashlib
import json
import logging
import os
import secrets
import time
from typing import Any

import bcrypt

logger = logging.getLogger("lucas.auth")

AUTH_SECRET = os.getenv("PMD_AUTH_SECRET", "dev-only-INSECURE-default-change-me")
SESSION_TTL_SECONDS = 24 * 60 * 60
INVITE_TTL_SECONDS = 24 * 60 * 60


def hash_password(plain: str) -> str:
    if not plain:
        raise ValueError("Password no puede estar vacia")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        logger.warning("verify_password: hash invalido (%s)", exc)
        return False


def generate_random_token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def sign_session_token(user_id: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    payload = {"user_id": user_id, "exp": int(time.time()) + ttl_seconds}
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode("ascii")
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: str) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig_b64 = token.split(".", 1)
    except ValueError:
        return None
    expected_sig = hmac.new(AUTH_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).digest()
    expected_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode("ascii")
    if not hmac.compare_digest(sig_b64, expected_b64):
        return None
    try:
        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)) or exp < time.time():
        return None
    if not payload.get("user_id"):
        return None
    return payload


def extract_token_from_header(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def authenticated_user_id(authorization: str | None) -> str | None:
    token = extract_token_from_header(authorization)
    if not token:
        return None
    payload = verify_session_token(token)
    if not payload:
        return None
    return payload.get("user_id")
