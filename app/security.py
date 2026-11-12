"""JWT authentication and role-based authorization."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

ROLES = {"admin": ["admin"], "analyst": ["analyst"], "operator": ["operator"]}


@lru_cache
def _password_hash() -> bytes:
    """Demo users share one bcrypt-hashed password; a real deployment would use an identity provider."""
    return bcrypt.hashpw(get_settings().demo_password.encode(), bcrypt.gensalt())


def authenticate(username: str, password: str) -> list[str] | None:
    roles = ROLES.get(username)
    if roles is None or not bcrypt.checkpw(password.encode(), _password_hash()):
        return None
    return roles


def create_token(username: str, roles: list[str]) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {"sub": username, "roles": roles, "iat": now,
               "exp": now + timedelta(minutes=settings.jwt_ttl_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"}) from exc


def current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return decode_token(token)


def require_roles(*allowed: str) -> Callable[[dict], dict]:
    """Dependency factory: admin can always pass; otherwise the user needs one of `allowed`."""

    def checker(user: dict = Depends(current_user)) -> dict:
        roles = set(user.get("roles", []))
        if "admin" not in roles and not roles.intersection(allowed):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return checker
