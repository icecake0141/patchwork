# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

from models import ProjectInput
from services.allocator import allocate
from services.export import wiring_svg


def test_wiring_svg_contains_expected_labels() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "wiring"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 2}
            ],
        }
    )
    result = allocate(project)
    svg = wiring_svg(result)

    assert svg.startswith("<svg")
    assert "Cable Wiring Diagram" in svg
    assert "R1 U1S1" in svg
    assert "R2 U1S1" in svg
    assert "mpo12" in svg
    assert "Grouped by panel/slot pair" in svg


def test_wiring_svg_sorts_ports_in_ascending_order() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "wiring-sort"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 3}
            ],
        }
    )
    result = allocate(project)
    svg = wiring_svg(result)

    i1 = svg.find("P1</text>")
    i2 = svg.find("P2</text>")
    i3 = svg.find("P3</text>")

    assert i1 != -1 and i2 != -1 and i3 != -1
    assert i1 < i2 < i3
