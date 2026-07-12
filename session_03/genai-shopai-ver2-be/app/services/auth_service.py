import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services import account_service

load_dotenv()

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "change-me-in-production")
TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(60 * 60 * 24 * 7)))
HASH_ITERATIONS = 210_000

bearer_scheme = HTTPBearer(auto_error=False)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    return f"pbkdf2_sha256${HASH_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), _b64decode(salt), int(iterations))
        return hmac.compare_digest(_b64encode(digest), expected)
    except (ValueError, TypeError):
        return False


def _sign(value: str) -> str:
    signature = hmac.new(AUTH_SECRET_KEY.encode("utf-8"), value.encode("ascii"), hashlib.sha256).digest()
    return _b64encode(signature)


def create_access_token(user_id: str) -> str:
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode("utf-8"))
    payload = _b64encode(
        json.dumps(
            {
                "sub": user_id,
                "exp": int(time.time()) + TOKEN_TTL_SECONDS,
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )
    unsigned = f"{header}.{payload}"
    return f"{unsigned}.{_sign(unsigned)}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        header, payload, signature = token.split(".", 2)
        unsigned = f"{header}.{payload}"
        if not hmac.compare_digest(_sign(unsigned), signature):
            return None
        data = json.loads(_b64decode(payload))
        if int(data.get("exp", 0)) < int(time.time()):
            return None
        return data
    except (ValueError, json.JSONDecodeError, TypeError):
        return None


def register_user(email: str, password: str, display_name: str) -> dict:
    password_hash = hash_password(password)
    return account_service.create_user(email=email, display_name=display_name, password_hash=password_hash)


def authenticate_user(email: str, password: str) -> dict | None:
    user = account_service.get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return {
        "id": str(user["id"]),
        "email": user["email"],
        "display_name": user["display_name"],
    }


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bạn cần đăng nhập để dùng tính năng này.")

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.")

    user = account_service.get_user_by_id(str(payload["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không tồn tại.")
    return user
