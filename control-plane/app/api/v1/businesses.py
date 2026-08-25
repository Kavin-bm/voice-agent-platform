import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessRead

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
async def create_business(
    body: BusinessCreate,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessRead:
    business = Business(tenant_id=tenant_id, **body.model_dump())
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return business


@router.get("", response_model=list[BusinessRead])
async def list_businesses(
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BusinessRead]:
    result = await db.execute(select(Business).where(Business.tenant_id == tenant_id))
    return list(result.scalars().all())


@router.get("/{business_id}", response_model=BusinessRead)
async def get_business(
    business_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessRead:
    business = await db.get(Business, business_id)
    if business is None or business.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business
