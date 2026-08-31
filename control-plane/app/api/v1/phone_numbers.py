import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.models.agent import AgentVersion, AgentVersionStatus
from app.models.credential import ProviderType, TenantProviderCredential
from app.models.phone_number import PhoneNumber
from app.models.tenant import Tenant
from app.schemas.phone_number import PhoneNumberBind, PhoneNumberCreate, PhoneNumberRead
from app.services.dograh_client import ensure_telephony_configured, sync_phone_number

router = APIRouter(prefix="/phone-numbers", tags=["phone-numbers"])


@router.post("", response_model=PhoneNumberRead, status_code=status.HTTP_201_CREATED)
async def create_phone_number(
    body: PhoneNumberCreate,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PhoneNumberRead:
    """Registers a number this tenant owns on their telephony provider. Just
    our own record at this point — bind_phone_number below is what actually
    pushes it to Dograh, since that's the step that needs a published
    version to point it at."""
    number = PhoneNumber(
        tenant_id=tenant_id, number=body.number, provider=body.provider, country_code=body.country_code
    )
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
    one, which is still intact (see Agent versioning in the plan).

    Also the first point this number ever reaches Dograh: pushes the
    tenant's stored credential for number.provider as a Dograh telephony
    configuration (idempotent, cached on the credential row), then
    creates/updates the number there with inbound_workflow_id set to this
    version's workflow — which for Plivo also rewires the Plivo
    Application's answer_url, so no manual step is needed on the provider's
    own console."""
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

    tenant = await db.get(Tenant, tenant_id)
    credential = (
        await db.execute(
            select(TenantProviderCredential).where(
                TenantProviderCredential.tenant_id == tenant_id,
                TenantProviderCredential.provider_type == ProviderType.telephony,
                TenantProviderCredential.provider_name == number.provider,
            )
        )
    ).scalar_one_or_none()
    if credential is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No {number.provider} telephony credential on file for this tenant — add one first",
        )

    telephony_config_id = await ensure_telephony_configured(db, tenant, credential)
    await sync_phone_number(db, tenant, telephony_config_id, number, version.dograh_workflow_id)

    number.bound_agent_version_id = version.id
    await db.commit()
    await db.refresh(number)
    return number
