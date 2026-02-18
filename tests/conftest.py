# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def make_project(payload: dict):
    from models import ProjectInput

    return ProjectInput.model_validate(payload)


def load_yaml(text: str):
    from models import ProjectInput

    return ProjectInput.model_validate(yaml.safe_load(text))
