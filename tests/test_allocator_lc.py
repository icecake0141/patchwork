# Copyright 2026 OpenAI
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

from typing import Any

from conftest import allocate_twice, collect_values, iter_items


def test_allocator_lc_duplex_count13(allocator_fn) -> None:
    """14.1: mmf_lc_duplex count=13 を再現し、ラック2モジュール・13セッション・MPOトランク4を検証。"""
    scenario: dict[str, Any] = {
        "case": "14.1",
        "media": "mmf_lc_duplex",
        "count": 13,
        "racks": ["R01", "R02"],
    }

    result_first, result_second = allocate_twice(allocator_fn, scenario)

    racks = iter_items(result_first, ("racks", "rack_allocations"))
    assert len(racks) == 2
    for rack in racks:
        modules = iter_items(rack, ("modules", "line_modules", "patch_modules"))
        assert len(modules) == 2

    sessions = collect_values(result_first, "session_id")
    assert len(sessions) == 13

    trunks = [
        t
        for t in iter_items(result_first, ("trunks", "cables"))
        if str(t.get("type", "")).lower().startswith("mpo")
    ]
    assert len(trunks) == 4

    assert collect_values(result_first, "session_id") == collect_values(
        result_second, "session_id"
    )
    assert collect_values(result_first, "cable_id") == collect_values(
        result_second, "cable_id"
    )
