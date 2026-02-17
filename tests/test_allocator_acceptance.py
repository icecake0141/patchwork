# Copyright 2026 Patchwork Authors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

from models import ProjectYaml
from services.allocator import allocate_project


def _project(demands: list[dict[str, object]]) -> ProjectYaml:
    data = {
        "version": 1,
        "project": {"name": "test"},
        "racks": [
            {"id": "R01", "name": "R01"},
            {"id": "R02", "name": "R02"},
            {"id": "R03", "name": "R03"},
            {"id": "R04", "name": "R04"},
        ],
        "demands": demands,
    }
    return ProjectYaml.model_validate(data)


def test_lc_breakout_scaling_13() -> None:
    result = allocate_project(
        _project(
            [
                {
                    "id": "D1",
                    "src": "R01",
                    "dst": "R02",
                    "endpoint_type": "mmf_lc_duplex",
                    "count": 13,
                }
            ]
        )
    )
    mmf_modules = [
        m for m in result["modules"] if m["module_type"] == "lc_breakout_2xmpo12_to_12xlcduplex"
    ]
    assert len([m for m in mmf_modules if m["rack_id"] == "R01"]) == 2
    assert len([m for m in mmf_modules if m["rack_id"] == "R02"]) == 2
    lc_sessions = [s for s in result["sessions"] if s["media"] == "mmf_lc_duplex"]
    assert len(lc_sessions) == 13
    lc_trunks = [
        c
        for c in result["cables"]
        if c["cable_type"] == "mpo12_trunk"
        and c["fiber_kind"] == "mmf"
        and c["polarity_type"] == "A"
    ]
    assert len(lc_trunks) == 4


def test_mpo_e2e_slot_capacity_14() -> None:
    result = allocate_project(
        _project(
            [
                {
                    "id": "D1",
                    "src": "R01",
                    "dst": "R02",
                    "endpoint_type": "mpo12",
                    "count": 14,
                }
            ]
        )
    )
    mpo_modules = [m for m in result["modules"] if m["module_type"] == "mpo12_pass_through_12port"]
    assert len([m for m in mpo_modules if m["rack_id"] == "R01"]) == 2
    assert len([m for m in mpo_modules if m["rack_id"] == "R02"]) == 2
    mpo_sessions = [s for s in result["sessions"] if s["media"] == "mpo12"]
    assert len(mpo_sessions) == 14
    assert all(s["src_port"] == s["dst_port"] for s in mpo_sessions)
    mpo_trunks = [c for c in result["cables"] if c["cable_type"] == "mpo12_trunk"]
    assert len(mpo_trunks) == 14
    assert all(c["polarity_type"] == "B" for c in mpo_trunks)


def test_utp_grouping_tail_sharing_shape() -> None:
    result = allocate_project(
        _project(
            [
                {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "utp_rj45", "count": 7},
                {"id": "D2", "src": "R01", "dst": "R03", "endpoint_type": "utp_rj45", "count": 2},
            ]
        )
    )
    r01_modules = [
        m for m in result["modules"] if m["rack_id"] == "R01" and m["module_type"] == "utp_6xrj45"
    ]
    assert len(r01_modules) == 2
    r01_sessions = [
        s for s in result["sessions"] if s["media"] == "utp_rj45" and s["src_rack"] == "R01"
    ]
    to_r02 = [s for s in r01_sessions if s["dst_rack"] == "R02"]
    to_r03 = [s for s in r01_sessions if s["dst_rack"] == "R03"]
    assert len(to_r02) == 7
    assert len(to_r03) == 2
    assert max(s["src_u"] * 10 + s["src_slot"] for s in to_r02) <= max(
        s["src_u"] * 10 + s["src_slot"] for s in to_r03
    )


def test_mixed_in_u_behavior() -> None:
    result = allocate_project(
        _project(
            [
                {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "mpo12", "count": 36},
                {
                    "id": "D2",
                    "src": "R01",
                    "dst": "R03",
                    "endpoint_type": "mmf_lc_duplex",
                    "count": 1,
                },
            ]
        )
    )
    r01_modules = [m for m in result["modules"] if m["rack_id"] == "R01"]
    first_u_slots = [m for m in r01_modules if m["panel_u"] == 1]
    assert len(first_u_slots) == 4


def test_deterministic_ids_stable() -> None:
    project = _project(
        [
            {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "mpo12", "count": 14},
            {"id": "D2", "src": "R01", "dst": "R03", "endpoint_type": "utp_rj45", "count": 8},
        ]
    )
    result1 = allocate_project(project)
    result2 = allocate_project(project)
    assert [s["session_id"] for s in result1["sessions"]] == [
        s["session_id"] for s in result2["sessions"]
    ]
    assert [c["cable_id"] for c in result1["cables"]] == [c["cable_id"] for c in result2["cables"]]
