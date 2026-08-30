import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.models.agent import AgentVersion, AgentVersionStatus
from app.models.phone_number import PhoneNumber
from app.schemas.phone_number import PhoneNumberBind, PhoneNumberCreate, PhoneNumberRead

router = APIRouter(prefix="/phone-numbers", tags=["phone-numbers"])


@router.post("", response_model=PhoneNumberRead, status_code=status.HTTP_201_CREATED)
async def create_phone_number(
    body: PhoneNumberCreate,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PhoneNumberRead:
    """Registers a number this tenant owns on their telephony provider.
    Doesn't provision anything on the provider or Dograh side yet — that
    needs Dograh's org-level telephony-config, which isn't wired in this
    pass (see the plan: unverified without a real Exotel/Plivo account to
    test against). This is the record we bind a published agent version to."""
    number = PhoneNumber(tenant_id=tenant_id, number=body.number, provider=body.provider)
    db.add(number)
    await db.commit()
    await db.refresh(number)
    return number


@router.get("", response_model=list[PhoneNumberRead])
async def list_phone_numbers(
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PhoneNumberRead]:
    result = await db.execute(select(PhoneNumber).where(PhoneNumber.tenant_id == tenant_id))
    return list(result.scalars().all())


@router.post("/{phone_number_id}/bind", response_model=PhoneNumberRead)
async def bind_phone_number(
    phone_number_id: uuid.UUID,
    body: PhoneNumberBind,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PhoneNumberRead:
    """Points a number at a published version. Swapping which version a
    number is bound to is the whole rollback mechanism — publish a new
    version, confirm it, then bind; roll back by re-binding the previous
    one, which is still intact (see Agent versioning in the plan)."""
    number = await db.get(PhoneNumber, phone_number_id)
    if number is None or number.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone number not found")

    version = await db.get(AgentVersion, body.agent_version_id)
    if version is None or version.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent version not found")
    if version.status != AgentVersionStatus.published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only a published version can be bound to a phone number",
        )

    number.bound_agent_version_id = version.id
    await db.commit()
    await db.refresh(number)
    return number
