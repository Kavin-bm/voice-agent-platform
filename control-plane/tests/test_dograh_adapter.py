import uuid

from app.providers.adapters.dograh import build_tool_definitions, build_workflow_definition


def _spec(**overrides: object) -> dict:
    spec = {
        "prompt": "Be brief.",
        "business": {
            "id": str(uuid.uuid4()),
            "name": "Smile Bright",
            "structured_config": {},
            "default_transfer_number": "+919800000000",
        },
        "policies": [
            {"category": "escalation", "rule_text": "Transfer emergencies immediately."}
        ],
        "tools": [
            {"name": "transfer_call", "type": "built_in", "config": {}},
            {"name": "end_call", "type": "built_in", "config": {}},
            {"name": "search_knowledge", "type": "built_in", "config": {}},
            {"name": "book_appointment", "type": "built_in", "config": {}},
            {
                "name": "create_lead",
                "type": "webhook",
                "config": {"url": "https://crm.example/leads", "method": "POST"},
            },
        ],
        "knowledge_source_ids": [],
        "voice_config": {
            "persona": "warm",
            "backchannel": True,
            "interruption_sensitivity": "high",
            "languages": ["hi", "en"],
        },
        "provider_stack": {"stt": {"provider": "sarvam", "model": "saaras-v3"}},
    }
    spec.update(overrides)
    return spec


def test_workflow_enables_interrupt_and_ignores_voice_config() -> None:
    spec = _spec()
    definition = build_workflow_definition(spec, ["tool-1"], str(uuid.uuid4()))
    nodes = {node["id"]: node for node in definition["nodes"]}

    assert nodes["start"]["data"]["allow_interrupt"] is True
    assert nodes["main"]["data"]["allow_interrupt"] is True
    assert "allow_interrupt" not in nodes["end"]["data"]
    assert nodes["start"]["data"]["greeting"] == (
        "Thanks for calling Smile Bright, how can I help you today?"
    )
    assert nodes["start"]["data"]["greeting_type"] == "text"
    assert "Transfer emergencies immediately." in nodes["global"]["data"]["prompt"]

    # voice_config and provider_stack stay in the compiled spec. They are not
    # copied onto Dograh nodes.
    rendered = str(definition)
    assert "interruption_sensitivity" not in rendered
    assert "saaras-v3" not in rendered
    assert "backchannel" not in rendered

    webhook = nodes["call-complete-webhook"]["data"]
    assert webhook["endpoint_url"].endswith("/internal/webhooks/dograh-call-complete")
    assert "first_response_latency_ms" not in webhook["payload_template"]
    assert "call_duration_seconds" in webhook["payload_template"]


def test_tool_definitions_skip_unwired_builtins() -> None:
    spec = _spec()
    definitions = {item["name"]: item for item in build_tool_definitions(spec)}

    assert set(definitions) == {"transfer_call", "end_call", "search_knowledge", "create_lead"}
    assert definitions["transfer_call"]["definition"]["config"]["destination"] == "+919800000000"
    search = definitions["search_knowledge"]["definition"]["config"]
    assert search["url"].endswith("/internal/tools/search-knowledge")
    assert search["preset_parameters"][0]["value_template"] == spec["business"]["id"]
    assert definitions["create_lead"]["definition"]["config"]["url"] == "https://crm.example/leads"


def test_call_complete_schema_does_not_accept_latency() -> None:
    from app.api.internal import CallCompleteWebhook

    assert "first_response_latency_ms" not in CallCompleteWebhook.model_fields


def test_transfer_is_omitted_without_a_number() -> None:
    spec = _spec()
    spec["business"]["default_transfer_number"] = None
    spec["tools"] = [{"name": "transfer_call", "type": "built_in", "config": {}}]
    assert build_tool_definitions(spec) == []
