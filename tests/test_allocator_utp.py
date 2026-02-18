# Copyright 2026 OpenAI
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

from typing import Any

from conftest import allocate_twice, collect_values, iter_items


def test_allocator_utp_tail_share_for_6port_module(allocator_fn) -> None:
    """14.3: R02:7, R03:2 を入力し、6ポートモジュールへのテールシェア割当を検証。"""
    scenario: dict[str, Any] = {
        "case": "14.3",
        "media": "utp",
        "demands": {"R02": 7, "R03": 2},
        "module_ports": 6,
        "allocation_mode": "tail_share",
    }

    result_first, result_second = allocate_twice(allocator_fn, scenario)

    modules = [
        m
        for m in iter_items(result_first, ("modules", "patch_modules"))
        if int(m.get("port_count", m.get("ports", 0))) == 6
    ]
    assert modules, "At least one 6-port module allocation is required"

    tail_shared = [
        m for m in modules if bool(m.get("tail_share") or m.get("shared_tail"))
    ]
    assert tail_shared, "Expected tail-share allocation on 6-port module"

    assert len(collect_values(result_first, "session_id")) == 9

    assert collect_values(result_first, "session_id") == collect_values(
        result_second, "session_id"
    )
    assert collect_values(result_first, "cable_id") == collect_values(
        result_second, "cable_id"
    )
