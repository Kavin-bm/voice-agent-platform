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

import secrets

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt_secret, encrypt_secret
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
    db: AsyncSession, tenant: Tenant, agent_name: str, compiled_spec: dict
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

        definition = build_workflow_definition(compiled_spec, tool_uuids)
        workflow_id = await _create_workflow(client, token, agent_name, definition)

    return str(workflow_id)
