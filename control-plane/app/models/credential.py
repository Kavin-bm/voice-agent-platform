import enum

from sqlalchemy import Boolean, Enum, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TenantScoped, Timestamped, UUIDPk


class ProviderType(str, enum.Enum):
    telephony = "telephony"
    stt = "stt"
    llm = "llm"
    tts = "tts"


class TenantProviderCredential(Base, UUIDPk, Timestamped, TenantScoped):
    """BYOC/BYOK: each tenant supplies their own provider accounts. The
    platform never resells minutes in MVP (see plan: Credentials & tenant
    isolation) — this table just holds what a tenant's agents are allowed to
    call out with, encrypted at rest."""

    __tablename__ = "tenant_provider_credentials"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "provider_type", "provider_name", name="uq_tenant_provider"
        ),
    )

    provider_type: Mapped[ProviderType] = mapped_column(Enum(ProviderType, name="provider_type"))
    provider_name: Mapped[str] = mapped_column(String(50))  # e.g. "sarvam", "exotel", "gemini"
    encrypted_credentials: Mapped[str] = mapped_column(Text)  # Fernet ciphertext of a JSON blob
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # Set once this credential has been pushed to Dograh as a telephony
    # configuration (telephony credentials only) — caches the config id so
    # binding a second number doesn't re-create it on every call.
    dograh_telephony_config_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
