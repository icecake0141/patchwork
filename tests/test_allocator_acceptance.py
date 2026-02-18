# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

from models import ProjectInput
from services.allocator import allocate


def _base() -> dict:
    return {
        "version": 1,
        "project": {"name": "acc"},
        "racks": [
            {"id": "R01", "name": "R01"},
            {"id": "R02", "name": "R02"},
            {"id": "R03", "name": "R03"},
        ],
        "demands": [],
    }


def test_lc_breakout_scaling_acceptance() -> None:
    payload = _base()
    payload["demands"] = [
        {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "mmf_lc_duplex", "count": 13}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    mmf_mods = [
        m for m in result["modules"] if m["module_type"] == "lc_breakout_2xmpo12_to_12xlcduplex"
    ]
    assert len(mmf_mods) == 4
    assert len([s for s in result["sessions"] if s["media"] == "mmf_lc_duplex"]) == 13
    assert len([c for c in result["cables"] if c["polarity_type"] == "A"]) == 4


def test_mpo_e2e_capacity_acceptance() -> None:
    payload = _base()
    payload["demands"] = [
        {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "mpo12", "count": 14}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    mpo_sessions = [s for s in result["sessions"] if s["media"] == "mpo12"]
    assert len(mpo_sessions) == 14
    assert all(s["src_port"] == s["dst_port"] for s in mpo_sessions)
    assert len([c for c in result["cables"] if c["polarity_type"] == "B"]) == 14


def test_utp_tail_sharing_acceptance() -> None:
    payload = _base()
    payload["demands"] = [
        {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "utp_rj45", "count": 7},
        {"id": "D2", "src": "R01", "dst": "R03", "endpoint_type": "utp_rj45", "count": 2},
    ]
    result = allocate(ProjectInput.model_validate(payload))
    r01_utp = [
        m for m in result["modules"] if m["rack_id"] == "R01" and m["module_type"] == "utp_6xrj45"
    ]
    assert len(r01_utp) == 2


def test_mixed_in_u_behavior_acceptance() -> None:
    payload = _base()
    payload["demands"] = [
        {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "mpo12", "count": 36},
        {"id": "D2", "src": "R01", "dst": "R02", "endpoint_type": "mmf_lc_duplex", "count": 1},
    ]
    result = allocate(ProjectInput.model_validate(payload))
    r01 = [m for m in result["modules"] if m["rack_id"] == "R01"]
    assert any(
        m["panel_u"] == 1 and m["slot"] == 4 and m["module_type"].startswith("lc_breakout")
        for m in r01
    )
