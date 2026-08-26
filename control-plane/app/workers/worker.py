from arq.connections import RedisSettings

from app.core.config import get_settings
from app.workers.tasks import ingest_document


class WorkerSettings:
    functions = [ingest_document]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
