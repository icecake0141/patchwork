# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

from models import ProjectInput
from services.allocator import allocate


def test_slot_progression_top_down() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "mix"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 12},
                {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 1},
            ],
        }
    )
    result = allocate(project)
    r1_modules = [m for m in result["modules"] if m["rack_id"] == "R1"]
    assert {(m["panel_u"], m["slot"]) for m in r1_modules} == {(1, 1), (1, 2)}
