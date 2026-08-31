"""The ONLY module that talks to Dograh over HTTP. Everything above this
layer (agent_compiler, the API routers) works in our neutral compiled_spec;
this module and providers/adapters/dograh.py are what translate that into
Dograh API calls, so a future runtime swap touches only these two files.

Auth: signs up one local Dograh user per tenant (auto-bootstraps their org)
and logs in on demand — deliberately NOT using Dograh's /user/service-keys,
which is backed by their hosted MPS rather than the local DB (see the
plan's architecture-pivot correction).

Verification status: workflow/tool creation calls below are built from
Dograh's actual Pydantic schemas (runtime/dograh/api/services/workflow/dto.py,
schemas/tool.py) — high confidence. Org-level STT/LLM/TTS provider
configuration is NOT implemented here yet: it needs the exact
OrganizationAIModelConfigurationV2 field shape confirmed against a running
Dograh instance before first real use, not guessed.
"""

import json
import secrets

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.models.credential import TenantProviderCredential
from app.models.phone_number import PhoneNumber
from app.models.tenant import Tenant
from app.providers.adapters.dograh import build_tool_definitions, build_workflow_definition

settings = get_settings()


class DograhClientError(RuntimeError):
    pass


class _RaisingClient:
    """Wraps httpx so every call site gets DograhClientError uniformly —
    connection failures included — instead of the FastAPI default 500 with
    a raw stack trace. Dograh being unreachable is the single most likely
    real-world failure here and deserves a clear message, not a traceback."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=settings.dograh_base_url, timeout=30)

    async def __aenter__(self) -> "_RaisingClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self._client.__aexit__(*exc_info)

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            response = await self._client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise DograhClientError(f"Dograh runtime unreachable at {settings.dograh_base_url}: {exc}") from exc
        if response.is_error:
            raise DograhClientError(f"Dograh API {method} {url} -> {response.status_code}: {response.text}")
        return response

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)


def _client() -> _RaisingClient:
    return _RaisingClient()


async def ensure_tenant_provisioned(db: AsyncSession, tenant: Tenant) -> None:
    """Idempotent: signs up a Dograh user for this tenant the first time
    only. Dograh auto-bootstraps an organization on signup — no separate
    org-creation call needed."""
    if tenant.dograh_email:
        return

    # Dograh's signup validates email syntax including a reserved/special-use
    # TLD check — .local, .test, .example, .invalid all get rejected even
    # though nothing ever actually emails this address.
    email = f"tenant-{tenant.slug}@tenants.voiceagentplatform.com"
    password = secrets.token_urlsafe(24)

    async with _client() as client:
        await client.post(
            "/api/v1/auth/signup",
            json={"email": email, "password": password, "name": tenant.name},
        )

    tenant.dograh_email = email
    tenant.dograh_encrypted_password = encrypt_secret(password)
    await db.commit()


async def _login(tenant: Tenant) -> str:
    if not tenant.dograh_email or not tenant.dograh_encrypted_password:
        raise DograhClientError(f"Tenant {tenant.id} has no Dograh account provisioned yet")

    password = decrypt_secret(tenant.dograh_encrypted_password)
    async with _client() as client:
        response = await client.post(
            "/api/v1/auth/login", json={"email": tenant.dograh_email, "password": password}
        )
        return response.json()["token"]


async def _create_tool(client: "_RaisingClient", token: str, tool_def: dict) -> str:
    response = await client.post(
        "/api/v1/tools/", json=tool_def, headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()["tool_uuid"]


async def _create_workflow(client: "_RaisingClient", token: str, name: str, definition: dict) -> int:
    response = await client.post(
        "/api/v1/workflow/create/definition",
        json={"name": name, "workflow_definition": definition},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()["id"]


async def publish_compiled_spec(
    db: AsyncSession, tenant: Tenant, agent_name: str, agent_version_id: str, compiled_spec: dict
) -> str:
    """Pushes a compiled_spec to Dograh as a workflow. Returns the Dograh
    workflow id (stored as AgentVersion.dograh_workflow_id by the caller).

    POST /workflow/create/definition publishes immediately — version 1 comes
    back with status "published" already (confirmed against a live Dograh
    instance: GET .../versions shows published_at set on creation) — so
    there's no separate publish call to make; hitting /workflow/{id}/publish
    afterward 400s with "No draft to publish" since nothing is pending.

    Tools referenced by the spec are (re)created fresh each call — see
    build_tool_definitions for why. Republishing likewise creates a new
    Dograh workflow rather than updating the old one in place; acceptable
    for MVP, revisit if orphaned workflows become a real cleanup problem."""

    await ensure_tenant_provisioned(db, tenant)
    token = await _login(tenant)

    async with _client() as client:
        tool_uuids = [
            await _create_tool(client, token, tool_def)
            for tool_def in build_tool_definitions(compiled_spec)
        ]

        definition = build_workflow_definition(compiled_spec, tool_uuids, agent_version_id)
        workflow_id = await _create_workflow(client, token, agent_name, definition)

    return str(workflow_id)


async def create_dograh_campaign(
    tenant: Tenant, name: str, dograh_workflow_id: str, csv_bytes: bytes
) -> str:
    """Uploads the lead CSV and creates the Dograh campaign in one call.
    Confirmed against source (routes/campaign.py, routes/s3_signed_url.py):
    campaigns take a CSV file reference (source_id = the presigned-upload
    file_key), not an inline lead list — phone_number column required,
    every other column becomes {{initial_context.*}} for the workflow.

    Dograh resolves telephony_configuration_id itself when omitted, but
    raises if the org has none configured at all — unverified past that
    point in this environment, since no real Exotel/Plivo account exists
    here to configure one (see the plan's telephony-binding gap)."""

    token = await _login(tenant)

    async with _client() as client:
        presign = await client.post(
            "/api/v1/s3/presigned-upload-url",
            json={"file_name": "leads.csv", "file_size": len(csv_bytes), "content_type": "text/csv"},
            headers={"Authorization": f"Bearer {token}"},
        )
        upload_url = presign.json()["upload_url"]
        file_key = presign.json()["file_key"]

        async with httpx.AsyncClient(timeout=30) as plain_client:
            put_response = await plain_client.put(
                upload_url, content=csv_bytes, headers={"Content-Type": "text/csv"}
            )
            put_response.raise_for_status()

        campaign = await client.post(
            "/api/v1/campaign/create",
            json={
                "name": name,
                "workflow_id": int(dograh_workflow_id),
                "source_type": "csv",
                "source_id": file_key,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        return str(campaign.json()["id"])


async def _campaign_action(tenant: Tenant, dograh_campaign_id: str, action: str) -> dict:
    token = await _login(tenant)
    async with _client() as client:
        response = await client.post(
            f"/api/v1/campaign/{dograh_campaign_id}/{action}",
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()


async def start_dograh_campaign(tenant: Tenant, dograh_campaign_id: str) -> dict:
    return await _campaign_action(tenant, dograh_campaign_id, "start")


async def pause_dograh_campaign(tenant: Tenant, dograh_campaign_id: str) -> dict:
    return await _campaign_action(tenant, dograh_campaign_id, "pause")


async def resume_dograh_campaign(tenant: Tenant, dograh_campaign_id: str) -> dict:
    return await _campaign_action(tenant, dograh_campaign_id, "resume")


async def get_dograh_campaign_progress(tenant: Tenant, dograh_campaign_id: str) -> dict:
    token = await _login(tenant)
    async with _client() as client:
        response = await client.get(
            f"/api/v1/campaign/{dograh_campaign_id}/progress",
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()


async def fetch_call_artifact(tenant: Tenant, url: str) -> str:
    """Fetches a recording/transcript URL from the webhook payload. Tries
    unauthenticated first (most likely a presigned MinIO URL, already
    signed) and falls back to the tenant's Dograh bearer token — unverified
    which of these Dograh actually uses, no real call has hit this yet."""

    async with httpx.AsyncClient(timeout=30) as plain_client:
        response = await plain_client.get(url)
        if response.status_code == 200:
            return response.text

    token = await _login(tenant)
    async with httpx.AsyncClient(timeout=30) as auth_client:
        response = await auth_client.get(url, headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        return response.text


async def ensure_telephony_configured(
    db: AsyncSession, tenant: Tenant, credential: TenantProviderCredential
) -> str:
    """Idempotent: pushes a tenant's stored telephony credential to Dograh
    as an organization-level telephony configuration the first time it's
    needed, returning Dograh's config id. Confirmed against source
    (routes/organization.py, services/telephony/providers/<name>/config.py):
    ``config`` is a discriminated union on ``provider`` carrying exactly the
    provider's own credential fields (e.g. Plivo wants auth_id/auth_token) —
    no separate account_id/secret split on our side, we just forward
    whatever the operator entered under that provider_name."""
    if credential.dograh_telephony_config_id:
        return credential.dograh_telephony_config_id

    token = await _login(tenant)
    creds = json.loads(decrypt_secret(credential.encrypted_credentials))

    async with _client() as client:
        response = await client.post(
            "/api/v1/organizations/telephony-configs",
            json={
                "name": f"{credential.provider_name}-{tenant.slug}",
                "config": {"provider": credential.provider_name, **creds},
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    credential.dograh_telephony_config_id = str(response.json()["id"])
    await db.commit()
    return credential.dograh_telephony_config_id


async def sync_phone_number(
    db: AsyncSession,
    tenant: Tenant,
    telephony_config_id: str,
    phone_number: PhoneNumber,
    dograh_workflow_id: str | None,
) -> str:
    """Creates this number on Dograh the first time (PUT on every rebind
    after), setting inbound_workflow_id so Dograh points the provider's
    inbound webhook at our published workflow. For Plivo specifically this
    also rewrites the Plivo Application's answer_url via Dograh's
    programmatic sync (services/telephony/providers/plivo — no manual
    console step on the provider's side). Returns Dograh's phone-number id."""
    token = await _login(tenant)
    inbound_workflow_id = int(dograh_workflow_id) if dograh_workflow_id else None

    async with _client() as client:
        if phone_number.dograh_phone_number_id:
            response = await client.put(
                f"/api/v1/organizations/telephony-configs/{telephony_config_id}"
                f"/phone-numbers/{phone_number.dograh_phone_number_id}",
                json={"inbound_workflow_id": inbound_workflow_id},
                headers={"Authorization": f"Bearer {token}"},
            )
        else:
            response = await client.post(
                f"/api/v1/organizations/telephony-configs/{telephony_config_id}/phone-numbers",
                json={
                    "address": phone_number.number,
                    "country_code": phone_number.country_code,
                    "inbound_workflow_id": inbound_workflow_id,
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    phone_number.dograh_phone_number_id = str(response.json()["id"])
    await db.commit()
    return phone_number.dograh_phone_number_id
