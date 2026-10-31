import uuid

from app.models.business import Business
from app.models.policy import Policy
from app.models.template import AgentTemplate, VerticalPack
from app.models.tool import Tool, ToolType
from app.services.agent_compiler import build_compiled_spec


def _business() -> Business:
    return Business(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="Smile Bright",
        structured_config={"city": "Pune"},
        default_transfer_number="+919800000000",
    )


def _template() -> AgentTemplate:
    return AgentTemplate(
        id=uuid.uuid4(),
        slug="receptionist",
        name="Receptionist",
        base_prompt="You answer for {{business_name}}.",
        default_policies=[
            {"category": "scope", "rule_text": "Only discuss {{business_name}}."}
        ],
        default_tools=["search_knowledge"],
    )


def _pack(template_id: uuid.UUID) -> VerticalPack:
    return VerticalPack(
        id=uuid.uuid4(),
        template_id=template_id,
        slug="receptionist_dental_india",
        name="Receptionist — Dental (India)",
        prompt_additions="Clinic notes for {{business_name}}.",
        extra_policies=[
            {
                "category": "escalation",
                "rule_text": "Emergencies at {{business_name}} transfer immediately.",
                "escalation_target": "emergency",
            }
        ],
        extra_tools=["book_appointment"],
        default_provider_stack={
            "providers": {
                "stt": {"provider": "sarvam", "model": "saaras-v3"},
                "llm": {"provider": "gemini", "model": "gemini-flash"},
            },
            "voice_config_defaults": {
                "persona": "warm",
                "interruption_sensitivity": "high",
                "languages": ["hi", "en"],
            },
        },
    )


def test_compiled_spec_fills_names_and_merges_voice_config() -> None:
    business = _business()
    template = _template()
    pack = _pack(template.id)
    policy = Policy(
        id=uuid.uuid4(),
        tenant_id=business.tenant_id,
        agent_version_id=uuid.uuid4(),
        category="hours",
        rule_text="{{business_name}} is open 9 to 7.",
        escalation_target=None,
    )
    tool = Tool(
        id=uuid.uuid4(),
        tenant_id=None,
        type=ToolType.built_in,
        name="search_knowledge",
        config={},
    )

    spec = build_compiled_spec(
        business=business,
        template=template,
        vertical_pack=pack,
        knowledge_source_ids=[uuid.uuid4()],
        explicit_policies=[policy],
        resolved_tools=[tool],
        voice_config_override={"interruption_sensitivity": "low"},
    )

    assert spec["prompt"] == "You answer for Smile Bright.\n\nClinic notes for Smile Bright."
    assert spec["policies"][0]["rule_text"] == "Only discuss Smile Bright."
    assert spec["policies"][1]["escalation_target"] == "emergency"
    assert spec["policies"][2]["rule_text"] == "Smile Bright is open 9 to 7."
    assert spec["voice_config"]["persona"] == "warm"
    assert spec["voice_config"]["interruption_sensitivity"] == "low"
    assert spec["voice_config"]["languages"] == ["hi", "en"]
    assert spec["provider_stack"]["stt"]["provider"] == "sarvam"
    assert spec["tools"] == [{"name": "search_knowledge", "type": "built_in", "config": {}}]
    assert spec["business"]["default_transfer_number"] == "+919800000000"


def test_compiled_spec_without_vertical_pack() -> None:
    business = _business()
    spec = build_compiled_spec(
        business=business,
        template=_template(),
        vertical_pack=None,
        knowledge_source_ids=[],
        explicit_policies=[],
        resolved_tools=[],
        voice_config_override={"persona": "brief"},
    )
    assert spec["provider_stack"] == {}
    assert spec["voice_config"] == {"persona": "brief"}
    assert "Clinic notes" not in spec["prompt"]
