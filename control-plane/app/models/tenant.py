from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import Timestamped, UUIDPk


class Tenant(Base, UUIDPk, Timestamped):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)

    # This tenant's Dograh organization. Provisioned via Dograh's local
    # /auth/signup (auto-bootstraps an org), not their service-key endpoint —
    # that's backed by Dograh's hosted MPS, not self-hosted (see the plan's
    # architecture-pivot note). dograh_client.py logs in on demand with these
    # and caches the short-lived JWT in-process; nothing else in the
    # codebase should read these fields directly.
    dograh_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    dograh_encrypted_password: Mapped[str | None] = mapped_column(Text, nullable=True)
