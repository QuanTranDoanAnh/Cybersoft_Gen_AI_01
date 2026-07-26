import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Cookie, Depends, HTTPException, status
from pwdlib import PasswordHash

from . import store

COOKIE_NAME = "orbit_session"
JWT_SECRET = os.getenv("JWT_SECRET", "local-development-secret-change-me")
JWT_ALGORITHM = "HS256"
SESSION_HOURS = 8
password_hash = PasswordHash.recommended()


def authenticate(email: str, password: str) -> dict | None:
    user = store.get_user_by_email(email)
    if not user or not user["is_active"] or not password_hash.verify(password, user["password_hash"]):
        return None
    return user


def create_session_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": user["id"], "role": user["role"], "iat": now, "exp": now + timedelta(hours=SESSION_HOURS)}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def public_user(user: dict) -> dict:
    return {"id": user["id"], "email": user["email"], "full_name": user["full_name"], "role": user["role"]}


def get_current_user(orbit_session: str | None = Cookie(default=None)) -> dict:
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if not orbit_session:
        raise credentials_error
    try:
        payload = jwt.decode(orbit_session, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise credentials_error from exc
    user = store.get_user_by_id(str(payload.get("sub", "")))
    if not user or not user["is_active"]:
        raise credentials_error
    return user


def require_roles(*allowed_roles: str):
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return user
    return dependency
