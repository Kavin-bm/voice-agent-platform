import uuid

from pydantic import BaseModel, ConfigDict


class PhoneNumberCreate(BaseModel):
    number: str
    provider: str


class PhoneNumberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    provider: str
    bound_agent_version_id: uuid.UUID | None


class PhoneNumberBind(BaseModel):
    agent_version_id: uuid.UUID
