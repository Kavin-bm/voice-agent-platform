from functools import lru_cache
from io import BytesIO

from minio import Minio

from app.core.config import get_settings


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket(bucket: str) -> None:
    client = get_minio_client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def put_object(bucket: str, key: str, data: bytes, content_type: str) -> None:
    ensure_bucket(bucket)
    get_minio_client().put_object(bucket, key, BytesIO(data), length=len(data), content_type=content_type)


def get_object(bucket: str, key: str) -> bytes:
    response = get_minio_client().get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
