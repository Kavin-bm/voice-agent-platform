import uuid

from pydantic import BaseModel, ConfigDict


class PhoneNumberCreate(BaseModel):
    number: str
    provider: str
    country_code: str | None = None


class PhoneNumberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    provider: str
    country_code: str | None
    dograh_phone_number_id: str | None
    bound_agent_version_id: uuid.UUID | None


class PhoneNumberBind(BaseModel):
    agent_version_id: uuid.UUID
