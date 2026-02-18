# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

from models import ProjectInput
from services.allocator import allocate


def test_lc_fiber_mapping_present() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "lc"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "smf_lc_duplex", "count": 2}
            ],
        }
    )
    result = allocate(project)
    fibers = {(s["fiber_a"], s["fiber_b"]) for s in result["sessions"]}
    assert (1, 2) in fibers
    assert (3, 4) in fibers
