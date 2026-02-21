# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Tests validating datacenter wiring design sufficiency improvements:
- Rack U capacity constraint (max_u)
- Sequential cable labels (cable_seq)
- Bill of Materials (BOM) export
"""

from __future__ import annotations

import csv
import io

from models import ProjectInput
from services.allocator import allocate
from services.export import bom_csv, sessions_csv


def _base_two_racks(max_u_r1: int = 42, max_u_r2: int = 42) -> dict:
    return {
        "version": 1,
        "project": {"name": "dc-test"},
        "racks": [
            {"id": "R1", "name": "R1", "max_u": max_u_r1},
            {"id": "R2", "name": "R2", "max_u": max_u_r2},
        ],
        "demands": [],
    }


# ---------------------------------------------------------------------------
# Rack U capacity constraint
# ---------------------------------------------------------------------------


def test_max_u_default_is_42() -> None:
    """RackModel.max_u defaults to 42."""
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "x"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [],
        }
    )
    for rack in project.racks:
        assert rack.max_u == 42


def test_max_u_respected_for_mpo_overflow() -> None:
    """Requesting more MPO slots than max_u allows must produce an error, not silently overflow."""
    # 1 slot/U * max_u=1 → only 1 slot available per rack; 2 MPO demands → overflow
    payload = _base_two_racks(max_u_r1=1, max_u_r2=1)
    payload["settings"] = {"panel": {"slots_per_u": 1}}
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 24}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    assert len(result["errors"]) > 0
    assert any("max_u" in e or "exceeds" in e for e in result["errors"])


def test_max_u_respected_for_lc_overflow() -> None:
    """Requesting more LC slots than max_u allows must produce an error."""
    payload = _base_two_racks(max_u_r1=1, max_u_r2=1)
    payload["settings"] = {"panel": {"slots_per_u": 1}}
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mmf_lc_duplex", "count": 25}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    assert len(result["errors"]) > 0
    assert any("max_u" in e or "exceeds" in e for e in result["errors"])


def test_max_u_respected_for_utp_overflow() -> None:
    """Requesting more UTP ports than max_u allows must produce an error."""
    payload = _base_two_racks(max_u_r1=1, max_u_r2=1)
    payload["settings"] = {"panel": {"slots_per_u": 1}}
    # 1 slot at 6 ports/slot = 6 UTP ports max per rack; 7 requests overflow
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 7}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    assert len(result["errors"]) > 0
    assert any("max_u" in e or "exceeds" in e for e in result["errors"])


def test_no_errors_within_capacity() -> None:
    """Designs that fit within max_u must produce no rack overflow errors."""
    payload = _base_two_racks(max_u_r1=42, max_u_r2=42)
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 12}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    assert result["errors"] == []


# ---------------------------------------------------------------------------
# Sequential cable labels (cable_seq)
# ---------------------------------------------------------------------------


def test_cable_seq_assigned_sequentially() -> None:
    """Every cable must have a cable_seq field starting at 1 with no gaps."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 14}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    seqs = [c["cable_seq"] for c in result["cables"]]
    assert seqs == list(range(1, len(result["cables"]) + 1))


def test_cable_seq_mixed_media() -> None:
    """cable_seq is assigned across all media types with no duplicates."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 3},
        {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 2},
    ]
    result = allocate(ProjectInput.model_validate(payload))
    seqs = [c["cable_seq"] for c in result["cables"]]
    assert len(set(seqs)) == len(seqs), "cable_seq values must be unique"
    assert sorted(seqs) == list(range(1, len(result["cables"]) + 1))


def test_sessions_csv_includes_cable_seq() -> None:
    """sessions_csv must include the cable_seq column for field labelling."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 2}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    csv_text = sessions_csv(result, "prj_test", "rev_test")
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert "cable_seq" in reader.fieldnames  # type: ignore[operator]
    assert all(row["cable_seq"] != "" for row in rows)


# ---------------------------------------------------------------------------
# Bill of Materials (BOM) export
# ---------------------------------------------------------------------------


def test_bom_csv_contains_panels_modules_cables() -> None:
    """bom_csv must include rows for each item type."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1},
        {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 2},
    ]
    result = allocate(ProjectInput.model_validate(payload))
    csv_text = bom_csv(result)
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    item_types = {r["item_type"] for r in rows}
    assert "panel" in item_types
    assert "module" in item_types
    assert "cable" in item_types


def test_bom_csv_quantities_are_positive() -> None:
    """All BOM quantities must be positive integers."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mmf_lc_duplex", "count": 3}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    csv_text = bom_csv(result)
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        assert int(row["quantity"]) > 0


def test_bom_csv_panel_count_matches_result() -> None:
    """The sum of panel quantities in BOM must match result['metrics']['panel_count']."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 14}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    csv_text = bom_csv(result)
    reader = csv.DictReader(io.StringIO(csv_text))
    panel_qty = sum(int(r["quantity"]) for r in reader if r["item_type"] == "panel")
    assert panel_qty == result["metrics"]["panel_count"]


def test_bom_csv_cable_count_matches_result() -> None:
    """The sum of cable quantities in BOM must match result['metrics']['cable_count']."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 5},
        {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 3},
    ]
    result = allocate(ProjectInput.model_validate(payload))
    csv_text = bom_csv(result)
    reader = csv.DictReader(io.StringIO(csv_text))
    cable_qty = sum(int(r["quantity"]) for r in reader if r["item_type"] == "cable")
    assert cable_qty == result["metrics"]["cable_count"]
