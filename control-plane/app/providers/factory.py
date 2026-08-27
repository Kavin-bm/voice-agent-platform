from app.providers.adapters.dograh import DograhAdapter

_ADAPTERS = {"dograh": DograhAdapter}


def get_runtime_adapter(name: str = "dograh"):
    """The seam PRD section 7 asks for: swapping the voice runtime (e.g. for
    LiveKit/Pipecat later) means adding one adapter here, never touching
    tenant/agent/knowledge code. Only one adapter exists today because only
    one runtime is in use — this is the minimum shape that keeps the seam
    real without building for a runtime that doesn't exist yet."""
    try:
        return _ADAPTERS[name]()
    except KeyError:
        raise ValueError(f"Unknown runtime adapter: {name!r}") from None
