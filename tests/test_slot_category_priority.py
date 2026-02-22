# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Tests for ordering.slot_category_priority in the allocator."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import ProjectInput
from services.allocator import allocate


def _base_project(demands: list[dict], priority: list[str] | None = None) -> ProjectInput:
    payload: dict = {
        "version": 1,
        "project": {"name": "priority-test"},
        "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
        "demands": demands,
    }
    if priority is not None:
        payload["settings"] = {"ordering": {"slot_category_priority": priority}}
    return ProjectInput.model_validate(payload)


# ---------------------------------------------------------------------------
# Default order: mpo_e2e comes before lc_mmf
# ---------------------------------------------------------------------------


def test_default_priority_mpo_before_lc() -> None:
    """With default priority [mpo_e2e, lc_mmf, ...], MPO slots come first."""
    project = _base_project(
        [
            {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 12},
            {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "mmf_lc_duplex", "count": 1},
        ]
    )
    result = allocate(project)
    r1_mods = sorted(
        [m for m in result["modules"] if m["rack_id"] == "R1"],
        key=lambda m: (m["panel_u"], m["slot"]),
    )
    assert r1_mods[0]["module_type"] == "mpo12_pass_through_12port"
    assert r1_mods[1]["module_type"] == "lc_breakout_2xmpo12_to_12xlcduplex"


# ---------------------------------------------------------------------------
# Reversed priority: lc_mmf comes before mpo_e2e
# ---------------------------------------------------------------------------


def test_lc_mmf_before_mpo_e2e_changes_slot_assignment() -> None:
    """When lc_mmf is first in priority, LC slots come before MPO slots."""
    project = _base_project(
        [
            {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 12},
            {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "mmf_lc_duplex", "count": 1},
        ],
        priority=["lc_mmf", "mpo_e2e", "lc_smf", "utp"],
    )
    result = allocate(project)
    r1_mods = sorted(
        [m for m in result["modules"] if m["rack_id"] == "R1"],
        key=lambda m: (m["panel_u"], m["slot"]),
    )
    assert r1_mods[0]["module_type"] == "lc_breakout_2xmpo12_to_12xlcduplex"
    assert r1_mods[1]["module_type"] == "mpo12_pass_through_12port"


# ---------------------------------------------------------------------------
# Priority determinism: same priority always yields same result
# ---------------------------------------------------------------------------


def test_priority_is_deterministic() -> None:
    """Running the allocator twice with the same priority produces identical output."""
    demands = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 6},
        {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "mmf_lc_duplex", "count": 3},
        {"id": "D3", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 2},
    ]
    project = _base_project(demands, priority=["lc_mmf", "utp", "mpo_e2e", "lc_smf"])
    result1 = allocate(project)
    result2 = allocate(project)
    assert result1["modules"] == result2["modules"]
    assert result1["sessions"] == result2["sessions"]
    assert result1["input_hash"] == result2["input_hash"]


# ---------------------------------------------------------------------------
# UTP priority position affects slot assignment
# ---------------------------------------------------------------------------


def test_utp_first_priority_gets_first_slots() -> None:
    """When utp is first in priority, UTP modules occupy the lowest-numbered slots."""
    project = _base_project(
        [
            {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 3},
            {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 12},
        ],
        priority=["utp", "mpo_e2e", "lc_mmf", "lc_smf"],
    )
    result = allocate(project)
    r1_mods = sorted(
        [m for m in result["modules"] if m["rack_id"] == "R1"],
        key=lambda m: (m["panel_u"], m["slot"]),
    )
    assert r1_mods[0]["module_type"] == "utp_6xrj45"
    assert r1_mods[1]["module_type"] == "mpo12_pass_through_12port"


# ---------------------------------------------------------------------------
# Missing category: categories omitted from priority are simply not allocated
# ---------------------------------------------------------------------------


def test_omitted_category_skips_allocation() -> None:
    """A category absent from priority is not allocated at all."""
    project = _base_project(
        [
            {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 6},
            {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 2},
        ],
        # lc_mmf and lc_smf omitted; no LC demands so omission has no effect on modules
        priority=["mpo_e2e", "utp"],
    )
    result = allocate(project)
    module_types = {m["module_type"] for m in result["modules"]}
    assert "lc_breakout_2xmpo12_to_12xlcduplex" not in module_types
    assert "mpo12_pass_through_12port" in module_types
    assert "utp_6xrj45" in module_types


def test_utp_omitted_from_priority_skips_utp_allocation() -> None:
    """When 'utp' is absent from priority, UTP demands are not allocated."""
    project = _base_project(
        [
            {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 2},
            {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 6},
        ],
        priority=["mpo_e2e", "lc_mmf", "lc_smf"],  # "utp" deliberately omitted
    )
    result = allocate(project)
    utp_modules = [m for m in result["modules"] if m["module_type"] == "utp_6xrj45"]
    utp_sessions = [s for s in result["sessions"] if s["media"] == "utp_rj45"]
    assert utp_modules == []
    assert utp_sessions == []


# ---------------------------------------------------------------------------
# Validation: unknown categories are rejected
# ---------------------------------------------------------------------------


def test_unknown_category_raises_validation_error() -> None:
    """An unknown category in slot_category_priority must raise a ValidationError."""
    with pytest.raises(ValidationError, match="unknown slot_category_priority entries"):
        ProjectInput.model_validate(
            {
                "version": 1,
                "project": {"name": "bad"},
                "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
                "demands": [],
                "settings": {
                    "ordering": {
                        "slot_category_priority": ["mpo_e2e", "bad_category"],
                    }
                },
            }
        )
