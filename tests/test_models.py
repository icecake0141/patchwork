# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

import pytest

from models import ProjectInput


def test_model_validation_rejects_duplicate_rack_ids() -> None:
    payload = {
        "version": 1,
        "project": {"name": "x"},
        "racks": [{"id": "R1", "name": "A"}, {"id": "R1", "name": "B"}],
        "demands": [],
    }
    with pytest.raises(ValueError):
        ProjectInput.model_validate(payload)
