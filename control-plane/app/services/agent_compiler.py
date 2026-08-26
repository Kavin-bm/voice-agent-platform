import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentVersion
from app.models.business import Business
from app.models.knowledge import KnowledgeSource
from app.models.policy import Policy
from app.models.template import AgentTemplate, VerticalPack
from app.models.tool import Tool


def _fill(template_text: str, business: Business) -> str:
    return template_text.replace("{{business_name}}", business.name)


def build_compiled_spec(
    *,
    business: Business,
    template: AgentTemplate,
    vertical_pack: VerticalPack | None,
    knowledge_source_ids: list[uuid.UUID],
    explicit_policies: list[Policy],
    resolved_tools: list[Tool],
    voice_config_override: dict,
) -> dict:
    """Assembles Template + VerticalPack + Business + Knowledge + Policies +
    Tools + Voice into ONE neutral spec — the shape PRD section 3 describes
    as an agent's composition. Nothing here is Dograh-shaped; translating
    this into a runtime workflow is providers/adapters/dograh.py's job
    alone, so swapping runtimes later never touches this function."""

    prompt = _fill(template.base_prompt, business)
    if vertical_pack and vertical_pack.prompt_additions:
        prompt = f"{prompt}\n\n{_fill(vertical_pack.prompt_additions, business)}"

    policies = list(template.default_policies)
    if vertical_pack:
        policies += vertical_pack.extra_policies
    policies += [
        {"category": p.category, "rule_text": p.rule_text, "escalation_target": p.escalation_target}
        for p in explicit_policies
    ]

    tools = [{"name": t.name, "type": t.type.value, "config": t.config} for t in resolved_tools]

    provider_defaults = (vertical_pack.default_provider_stack if vertical_pack else {}) or {}
    voice_config = {
        **provider_defaults.get("voice_config_defaults", {}),
        **voice_config_override,
    }

    return {
        "prompt": prompt,
        "business": {
            "name": business.name,
            "structured_config": business.structured_config,
            "default_transfer_number": business.default_transfer_number,
        },
        "policies": policies,
        "tools": tools,
        "knowledge_source_ids": [str(ks_id) for ks_id in knowledge_source_ids],
        "voice_config": voice_config,
        "provider_stack": provider_defaults.get("providers", {}),
    }


async def compile_agent_version(db: AsyncSession, agent_version: AgentVersion) -> dict:
    agent = await db.get(Agent, agent_version.agent_id)
    business = await db.get(Business, agent.business_id)
    template = await db.get(AgentTemplate, agent.template_id)
    vertical_pack = (
        await db.get(VerticalPack, agent.vertical_pack_id) if agent.vertical_pack_id else None
    )

    knowledge_source_ids = list(
        (
            await db.execute(
                select(KnowledgeSource.id).where(KnowledgeSource.business_id == business.id)
            )
        )
        .scalars()
        .all()
    )

    explicit_policies = list(
        (
            await db.execute(select(Policy).where(Policy.agent_version_id == agent_version.id))
        )
        .scalars()
        .all()
    )

    # Tool set = template + vertical-pack defaults (by name, global built-in
    # rows) — an operator adds anything beyond that via AgentVersionTool,
    # not by editing the template. See Tools & integrations in the plan.
    default_tool_names = set(template.default_tools)
    if vertical_pack:
        default_tool_names |= set(vertical_pack.extra_tools)

    resolved_tools: list[Tool] = []
    if default_tool_names:
        resolved_tools = list(
            (
                await db.execute(
                    select(Tool).where(
                        Tool.tenant_id.is_(None), Tool.name.in_(default_tool_names)
                    )
                )
            )
            .scalars()
            .all()
        )

    spec = build_compiled_spec(
        business=business,
        template=template,
        vertical_pack=vertical_pack,
        knowledge_source_ids=knowledge_source_ids,
        explicit_policies=explicit_policies,
        resolved_tools=resolved_tools,
        voice_config_override=agent_version.voice_config,
    )

    agent_version.compiled_spec = spec
    await db.commit()
    await db.refresh(agent_version)
    return spec
