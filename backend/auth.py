"""
JWT authentication + password hashing + role-based access dependencies.

Only volunteers and control-room/admin staff ever log in -- pilgrims use the
app anonymously (see spec section 18). Passwords are always stored hashed
(bcrypt, used directly -- not via passlib, whose bcrypt backend has known
compatibility breaks against modern bcrypt releases), never in plain text.
"""
import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserRole

# In a real deployment this MUST come from an environment variable / secret
# manager. A fallback is provided so the demo runs out of the box.
SECRET_KEY = os.getenv("NAVIX_SECRET_KEY", "navix-dev-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours -- long enough for a field shift

# HTTPBearer (rather than OAuth2PasswordBearer) because /api/auth/login takes
# a plain JSON body, not an OAuth2 form -- this still shows a working
# "Authorize" button in /docs where a token from /api/auth/login can be
# pasted directly.
bearer_scheme = HTTPBearer(auto_error=False)

# bcrypt only hashes the first 72 bytes of a password -- truncate up front so
# hashing never raises on a long input instead of silently ignoring the rest.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    truncated = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(truncated, password_hash.encode("utf-8"))


def create_access_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user.id), "username": user.username, "role": user.role.value, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme), db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = _decode_token(credentials.credentials)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme), db: Session = Depends(get_db)
) -> Optional[User]:
    """Same as get_current_user but returns None instead of raising -- used
    on endpoints pilgrims can call anonymously but that behave slightly
    differently when an authenticated volunteer/admin calls them."""
    if not credentials:
        return None
    try:
        payload = _decode_token(credentials.credentials)
    except HTTPException:
        return None
    return db.query(User).filter(User.id == int(payload["sub"])).first()


def require_volunteer(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.volunteer, UserRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Volunteer access required")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Control-room/admin access required")
    return user
