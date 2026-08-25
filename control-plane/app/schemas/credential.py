import uuid

from pydantic import BaseModel, ConfigDict

from app.models.credential import ProviderType


class CredentialCreate(BaseModel):
    provider_type: ProviderType
    provider_name: str
    credentials: dict  # plaintext in the request only; encrypted before storage
    is_default: bool = True


class CredentialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_type: ProviderType
    provider_name: str
    is_default: bool
