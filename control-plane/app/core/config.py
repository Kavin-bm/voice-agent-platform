from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    database_url: str = "postgresql+asyncpg://voice:voice@localhost:5432/control_plane"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    # Gates operator-only endpoints (create tenant, seed templates/vertical
    # packs) — there's no self-serve signup, the agency operator is the only
    # actor who should ever hit these. Simple shared-secret header, not a
    # full admin-user system: single-operator tool, not worth the weight.
    platform_admin_api_key: str = "change-me-in-.env"

    # Fernet key for encrypting TenantProviderCredential secrets at rest.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    credential_encryption_key: str = "change-me-in-.env"

    dograh_base_url: str = "http://localhost:8080"
    dograh_webhook_secret: str = "change-me-in-.env"

    # URL Dograh's own containers use to call back into us (tool webhooks,
    # inbound-call webhook). Distinct from dograh_base_url (which is how WE
    # reach Dograh) because the two sides usually can't use "localhost" for
    # each other — e.g. on Docker Desktop, Dograh's container reaches a
    # control-plane running directly on the host via host.docker.internal,
    # not localhost, even though our own browser/dashboard uses localhost.
    dograh_callback_base_url: str = "http://host.docker.internal:8000"

    # Shared secret Dograh sends back on every tool webhook call (transfer_call/
    # end_call ride Dograh's native nodes, so only book_appointment/
    # search_knowledge-style webhook tools use this) — checked in
    # api/v1/internal_tools.py. Not a full auth system: these endpoints only
    # ever get called by Dograh, never a browser.
    internal_tool_secret: str = "change-me-in-.env"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "voiceagent"
    minio_secret_key: str = "voiceagent-secret"
    minio_secure: bool = False
    minio_documents_bucket: str = "documents"
    minio_recordings_bucket: str = "recordings"

    # The dashboard runs on a different origin (localhost:3000) in dev and
    # its own domain in prod — CORS has to allow it explicitly.
    dashboard_origins: str = "http://localhost:3000,http://localhost:3001"

    @property
    def dashboard_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.dashboard_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
