import uuid
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError

from app.core import crypto
from app.core.config import Settings
from app.core.security import (
    create_access_token,
    hash_password,
    require_platform_admin,
    settings,
    verify_password,
)
from app.main import app
from app.schemas.tenant import TenantCreate


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_password_roundtrip() -> None:
    hashed = hash_password("change-me-now")
    assert verify_password("change-me-now", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_carries_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "test-secret")
    monkeypatch.setattr(settings, "jwt_algorithm", "HS256")
    monkeypatch.setattr(settings, "jwt_expires_minutes", 15)
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, tenant_id=tenant_id, role="owner")
    payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["role"] == "owner"


def test_platform_admin_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "platform_admin_api_key", "local-admin")
    require_platform_admin(x_admin_key="local-admin")
    with pytest.raises(HTTPException) as exc:
        require_platform_admin(x_admin_key="nope")
    assert exc.value.status_code == 403


def test_fernet_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(
        crypto,
        "get_settings",
        lambda: SimpleNamespace(credential_encryption_key=key),
    )
    crypto._fernet.cache_clear()
    try:
        ciphertext = crypto.encrypt_secret("secret-value")
        assert crypto.decrypt_secret(ciphertext) == "secret-value"
        # Appending junk can still decode: urlsafe base64 ignores some
        # trailing characters. Flip a payload character instead.
        chars = list(ciphertext)
        chars[10] = "A" if chars[10] != "A" else "B"
        with pytest.raises(InvalidToken):
            crypto.decrypt_secret("".join(chars))
    finally:
        crypto._fernet.cache_clear()


def test_dashboard_origins_are_split() -> None:
    settings_obj = Settings(
        _env_file=None,
        dashboard_origins=" http://localhost:3000, http://localhost:3001, ",
    )
    assert settings_obj.dashboard_origin_list == [
        "http://localhost:3000",
        "http://localhost:3001",
    ]


def test_quickstart_owner_email_is_accepted() -> None:
    body = TenantCreate(
        name="Acme Dental",
        slug="acme-dental",
        owner_email="owner@example.com",
        owner_password="change-me-now",
    )
    assert body.owner_email == "owner@example.com"


def test_reserved_test_tld_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TenantCreate(
            name="Acme Dental",
            slug="acme-dental",
            owner_email="owner@acme.test",
            owner_password="change-me-now",
        )
