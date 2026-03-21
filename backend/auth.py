from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

import bcrypt
import jwt
from dotenv import load_dotenv
from flask import request

load_dotenv()
# Also support a backend-local .env for app-specific settings
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

T = TypeVar("T")


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("Missing JWT_SECRET in environment/.env")
    return secret


def _expires_minutes() -> int:
    raw = os.getenv("JWT_EXPIRES_MINUTES", "10080").strip()
    try:
        return int(raw)
    except ValueError:
        return 10080


def hash_password(password: str) -> str:
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(*, user_id: str, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=_expires_minutes())

    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, _jwt_secret(), algorithm="HS256")
    # pyjwt can return bytes depending on version
    return token.decode("utf-8") if isinstance(token, (bytes, bytearray)) else token


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])


def get_bearer_token() -> Optional[str]:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def require_auth(expected_roles: Optional[Tuple[str, ...]] = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Flask decorator: verifies JWT and injects `request.user` dict.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            token = get_bearer_token()
            if not token:
                from flask import jsonify

                return jsonify({"error": "Missing Authorization token", "success": False}), 401
            try:
                decoded = decode_token(token)
            except jwt.ExpiredSignatureError:
                from flask import jsonify

                return jsonify({"error": "Token expired", "success": False}), 401
            except jwt.InvalidTokenError:
                from flask import jsonify

                return jsonify({"error": "Invalid token", "success": False}), 401

            role = decoded.get("role")
            if expected_roles and role not in expected_roles:
                from flask import jsonify

                return jsonify({"error": "Forbidden", "success": False}), 403

            # Attach to request for downstream handlers
            from flask import g

            g.user = {
                "id": decoded.get("sub"),
                "username": decoded.get("username"),
                "role": role,
            }
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator

