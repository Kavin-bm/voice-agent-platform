#!/usr/bin/env python3
"""Drafts a starter VerticalPack YAML for a new industry vertical so the
operator edits a first draft instead of writing one from a blank file —
see "Scaffolding a brand-new vertical fast" in the plan.

This is a draft generator, not an autonomous agent: it writes the file
under templates/verticals/ and stops. Nothing is seeded into the DB and
nothing is deployed to a client until a human reviews the YAML and runs
scripts/seed_templates.py.

Usage:
    uv run python ../scripts/scaffold_vertical.py \
        --template receptionist --name salon \
        --brief "Hair/beauty salon: haircuts, coloring, walk-ins vs appointments"

Requires an LLM API key on the environment (e.g. GEMINI_API_KEY or
OPENAI_API_KEY) — litellm picks whichever matches --model.
"""

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401
import litellm
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"

SYSTEM_PROMPT = """You draft VerticalPack YAML files for a voice AI agent \
platform. Output ONLY valid YAML, no markdown fences, no commentary, \
matching exactly this schema:

template_slug: <the base template slug, unchanged from input>
slug: <template_slug>_<vertical_name>_india
name: <Human readable name>
prompt_additions: |
  <2-4 sentences: what this vertical's callers typically ask about, any
  domain-specific handling (urgency signals, common terms), and a note
  that Hindi/English code-switching is normal and should be handled
  naturally — this platform is India-first.>
extra_policies:
  - category: <short category slug>
    rule_text: >
      <one clear rule this vertical needs beyond the base template>
extra_tools:
  - <tool name, only from: search_knowledge, book_appointment, create_lead, transfer_call, end_call>
default_provider_stack:
  stt: { provider: sarvam, model: saaras-v3 }
  tts: { provider: sarvam, model: bulbul-v3 }
  telephony: exotel
  llm: { provider: gemini, model: gemini-flash }
voice_config_defaults:
  persona: <short phrase>
  backchannel: true
  interruption_sensitivity: high
  emotion: <short phrase>
  languages: [hi, en]

Write 1-3 extra_policies entries, grounded in the brief. Don't invent tools \
outside the allowed list."""


def scaffold(template_slug: str, name: str, brief: str, model: str) -> Path:
    user_prompt = f"template_slug: {template_slug}\nvertical_name: {name}\nbrief: {brief}"
    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.removeprefix("```yaml").removeprefix("```").removesuffix("```").strip()

    data = yaml.safe_load(raw)  # fail loudly if the model didn't return valid YAML
    out_path = TEMPLATES_DIR / "verticals" / f"{data['slug']}.yaml"
    out_path.write_text(raw + "\n")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, help="base template slug, e.g. receptionist")
    parser.add_argument("--name", required=True, help="short vertical name, e.g. salon")
    parser.add_argument("--brief", required=True, help="one-line description of the business type")
    parser.add_argument("--model", default="gemini/gemini-flash-latest")
    args = parser.parse_args()

    path = scaffold(args.template, args.name, args.brief, args.model)
    print(f"Draft written to {path}")
    print("Review and edit it, then run: uv run python ../scripts/seed_templates.py")
