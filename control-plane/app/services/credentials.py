import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret
from app.models.credential import ProviderType, TenantProviderCredential


async def get_credential(
    db: AsyncSession, tenant_id: uuid.UUID, provider_type: ProviderType, provider_name: str
) -> dict | None:
    result = await db.execute(
        select(TenantProviderCredential).where(
            TenantProviderCredential.tenant_id == tenant_id,
            TenantProviderCredential.provider_type == provider_type,
            TenantProviderCredential.provider_name == provider_name,
        )
    )
    credential = result.scalar_one_or_none()
    if credential is None:
        return None
    return json.loads(decrypt_secret(credential.encrypted_credentials))
