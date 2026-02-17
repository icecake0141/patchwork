# Copyright 2026 OpenAI
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

from typing import Any

from conftest import allocate_twice, collect_values, iter_items


def test_allocator_mpo12_count14(allocator_fn) -> None:
    """14.2: mpo12 count=14 の検証（各ラック2スロット/14セッション/極性B/ポート整合）。"""
    scenario: dict[str, Any] = {
        "case": "14.2",
        "media": "mpo12",
        "count": 14,
        "polarity": "B",
        "racks": ["R01", "R02"],
    }

    result_first, result_second = allocate_twice(allocator_fn, scenario)

    racks = iter_items(result_first, ("racks", "rack_allocations"))
    assert len(racks) == 2
    for rack in racks:
        slots = iter_items(rack, ("slots", "slot_allocations"))
        assert len(slots) == 2

    sessions = collect_values(result_first, "session_id")
    assert len(sessions) == 14

    trunks = [
        t
        for t in iter_items(result_first, ("trunks", "cables"))
        if str(t.get("type", "")).lower().startswith("mpo")
    ]
    assert trunks, "MPO trunk allocation must exist"
    assert all(str(t.get("polarity", "")).upper() == "B" for t in trunks)

    for trunk in trunks:
        src_port = trunk.get("from_port") or trunk.get("src_port")
        dst_port = trunk.get("to_port") or trunk.get("dst_port")
        assert isinstance(src_port, int) and isinstance(dst_port, int)
        assert 1 <= src_port <= 12
        assert 1 <= dst_port <= 12

    assert collect_values(result_first, "session_id") == collect_values(
        result_second, "session_id"
    )
    assert collect_values(result_first, "cable_id") == collect_values(
        result_second, "cable_id"
    )
