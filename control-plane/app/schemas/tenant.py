import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class TenantCreate(BaseModel):
    name: str
    slug: str
    # Bootstraps the tenant's first user (owner) in the same call — an agency
    # operator provisions tenants, there's no self-serve signup in MVP.
    owner_email: EmailStr
    owner_password: str


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
