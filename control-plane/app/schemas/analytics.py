from pydantic import BaseModel


class CallAnalyticsResponse(BaseModel):
    total_calls: int
    by_direction: dict[str, int]
    by_status: dict[str, int]
    by_outcome: dict[str, int]

    duration_seconds_p50: float | None
    duration_seconds_p95: float | None

    # Only meaningful once dograh_call_complete actually populates
    # Call.first_response_latency_ms (still an open gap — see the plan's
    # Voice quality & latency section). sample_size makes that honest
    # instead of silently returning a p50/p95 computed from nothing.
    first_response_latency_ms_p50: float | None
    first_response_latency_ms_p95: float | None
    first_response_latency_sample_size: int
