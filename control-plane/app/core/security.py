from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(*, user_id: UUID, tenant_id: UUID, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": str(user_id), "tenant_id": str(tenant_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


class CurrentUser:
    """Decoded JWT identity. This — not a per-endpoint check — is what every
    tenant-scoped repository/query filters on, so a missed check anywhere
    still can't leak another tenant's rows (see Credentials & tenant
    isolation in the plan)."""

    def __init__(self, user_id: UUID, tenant_id: UUID, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> CurrentUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        role = payload.get("role")
        if user_id is None or tenant_id is None:
            raise credentials_error
    except JWTError as exc:
        raise credentials_error from exc
    return CurrentUser(user_id=UUID(user_id), tenant_id=UUID(tenant_id), role=role)


def get_current_tenant_id(user: Annotated[CurrentUser, Depends(get_current_user)]) -> UUID:
    return user.tenant_id


def require_platform_admin(x_admin_key: Annotated[str | None, Header()] = None) -> None:
    if x_admin_key != settings.platform_admin_api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin key required")
