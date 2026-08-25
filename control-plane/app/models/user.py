import enum

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class UserRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class User(Base, UUIDPk, Timestamped, TenantScoped):
    __tablename__ = "users"

    # Globally unique, not per-tenant: login is by email+password alone (no
    # tenant/org selector in MVP — the agency operator is the primary user).
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.member)
