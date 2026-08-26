from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import Timestamped, UUIDPk


class Tenant(Base, UUIDPk, Timestamped):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)

    # This tenant's Dograh organization, provisioned via /auth/signup + a
    # service API key (see dograh_client.py). The one Dograh-shaped field on
    # a core model: it's the tenant<->runtime mapping itself, not business
    # data, and every other Dograh integration detail stays out of app/models.
    dograh_org_encrypted_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
