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
    ports = sorted((s["src_port"], s["dst_port"]) for s in result["sessions"])
    assert ports == [(1, 1), (2, 2), (3, 3)]

    cores = sorted((s.get("src_core"), s.get("dst_core")) for s in result["sessions"])
    assert cores == [(1, 12), (2, 11), (3, 10)]

    r1_variant = next(m for m in result["modules"] if m["rack_id"] == "R1")["polarity_variant"]
    r2_variant = next(m for m in result["modules"] if m["rack_id"] == "R2")["polarity_variant"]
    assert {r1_variant, r2_variant} == {"B"}


def test_mpo_pass_through_forces_type_b_even_if_af_is_requested() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "mpo-type-af"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 3}
            ],
            "settings": {"fixed_profiles": {"mpo_e2e": {"pass_through_variant": "Type-AF"}}},
        }
    )
    result = allocate(project)
    ports = sorted((s["src_port"], s["dst_port"]) for s in result["sessions"])
    assert ports == [(1, 1), (2, 2), (3, 3)]

    cores = sorted((s.get("src_core"), s.get("dst_core")) for s in result["sessions"])
    assert cores == [(1, 12), (2, 11), (3, 10)]

    r1_variant = next(m for m in result["modules"] if m["rack_id"] == "R1")["polarity_variant"]
    r2_variant = next(m for m in result["modules"] if m["rack_id"] == "R2")["polarity_variant"]
    assert {r1_variant, r2_variant} == {"B"}
