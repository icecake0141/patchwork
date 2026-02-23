# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

import copy

from models import ProjectInput
from services.allocator import allocate
from services.export import (
    integrated_wiring_drawio,
    integrated_wiring_svg,
    rack_occupancy_drawio,
    svg_to_drawio,
    wiring_drawio,
    wiring_svg,
)


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


def test_integrated_wiring_svg_contains_title_and_grouping_text() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-title"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 2}
            ],
        }
    )
    result = allocate(project)
    svg = integrated_wiring_svg(result, mode="aggregate")

    assert svg.startswith("<svg")
    assert "Integrated Wiring View" in svg
    assert "Grouped by panel/slot pair" in svg


def test_integrated_wiring_svg_detailed_port_sorting() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-sort"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 3}
            ],
        }
    )
    result = allocate(project)
    svg = integrated_wiring_svg(result, mode="detailed")

    i1 = svg.find("P1→P1")
    i2 = svg.find("P2→P2")
    i3 = svg.find("P3→P3")

    assert i1 != -1 and i2 != -1 and i3 != -1
    assert i1 < i2 < i3


def test_integrated_wiring_svg_mode_changes_wire_count() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-mode"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {
                    "id": "D1",
                    "src": "R1",
                    "dst": "R2",
                    "endpoint_type": "mmf_lc_duplex",
                    "count": 2,
                }
            ],
        }
    )
    result = allocate(project)
    patched = copy.deepcopy(result)
    patched["sessions"][1]["cable_id"] = patched["sessions"][0]["cable_id"]

    svg_aggregate = integrated_wiring_svg(patched, mode="aggregate")
    svg_detailed = integrated_wiring_svg(patched, mode="detailed")

    aggregate_count = svg_aggregate.count('class="integrated-wire ')
    detailed_count = svg_detailed.count('class="integrated-wire ')

    assert aggregate_count == 1
    assert detailed_count == 2


def test_integrated_wiring_svg_media_filter_excludes_other_media() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-media"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {
                    "id": "D1",
                    "src": "R1",
                    "dst": "R2",
                    "endpoint_type": "mmf_lc_duplex",
                    "count": 1,
                },
                {"id": "D2", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1},
            ],
        }
    )
    result = allocate(project)
    svg = integrated_wiring_svg(result, mode="detailed", media_filter=["mpo12"])

    assert 'data-media="mpo12"' in svg
    assert 'data-media="mmf_lc_duplex"' not in svg


def test_integrated_wiring_svg_contains_rack_metadata_for_filtering() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-rack-filter"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}
            ],
        }
    )
    result = allocate(project)
    svg = integrated_wiring_svg(result, mode="detailed")

    assert 'data-src-rack="R1"' in svg
    assert 'data-dst-rack="R2"' in svg
    assert 'class="integrated-rack-element"' in svg


def test_integrated_wiring_svg_draws_visible_port_labels() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-port-label"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {
                    "id": "D1",
                    "src": "R1",
                    "dst": "R2",
                    "endpoint_type": "mmf_lc_duplex",
                    "count": 1,
                }
            ],
        }
    )
    result = allocate(project)
    detailed_svg = integrated_wiring_svg(result, mode="detailed")
    aggregate_svg = integrated_wiring_svg(result, mode="aggregate")

    assert 'class="integrated-port-label integrated-rack-element"' in detailed_svg
    assert detailed_svg.count(">P1</text>") >= 2
    assert "Front" in detailed_svg
    assert "Rear" in detailed_svg
    assert "P1→P1" in detailed_svg
    assert "P1→P1" in aggregate_svg


def test_svg_to_drawio_converts_svg_primitives_to_editable_cells() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">'
        '<rect x="10" y="20" width="50" height="30" fill="#ffffff" stroke="#000000"/>'
        '<line x1="20" y1="80" x2="120" y2="80" stroke="#ff0000" stroke-width="2"/>'
        '<text x="30" y="40" font-size="12" fill="#111111">Hello</text>'
        "</svg>"
    )
    drawio = svg_to_drawio(svg, page_name="Test Wiring")

    assert drawio.startswith('<mxfile host="app.diagrams.net"')
    assert 'name="Test Wiring"' in drawio
    assert "<mxGraphModel" in drawio
    assert "shape=rectangle;" in drawio
    assert "edgeStyle=none;" in drawio
    assert "Hello" in drawio
    assert "data:image/svg+xml," not in drawio


def test_wiring_drawio_contains_encoded_wiring_svg() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "wiring-drawio"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}
            ],
        }
    )
    result = allocate(project)

    drawio = wiring_drawio(result)

    assert '<diagram id="wiring" name="Cable Wiring">' in drawio
    assert "Cable Wiring Diagram" in drawio
    assert "shape=rectangle;" in drawio
    assert "edgeStyle=none;" in drawio


def test_integrated_wiring_drawio_contains_aggregate_and_detailed_pages() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-drawio"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {
                    "id": "D1",
                    "src": "R1",
                    "dst": "R2",
                    "endpoint_type": "mmf_lc_duplex",
                    "count": 1,
                }
            ],
        }
    )
    result = allocate(project)

    drawio = integrated_wiring_drawio(result)

    assert drawio.startswith('<mxfile host="app.diagrams.net"')
    assert 'name="Integrated Wiring (Aggregate)"' in drawio
    assert 'name="Integrated Wiring (Detailed)"' in drawio
    assert drawio.count("<diagram ") >= 2
    assert "curved=1;" in drawio


def test_rack_occupancy_drawio_is_combined_into_single_page() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "rack-drawio"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}
            ],
        }
    )
    result = allocate(project)

    drawio = rack_occupancy_drawio(result)

    assert drawio.startswith('<mxfile host="app.diagrams.net"')
    assert 'name="Rack Occupancy"' in drawio
    assert drawio.count("<diagram ") == 1
    assert "Rack R1 Panel Occupancy" in drawio
    assert "Rack R2 Panel Occupancy" in drawio
