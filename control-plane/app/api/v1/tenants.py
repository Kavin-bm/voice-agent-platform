from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import hash_password, require_platform_admin
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.tenant import TenantCreate, TenantRead

router = APIRouter(prefix="/tenants", tags=["tenants"], dependencies=[Depends(require_platform_admin)])


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate, db: Annotated[AsyncSession, Depends(get_db)]
) -> TenantRead:
    tenant = Tenant(name=body.name, slug=body.slug)
    db.add(tenant)
    await db.flush()

    owner = User(
        tenant_id=tenant.id,
        email=body.owner_email,
        hashed_password=hash_password(body.owner_password),
        role=UserRole.owner,
    )
    db.add(owner)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(tenant_id: str, db: Annotated[AsyncSession, Depends(get_db)]) -> TenantRead:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant
