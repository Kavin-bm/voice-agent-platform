"""Translates our neutral compiled_spec into Dograh's workflow/tool JSON.

This is the ONLY module that knows Dograh's shapes (node types, tool
categories) — confirmed against runtime/dograh/api/services/workflow/dto.py
and schemas/tool.py directly, not guessed. Swapping the runtime later means
writing one new adapter with this same interface, not touching
tenant/agent/knowledge code (see the plan's core architectural rule).

NOTE — verified vs. unverified:
- Node graph shape (startCall/globalNode/agentNode/endCall) and tool
  categories (http_api/transfer_call/end_call) are read directly from
  Dograh's Pydantic models — high confidence.
- Org-level STT/LLM/TTS provider configuration (OrganizationAIModelConfigurationV2)
  and telephony-config binding were only located, not fully read field-by-field —
  services/dograh_client.py flags those calls as needing verification against
  a live Dograh instance before the first real client deployment.
"""

from app.core.config import get_settings

settings = get_settings()


def _search_knowledge_tool_definition(business_id: str) -> dict:
    """search_knowledge is a webhook tool like any other, pointed at our own
    retrieval endpoint (services/search.py) rather than a tenant's URL.
    business_id is baked in as a preset_parameter — fixed at compile time,
    never something the LLM has to know or could get wrong — so retrieval
    can never leak across businesses/tenants."""

    return {
        "name": "search_knowledge",
        "description": (
            "Search this business's knowledge base for facts the caller is asking "
            "about (pricing, hours, services, policies). Always use this instead of "
            "guessing when the answer isn't already in your instructions."
        ),
        "definition": {
            "type": "http_api",
            "config": {
                "method": "POST",
                "url": f"{settings.dograh_callback_base_url}/internal/tools/search-knowledge",
                "headers": {"X-Tool-Secret": settings.internal_tool_secret},
                "parameters": [
                    {
                        "name": "query",
                        "type": "string",
                        "description": "The caller's question, as a short search query.",
                        "required": True,
                    }
                ],
                "preset_parameters": [
                    {
                        "name": "business_id",
                        "type": "string",
                        "value_template": business_id,
                        "required": True,
                    }
                ],
            },
        },
    }


def build_workflow_definition(compiled_spec: dict, tool_uuids: list[str]) -> dict:
    policies_text = "\n".join(
        f"- {p['rule_text'].strip()}" for p in compiled_spec["policies"] if p.get("rule_text")
    )
    global_prompt = compiled_spec["prompt"]
    if policies_text:
        global_prompt = f"{global_prompt}\n\nRules you must follow:\n{policies_text}"

    business_name = compiled_spec["business"]["name"]

    nodes = [
        {
            "id": "global",
            "type": "globalNode",
            "position": {"x": 0, "y": 0},
            "data": {"name": "Global", "prompt": global_prompt},
        },
        {
            "id": "start",
            "type": "startCall",
            "position": {"x": 300, "y": 0},
            "data": {
                "name": "Start Call",
                "is_start": True,
                "prompt": "Greet the caller and ask how you can help.",
                "greeting": f"Thanks for calling {business_name}, how can I help you today?",
                "greeting_type": "text",
                "add_global_prompt": True,
                "allow_interrupt": True,
                "tool_uuids": tool_uuids,
            },
        },
        {
            "id": "main",
            "type": "agentNode",
            "position": {"x": 600, "y": 0},
            "data": {
                "name": "Conversation",
                "prompt": "Continue the conversation naturally, answering questions and using tools as needed.",
                "allow_interrupt": True,
                "add_global_prompt": True,
                "tool_uuids": tool_uuids,
            },
        },
        {
            "id": "end",
            "type": "endCall",
            "position": {"x": 900, "y": 0},
            "data": {
                "name": "End Call",
                "prompt": "Thank the caller warmly and end the call.",
                "add_global_prompt": True,
            },
        },
    ]

    edges = [
        {
            "id": "start-main",
            "source": "start",
            "target": "main",
            "data": {"condition": "Always take this route", "label": "continue"},
        },
        {
            "id": "main-end",
            "source": "main",
            "target": "end",
            "data": {
                "condition": "The caller's request is resolved or they want to end the call",
                "label": "end call",
            },
        },
    ]

    return {"nodes": nodes, "edges": edges, "viewport": {"x": 0, "y": 0, "zoom": 1}}


def build_tool_definitions(compiled_spec: dict) -> list[dict]:
    """One CreateToolRequest body per tool this agent version needs.
    transfer_call bakes in this business's transfer number, so it's created
    fresh per publish rather than reused — simplest way to avoid a stale
    destination if the number changes later."""

    transfer_number = compiled_spec["business"].get("default_transfer_number")
    definitions = []

    for tool in compiled_spec["tools"]:
        name = tool["name"]
        if name == "transfer_call":
            if not transfer_number:
                continue
            definitions.append(
                {
                    "name": "transfer_call",
                    "description": "Transfer the call to a human when the caller needs one.",
                    "definition": {
                        "type": "transfer_call",
                        "config": {"destination_source": "static", "destination": transfer_number},
                    },
                }
            )
        elif name == "end_call":
            definitions.append(
                {
                    "name": "end_call",
                    "description": "End the call politely once the conversation is complete.",
                    "definition": {"type": "end_call", "config": {"messageType": "none"}},
                }
            )
        elif name == "search_knowledge":
            definitions.append(_search_knowledge_tool_definition(compiled_spec["business"]["id"]))
        elif tool["config"].get("url"):
            config = tool["config"]
            definitions.append(
                {
                    "name": name,
                    "description": config.get("description", f"Calls the {name} webhook."),
                    "definition": {
                        "type": "http_api",
                        "config": {
                            "method": config.get("method", "POST"),
                            "url": config["url"],
                            "headers": config.get("headers"),
                        },
                    },
                }
            )
        # else: built-in tool with no webhook URL configured yet (e.g.
        # search_knowledge before its endpoint is wired) — skipped, not
        # fabricated with a placeholder URL.

    return definitions


class DograhAdapter:
    """Groups the translation functions behind the provider-factory seam."""

    build_workflow_definition = staticmethod(build_workflow_definition)
    build_tool_definitions = staticmethod(build_tool_definitions)
