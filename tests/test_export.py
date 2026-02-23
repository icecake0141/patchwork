# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

import copy
import xml.etree.ElementTree as ET

from models import ProjectInput
from services.allocator import allocate
from services.export import (
    _integrated_gap_scale,
    _integrated_wire_gap_overlays,
    integrated_wiring_drawio,
    integrated_wiring_interactive_svg,
    integrated_wiring_svg,
    rack_occupancy_drawio,
    svg_to_drawio,
    wiring_drawio,
    wiring_svg,
)
from services.render_svg import rack_slot_width, render_rack_panels_svg


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


def test_integrated_wiring_svg_aggregate_uses_single_line_per_slot_mapping() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-aggregate-concept"},
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

    svg_aggregate = integrated_wiring_svg(result, mode="aggregate")
    svg_detailed = integrated_wiring_svg(result, mode="detailed")

    aggregate_count = svg_aggregate.count('class="integrated-wire ')
    detailed_count = svg_detailed.count('class="integrated-wire ')

    assert aggregate_count == 1
    assert detailed_count == 2
    assert "U1S1↔U1S1" in svg_aggregate


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
    assert "occ 1/12" in detailed_svg
    assert 'data-slot-state="occupied"' in detailed_svg
    assert "P1→P1" in detailed_svg
    assert "U1S1↔U1S1" in aggregate_svg
    assert "ses/" in aggregate_svg


def test_integrated_wiring_svg_shows_utp_slot_capacity() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-utp-capacity"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {
                    "id": "D1",
                    "src": "R1",
                    "dst": "R2",
                    "endpoint_type": "utp_rj45",
                    "count": 1,
                }
            ],
        }
    )
    result = allocate(project)
    detailed_svg = integrated_wiring_svg(result, mode="detailed")

    assert "occ 1/6" in detailed_svg


def test_integrated_wire_gap_overlays_detects_crossing() -> None:
    overlays = _integrated_wire_gap_overlays(
        [
            {
                "order": 0,
                "wire_id": "w1",
                "media": "mpo12",
                "src_rack": "R1",
                "dst_rack": "R2",
                "group": "g1",
                "color": "#111111",
                "stroke_width": 1.6,
                "label": "w1",
                "curve": (20.0, 60.0, 40.0, 60.0, 80.0, 60.0, 100.0, 60.0),
            },
            {
                "order": 1,
                "wire_id": "w2",
                "media": "mmf_lc_duplex",
                "src_rack": "R2",
                "dst_rack": "R3",
                "group": "g2",
                "color": "#222222",
                "stroke_width": 1.6,
                "label": "w2",
                "curve": (60.0, 20.0, 60.0, 40.0, 60.0, 80.0, 60.0, 100.0),
            },
        ]
    )

    assert overlays
    assert abs(overlays[0]["x"] - 60.0) < 1.5
    assert abs(overlays[0]["y"] - 60.0) < 1.5
    assert overlays[0]["over"]["wire_id"] == "w2"


def test_integrated_gap_scale_reduces_in_high_density() -> None:
    low_density = _integrated_gap_scale(wire_count=20, overlay_count=10, overlays_on_wire=1)
    high_density = _integrated_gap_scale(wire_count=220, overlay_count=360, overlays_on_wire=20)

    assert 0.45 <= low_density <= 1.0
    assert 0.45 <= high_density <= 1.0
    assert high_density < low_density


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
    assert "jumpStyle=arc;" in drawio
    assert "jumpSize=6;" in drawio
    assert "Hello" in drawio
    assert "data:image/svg+xml," not in drawio


def test_svg_to_drawio_applies_group_translate_transform() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120">'
        '<g transform="translate(100,20)"><text x="10" y="20" font-size="12">Rack B</text></g>'
        "</svg>"
    )
    drawio = svg_to_drawio(svg, page_name="Translate")

    assert "Rack B" in drawio
    assert 'x="110.00"' in drawio


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
    assert "jumpStyle=arc;" in drawio


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
    assert "jumpStyle=arc;" in drawio
    assert "Front" in drawio
    assert "Rear" in drawio
    assert "occ 1/12" in drawio


def test_svg_to_drawio_preserves_opacity_style() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="90">'
        '<path d="M 10 40 C 40 10, 80 70, 120 40" stroke="#2563eb" stroke-width="2" opacity="0.85" fill="none"/>'
        '<text x="130" y="40" font-size="12" opacity="0.62">Label</text>'
        "</svg>"
    )
    drawio = svg_to_drawio(svg, page_name="Opacity")

    assert "opacity=85;" in drawio
    assert "opacity=62;" in drawio


def test_integrated_wiring_interactive_svg_contains_checkbox_filters() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-interactive-svg"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}
            ],
        }
    )
    result = allocate(project)

    svg = integrated_wiring_interactive_svg(result, mode="aggregate")

    assert svg.startswith("<svg")
    assert "<foreignObject" in svg
    assert 'data-role="integrated-media"' in svg
    assert 'data-role="integrated-rack"' in svg
    assert ".integrated-filterable" in svg
    assert "Legend" in svg
    assert "background:#7c3aed" in svg


def test_integrated_wiring_interactive_svg_is_well_formed_xml() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "integrated-interactive-xml"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}
            ],
        }
    )
    result = allocate(project)

    svg = integrated_wiring_interactive_svg(result, mode="aggregate")

    ET.fromstring(svg)


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


def test_rack_panel_svg_supports_uniform_slot_width_across_racks() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "rack-uniform-slot-width"},
            "racks": [
                {"id": "R1", "name": "R1"},
                {"id": "R2", "name": "R2"},
                {"id": "R3", "name": "R3"},
            ],
            "demands": [
                {
                    "id": "D1",
                    "src": "R1",
                    "dst": "R2",
                    "endpoint_type": "mpo12",
                    "count": 1,
                },
                {
                    "id": "D2",
                    "src": "R1",
                    "dst": "R3",
                    "endpoint_type": "utp_rj45",
                    "count": 2,
                },
            ],
        }
    )
    result = allocate(project)

    uniform_slot_width = rack_slot_width(result)
    rack_max_slot_width = max(
        rack_slot_width(result, "R1"),
        rack_slot_width(result, "R2"),
        rack_slot_width(result, "R3"),
    )
    svg_r1 = render_rack_panels_svg(result, "R1", slot_width=uniform_slot_width)
    svg_r2 = render_rack_panels_svg(result, "R2", slot_width=uniform_slot_width)
    svg_r3 = render_rack_panels_svg(result, "R3", slot_width=uniform_slot_width)

    assert uniform_slot_width == rack_max_slot_width
    assert f'width="{uniform_slot_width}"' in svg_r1
    assert f'width="{uniform_slot_width}"' in svg_r2
    assert f'width="{uniform_slot_width}"' in svg_r3
