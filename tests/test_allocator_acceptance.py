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
    assert all(m["fiber_kind"] == "mmf" for m in mmf_mods)

    sessions = [s for s in result["sessions"] if s["media"] == "mmf_lc_duplex"]
    assert len(sessions) == 13
    assert {s["adapter_type"] for s in sessions} == {"lc_breakout_2xmpo12_to_12xlcduplex"}

    session_ports = sorted((s["src_u"], s["src_slot"], s["src_port"]) for s in sessions)
    assert session_ports[:12] == [(1, 1, port) for port in range(1, 13)]
    assert session_ports[12] == (1, 2, 1)

    mpo_trunks = [
        c
        for c in result["cables"]
        if c["cable_type"] == "mpo12_trunk" and c["polarity_type"] == "A"
    ]
    assert len(mpo_trunks) == 4


def test_mpo_e2e_capacity_acceptance() -> None:
    payload = _base()
    payload["demands"] = [
        {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "mpo12", "count": 14}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    mpo_sessions = [s for s in result["sessions"] if s["media"] == "mpo12"]
    assert len(mpo_sessions) == 14
    assert all(s["src_port"] == s["dst_port"] for s in mpo_sessions)

    slot1_ports = sorted(
        s["src_port"] for s in mpo_sessions if s["src_u"] == 1 and s["src_slot"] == 1
    )
    slot2_ports = sorted(
        s["src_port"] for s in mpo_sessions if s["src_u"] == 1 and s["src_slot"] == 2
    )
    assert slot1_ports == list(range(1, 13))
    assert slot2_ports == [1, 2]

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

    sessions = [
        s for s in result["sessions"] if s["media"] == "utp_rj45" and s["src_rack"] == "R01"
    ]
    r02_ports = sorted(
        (s["src_u"], s["src_slot"], s["src_port"]) for s in sessions if s["dst_rack"] == "R02"
    )
    r03_ports = sorted(
        (s["src_u"], s["src_slot"], s["src_port"]) for s in sessions if s["dst_rack"] == "R03"
    )
    assert r02_ports == [
        (1, 1, 1),
        (1, 1, 2),
        (1, 1, 3),
        (1, 1, 4),
        (1, 1, 5),
        (1, 1, 6),
        (1, 2, 1),
    ]
    assert r03_ports == [(1, 2, 2), (1, 2, 3)]


def test_utp_tail_module_exact_fill_acceptance() -> None:
    payload = _base()
    payload["demands"] = [
        {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "utp_rj45", "count": 4},
        {"id": "D2", "src": "R01", "dst": "R03", "endpoint_type": "utp_rj45", "count": 2},
    ]
    result = allocate(ProjectInput.model_validate(payload))

    r01_utp = [
        m for m in result["modules"] if m["rack_id"] == "R01" and m["module_type"] == "utp_6xrj45"
    ]
    assert len(r01_utp) == 1

    sessions = [
        s for s in result["sessions"] if s["media"] == "utp_rj45" and s["src_rack"] == "R01"
    ]
    r02_ports = sorted(
        s["src_port"]
        for s in sessions
        if s["src_u"] == r01_utp[0]["panel_u"]
        and s["src_slot"] == r01_utp[0]["slot"]
        and s["dst_rack"] == "R02"
    )
    r03_ports = sorted(
        s["src_port"]
        for s in sessions
        if s["src_u"] == r01_utp[0]["panel_u"]
        and s["src_slot"] == r01_utp[0]["slot"]
        and s["dst_rack"] == "R03"
    )
    assert r02_ports == [1, 2, 3, 4]
    assert r03_ports == [5, 6]


def test_mixed_in_u_behavior_acceptance() -> None:
    payload = _base()
    payload["demands"] = [
        {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "mpo12", "count": 36},
        {"id": "D2", "src": "R01", "dst": "R02", "endpoint_type": "mmf_lc_duplex", "count": 1},
    ]
    result = allocate(ProjectInput.model_validate(payload))
    r01 = [m for m in result["modules"] if m["rack_id"] == "R01"]
    r02 = [m for m in result["modules"] if m["rack_id"] == "R02"]
    assert any(
        m["panel_u"] == 1 and m["slot"] == 4 and m["module_type"].startswith("lc_breakout")
        for m in r01
    )
    assert any(
        m["panel_u"] == 1 and m["slot"] == 4 and m["module_type"].startswith("lc_breakout")
        for m in r02
    )


def test_lc_demands_are_dedicated_by_default() -> None:
    payload = _base()
    payload["demands"] = [
        {"id": "D1", "src": "R01", "dst": "R02", "endpoint_type": "mmf_lc_duplex", "count": 1},
        {"id": "D2", "src": "R01", "dst": "R03", "endpoint_type": "mmf_lc_duplex", "count": 1},
    ]
    result = allocate(ProjectInput.model_validate(payload))
    r01_lc = [
        m
        for m in result["modules"]
        if m["rack_id"] == "R01" and m["module_type"] == "lc_breakout_2xmpo12_to_12xlcduplex"
    ]
    assert len(r01_lc) == 2
    assert {m["peer_rack_id"] for m in r01_lc} == {"R02", "R03"}
    assert all(m["dedicated"] == 1 for m in r01_lc)


def test_lc_demands_can_share_slots_when_aggregatable() -> None:
    payload = _base()
    payload["demands"] = [
        {
            "id": "D1",
            "src": "R01",
            "dst": "R02",
            "endpoint_type": "mmf_lc_duplex",
            "count": 1,
            "aggregatable": True,
        },
        {
            "id": "D2",
            "src": "R01",
            "dst": "R03",
            "endpoint_type": "mmf_lc_duplex",
            "count": 1,
            "aggregatable": True,
        },
    ]
    result = allocate(ProjectInput.model_validate(payload))
    r01_lc = [
        m
        for m in result["modules"]
        if m["rack_id"] == "R01" and m["module_type"] == "lc_breakout_2xmpo12_to_12xlcduplex"
    ]
    assert len(r01_lc) == 1
    assert r01_lc[0]["peer_rack_id"] is None
    assert r01_lc[0]["dedicated"] == 0

    r01_sessions = [
        s for s in result["sessions"] if s["media"] == "mmf_lc_duplex" and s["src_rack"] == "R01"
    ]
    assert len(r01_sessions) == 2
    assert {s["src_slot"] for s in r01_sessions} == {r01_lc[0]["slot"]}
