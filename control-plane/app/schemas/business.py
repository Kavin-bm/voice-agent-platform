import uuid

from pydantic import BaseModel, ConfigDict


class BusinessCreate(BaseModel):
    name: str
    structured_config: dict = {}
    default_transfer_number: str | None = None


class BusinessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    structured_config: dict
    default_transfer_number: str | None
