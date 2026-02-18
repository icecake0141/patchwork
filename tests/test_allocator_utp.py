# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

from models import ProjectInput
from services.allocator import allocate


def test_utp_sessions_match_count() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "utp"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 8}
            ],
        }
    )
    result = allocate(project)
    assert len([s for s in result["sessions"] if s["media"] == "utp_rj45"]) == 8
