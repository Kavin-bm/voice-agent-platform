import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt_secret
from app.core.db import get_db
from app.core.security import get_current_tenant_id
from app.models.credential import TenantProviderCredential
from app.schemas.credential import CredentialCreate, CredentialRead

router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.post("", response_model=CredentialRead, status_code=status.HTTP_201_CREATED)
async def create_credential(
    body: CredentialCreate,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CredentialRead:
    credential = TenantProviderCredential(
        tenant_id=tenant_id,
        provider_type=body.provider_type,
        provider_name=body.provider_name,
        encrypted_credentials=encrypt_secret(json.dumps(body.credentials)),
        is_default=body.is_default,
    )
    db.add(credential)
    await db.commit()
    await db.refresh(credential)
    return credential


@router.get("", response_model=list[CredentialRead])
async def list_credentials(
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CredentialRead]:
    result = await db.execute(
        select(TenantProviderCredential).where(TenantProviderCredential.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: uuid.UUID,
    tenant_id: Annotated[uuid.UUID, Depends(get_current_tenant_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    credential = await db.get(TenantProviderCredential, credential_id)
    if credential is None or credential.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    await db.delete(credential)
    await db.commit()
