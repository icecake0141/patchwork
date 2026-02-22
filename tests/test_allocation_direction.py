# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Tests for panel.allocation_direction (top_down / bottom_up) behavior."""

from __future__ import annotations

import pytest

from models import ProjectInput
from services.allocator import RackOverflowError, RackSlotAllocator, allocate

# ---------------------------------------------------------------------------
# Unit tests for RackSlotAllocator
# ---------------------------------------------------------------------------


def test_top_down_default_starts_at_u1() -> None:
    alloc = RackSlotAllocator("R1", slots_per_u=4, max_u=42)
    ref = alloc.reserve_slot()
    assert ref.u == 1
    assert ref.slot == 1


def test_top_down_slot_progression() -> None:
    alloc = RackSlotAllocator("R1", slots_per_u=4, max_u=42)
    refs = [alloc.reserve_slot() for _ in range(5)]
    assert [(r.u, r.slot) for r in refs] == [(1, 1), (1, 2), (1, 3), (1, 4), (2, 1)]


def test_bottom_up_starts_at_max_u() -> None:
    alloc = RackSlotAllocator("R1", slots_per_u=4, max_u=42, allocation_direction="bottom_up")
    ref = alloc.reserve_slot()
    assert ref.u == 42
    assert ref.slot == 1


def test_bottom_up_slot_progression() -> None:
    alloc = RackSlotAllocator("R1", slots_per_u=4, max_u=10, allocation_direction="bottom_up")
    refs = [alloc.reserve_slot() for _ in range(5)]
    assert [(r.u, r.slot) for r in refs] == [(10, 1), (10, 2), (10, 3), (10, 4), (9, 1)]


def test_top_down_overflow_raises() -> None:
    alloc = RackSlotAllocator("R1", slots_per_u=4, max_u=1)
    for _ in range(4):
        alloc.reserve_slot()
    with pytest.raises(RackOverflowError):
        alloc.reserve_slot()


def test_bottom_up_overflow_raises() -> None:
    alloc = RackSlotAllocator("R1", slots_per_u=4, max_u=1, allocation_direction="bottom_up")
    for _ in range(4):
        alloc.reserve_slot()
    with pytest.raises(RackOverflowError):
        alloc.reserve_slot()


# ---------------------------------------------------------------------------
# Integration tests via allocate()
# ---------------------------------------------------------------------------

_BASE = {
    "version": 1,
    "project": {"name": "dir_test"},
    "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
    "demands": [{"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 12}],
}


def test_allocate_top_down_panels_start_at_u1() -> None:
    project = ProjectInput.model_validate(
        {**_BASE, "settings": {"panel": {"allocation_direction": "top_down"}}}
    )
    result = allocate(project)
    r1_us = {m["panel_u"] for m in result["modules"] if m["rack_id"] == "R1"}
    assert r1_us == {1}


def test_allocate_bottom_up_panels_start_at_max_u() -> None:
    project = ProjectInput.model_validate(
        {
            **_BASE,
            "racks": [
                {"id": "R1", "name": "R1", "max_u": 42},
                {"id": "R2", "name": "R2", "max_u": 42},
            ],
            "settings": {"panel": {"allocation_direction": "bottom_up"}},
        }
    )
    result = allocate(project)
    r1_us = {m["panel_u"] for m in result["modules"] if m["rack_id"] == "R1"}
    assert r1_us == {42}


def test_allocate_bottom_up_multiple_panels_descend() -> None:
    # 20 mpo12 demands → 2 slots → 2 panels on each rack
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "dir_multi"},
            "racks": [
                {"id": "R1", "name": "R1", "max_u": 10},
                {"id": "R2", "name": "R2", "max_u": 10},
            ],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 20}
            ],
            "settings": {"panel": {"slots_per_u": 1, "allocation_direction": "bottom_up"}},
        }
    )
    result = allocate(project)
    r1_us = sorted({m["panel_u"] for m in result["modules"] if m["rack_id"] == "R1"})
    # slots_per_u=1, 2 slots needed → U10 and U9
    assert r1_us == [9, 10]


def test_allocate_bottom_up_overflow_reported() -> None:
    # slots_per_u=1 forces each slot to its own U; max_u=1 means only 1 U available
    # 20 mpo12 → ceil(20/12)=2 slots needed → second slot overflows on U0
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "overflow"},
            "racks": [
                {"id": "R1", "name": "R1", "max_u": 1},
                {"id": "R2", "name": "R2", "max_u": 1},
            ],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 20}
            ],
            "settings": {"panel": {"slots_per_u": 1, "allocation_direction": "bottom_up"}},
        }
    )
    result = allocate(project)
    assert result["errors"]


def test_model_rejects_invalid_allocation_direction() -> None:
    with pytest.raises(ValueError, match="unsupported allocation_direction"):
        ProjectInput.model_validate(
            {
                "version": 1,
                "project": {"name": "x"},
                "racks": [{"id": "R1", "name": "R1"}],
                "demands": [],
                "settings": {"panel": {"allocation_direction": "sideways"}},
            }
        )


def test_default_allocation_direction_is_top_down() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "default"},
            "racks": [{"id": "R1", "name": "R1"}],
            "demands": [],
        }
    )
    assert project.settings.panel.allocation_direction == "top_down"
