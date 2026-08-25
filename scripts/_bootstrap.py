"""Puts control-plane/ on sys.path so operator scripts in scripts/ can
import the app package. Run these scripts with the control-plane venv,
e.g. `uv run --project control-plane python ../scripts/seed_templates.py`."""

import sys
from pathlib import Path

CONTROL_PLANE = Path(__file__).resolve().parent.parent / "control-plane"
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(CONTROL_PLANE) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE))
