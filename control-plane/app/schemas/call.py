import uuid

from pydantic import BaseModel, ConfigDict

from app.models.call import CallDirection, CallStatus


class CallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_version_id: uuid.UUID
    dograh_call_id: str | None
    direction: CallDirection
    status: CallStatus
    duration_sec: int | None
    first_response_latency_ms: float | None
    outcome: str | None
    summary: str | None


class TranscriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content: str


class RecordingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    storage_uri: str
    duration_sec: int | None


class CallDetail(CallRead):
    transcript: TranscriptRead | None
    recording: RecordingRead | None
