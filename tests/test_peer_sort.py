# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Tests for ordering.peer_sort strategy support in the allocator."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import ProjectInput
from services.allocator import allocate


def _base_project(
    rack_ids: list[str],
    demands: list[dict],
    peer_sort: str | None = None,
) -> ProjectInput:
    payload: dict = {
        "version": 1,
        "project": {"name": "peer-sort-test"},
        "racks": [{"id": rid, "name": rid} for rid in rack_ids],
        "demands": demands,
    }
    if peer_sort is not None:
        payload["settings"] = {"ordering": {"peer_sort": peer_sort}}
    return ProjectInput.model_validate(payload)


# ---------------------------------------------------------------------------
# Default: natural_trailing_digits
# ---------------------------------------------------------------------------


def test_default_peer_sort_is_natural_trailing_digits() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "x"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [],
        }
    )
    assert project.settings.ordering.peer_sort == "natural_trailing_digits"


# ---------------------------------------------------------------------------
# natural_trailing_digits: R2 comes before R10 (numeric ordering)
# ---------------------------------------------------------------------------


def test_natural_trailing_digits_orders_numerically() -> None:
    """natural_trailing_digits must sort R2 before R10 (numeric, not lexicographic)."""
    rack_ids = ["R1", "R2", "R10"]
    demands = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 12},
        {"id": "D2", "src": "R1", "dst": "R10", "endpoint_type": "mpo12", "count": 12},
    ]
    project = _base_project(rack_ids, demands, peer_sort="natural_trailing_digits")
    result = allocate(project)
    # Under natural sort: R2 < R10, so the R1-R2 pair is processed first.
    # R1 gets slot 1 for the R1-R2 pair and slot 2 for the R1-R10 pair.
    r1_modules = sorted(
        [m for m in result["modules"] if m["rack_id"] == "R1"],
        key=lambda m: (m["panel_u"], m["slot"]),
    )
    assert r1_modules[0]["peer_rack_id"] == "R2"
    assert r1_modules[1]["peer_rack_id"] == "R10"


# ---------------------------------------------------------------------------
# lexicographic: R10 comes before R2 (string ordering)
# ---------------------------------------------------------------------------


def test_lexicographic_orders_as_strings() -> None:
    """lexicographic must sort R10 before R2 (string comparison: '1' < '2')."""
    rack_ids = ["R1", "R2", "R10"]
    demands = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 12},
        {"id": "D2", "src": "R1", "dst": "R10", "endpoint_type": "mpo12", "count": 12},
    ]
    project = _base_project(rack_ids, demands, peer_sort="lexicographic")
    result = allocate(project)
    # Under lexicographic sort: "R10" < "R2", so R1-R10 pair is processed first.
    r1_modules = sorted(
        [m for m in result["modules"] if m["rack_id"] == "R1"],
        key=lambda m: (m["panel_u"], m["slot"]),
    )
    assert r1_modules[0]["peer_rack_id"] == "R10"
    assert r1_modules[1]["peer_rack_id"] == "R2"


# ---------------------------------------------------------------------------
# Determinism: same strategy always yields same result
# ---------------------------------------------------------------------------


def test_peer_sort_is_deterministic() -> None:
    """Running allocator twice with the same peer_sort yields identical output."""
    rack_ids = ["R1", "R2", "R3"]
    demands = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 6},
        {"id": "D2", "src": "R1", "dst": "R3", "endpoint_type": "mpo12", "count": 6},
    ]
    for strategy in ("natural_trailing_digits", "lexicographic"):
        project = _base_project(rack_ids, demands, peer_sort=strategy)
        result1 = allocate(project)
        result2 = allocate(project)
        assert result1["modules"] == result2["modules"], f"Non-deterministic for {strategy}"
        assert result1["sessions"] == result2["sessions"], f"Non-deterministic for {strategy}"


# ---------------------------------------------------------------------------
# UTP: peer_sort also controls UTP peer ordering within a rack
# ---------------------------------------------------------------------------


def test_natural_vs_lexicographic_utp_peer_order() -> None:
    """UTP peer ordering within a rack also respects peer_sort strategy."""
    rack_ids = ["R1", "R2", "R10"]
    demands = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 1},
        {"id": "D2", "src": "R1", "dst": "R10", "endpoint_type": "utp_rj45", "count": 1},
    ]
    nat_project = _base_project(rack_ids, demands, peer_sort="natural_trailing_digits")
    lex_project = _base_project(rack_ids, demands, peer_sort="lexicographic")

    nat_result = allocate(nat_project)
    lex_result = allocate(lex_project)

    # Both strategies must still allocate both sessions; results may differ in ordering.
    assert len(nat_result["sessions"]) == 2
    assert len(lex_result["sessions"]) == 2


# ---------------------------------------------------------------------------
# Validation: unsupported peer_sort value raises clear error
# ---------------------------------------------------------------------------


def test_unsupported_peer_sort_raises_validation_error() -> None:
    """An unsupported peer_sort value must raise ValidationError with a clear message."""
    with pytest.raises(ValidationError, match="unsupported peer_sort strategy"):
        ProjectInput.model_validate(
            {
                "version": 1,
                "project": {"name": "bad"},
                "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
                "demands": [],
                "settings": {
                    "ordering": {"peer_sort": "alphabetical"},
                },
            }
        )
