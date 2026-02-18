# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

from models import ProjectInput
from services.allocator import allocate


def test_mpo_alignment() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "mpo"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 3}
            ],
        }
    )
    result = allocate(project)
    assert all(s["src_port"] == s["dst_port"] for s in result["sessions"])
