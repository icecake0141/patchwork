# Copyright 2026 OpenAI
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

from typing import Any

from conftest import allocate_twice, collect_values, iter_items


def test_allocator_mixed_same_u_mpo_and_mmf(allocator_fn) -> None:
    """14.4: MPO3スロット+MMF1スロットで、同一U内混在配置を検証。"""
    scenario: dict[str, Any] = {
        "case": "14.4",
        "racks": ["R01"],
        "u_position": 14,
        "mix": [
            {"media": "mpo", "slots": 3},
            {"media": "mmf_lc_duplex", "slots": 1},
        ],
    }

    result_first, result_second = allocate_twice(allocator_fn, scenario)

    placements = iter_items(result_first, ("placements", "slot_allocations", "modules"))
    same_u = [p for p in placements if p.get("u") == 14 or p.get("u_position") == 14]

    mpo_count = sum(
        1 for p in same_u if str(p.get("media", "")).lower().startswith("mpo")
    )
    mmf_count = sum(1 for p in same_u if "mmf" in str(p.get("media", "")).lower())

    assert mpo_count == 3
    assert mmf_count == 1

    assert collect_values(result_first, "session_id") == collect_values(
        result_second, "session_id"
    )
    assert collect_values(result_first, "cable_id") == collect_values(
        result_second, "cable_id"
    )
