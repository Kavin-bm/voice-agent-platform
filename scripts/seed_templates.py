#!/usr/bin/env python3
"""Upserts AgentTemplate/VerticalPack rows from templates/*.yaml and
templates/verticals/*.yaml. Idempotent — safe to rerun after editing a
YAML file (matches on slug).

Usage (from control-plane/, so its venv/deps are on the path):
    uv run python ../scripts/seed_templates.py
"""

import asyncio
from pathlib import Path

import _bootstrap  # noqa: F401  (adds control-plane/ to sys.path)
import yaml

from app.core.db import async_session_factory
from app.models.template import AgentTemplate, VerticalPack
from app.models.tool import Tool, ToolType
from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"

# Global (tenant_id=NULL) built-in tools every template can reference by
# name. search_knowledge's real behavior lives in app/api/internal.py; the
# rest ride Dograh's native nodes. This just registers the name so
# agent_compiler.py can resolve default_tools lists to Tool rows before
# AgentVersionTool wiring exists per-tenant.
BUILT_IN_TOOLS = ["search_knowledge", "book_appointment", "create_lead", "transfer_call", "end_call"]


async def seed_builtin_tools(db) -> None:
    for name in BUILT_IN_TOOLS:
        existing = (
            await db.execute(
                select(Tool).where(Tool.tenant_id.is_(None), Tool.type == ToolType.built_in, Tool.name == name)
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(Tool(tenant_id=None, type=ToolType.built_in, name=name, config={}))
            print(f"tool      {name!r}")


async def seed() -> None:
    async with async_session_factory() as db:
        await seed_builtin_tools(db)
        await db.flush()

        template_ids_by_slug: dict[str, object] = {}

        for path in sorted(TEMPLATES_DIR.glob("*.yaml")):
            data = yaml.safe_load(path.read_text())
            existing = (
                await db.execute(select(AgentTemplate).where(AgentTemplate.slug == data["slug"]))
            ).scalar_one_or_none()
            if existing:
                existing.name = data["name"]
                existing.base_prompt = data["base_prompt"]
                existing.default_policies = data.get("default_policies", [])
                existing.default_tools = data.get("default_tools", [])
                template = existing
            else:
                template = AgentTemplate(
                    slug=data["slug"],
                    name=data["name"],
                    base_prompt=data["base_prompt"],
                    default_policies=data.get("default_policies", []),
                    default_tools=data.get("default_tools", []),
                )
                db.add(template)
            await db.flush()
            template_ids_by_slug[template.slug] = template.id
            print(f"template  {template.slug!r} -> {template.id}")

        for path in sorted((TEMPLATES_DIR / "verticals").glob("*.yaml")):
            data = yaml.safe_load(path.read_text())
            template_id = template_ids_by_slug.get(data["template_slug"])
            if template_id is None:
                print(f"skip {path.name}: unknown template_slug {data['template_slug']!r}")
                continue
            existing = (
                await db.execute(select(VerticalPack).where(VerticalPack.slug == data["slug"]))
            ).scalar_one_or_none()
            if existing:
                pack = existing
            else:
                pack = VerticalPack(slug=data["slug"])
                db.add(pack)
            pack.template_id = template_id
            pack.name = data["name"]
            pack.prompt_additions = data.get("prompt_additions", "")
            pack.extra_policies = data.get("extra_policies", [])
            pack.extra_tools = data.get("extra_tools", [])
            pack.default_provider_stack = {
                "providers": data.get("default_provider_stack", {}),
                "voice_config_defaults": data.get("voice_config_defaults", {}),
            }
            print(f"vertical  {pack.slug!r}")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
