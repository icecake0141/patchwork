# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""SVG rendering utilities for topology, rack occupancy, and pair detail."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from services.allocator import pair_key


def render_topology_svg(result: dict[str, Any]) -> str:
    sessions = result["sessions"]
    agg: dict[tuple[str, str, str], int] = defaultdict(int)
    for s in sessions:
        a, b = sorted((s["src_rack"], s["dst_rack"]))
        agg[(a, b, s["media"])] += 1
    rows = "".join(
        f'<text x="10" y="{20 + i * 18}" font-size="12">{a} ↔ {b} [{m}] : {c}</text>'
        for i, ((a, b, m), c) in enumerate(sorted(agg.items()))
    )
    height = 40 + len(agg) * 18
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}"><text x="10" y="15" font-size="14">Rack Topology</text>{rows}</svg>'


def render_rack_panels_svg(result: dict[str, Any], rack_id: str) -> str:
    rack_panels = [p for p in result["panels"] if p["rack_id"] == rack_id]
    modules = [m for m in result["modules"] if m["rack_id"] == rack_id]
    by_uslot = {(m["panel_u"], m["slot"]): m for m in modules}
    lines = [f'<text x="10" y="18" font-size="14">Rack {rack_id} Panel Occupancy</text>']
    y = 40
    for panel in sorted(rack_panels, key=lambda p: p["u"]):
        lines.append(f'<text x="10" y="{y}" font-size="12">U{panel["u"]}</text>')
        for slot in range(1, panel["slots_per_u"] + 1):
            x = 80 + (slot - 1) * 190
            mod = by_uslot.get((panel["u"], slot))
            label = mod["module_type"] if mod else "empty"
            lines.append(
                f'<rect x="{x}" y="{y - 12}" width="180" height="18" fill="#eef" stroke="#225"/>'
            )
            lines.append(f'<text x="{x + 4}" y="{y}" font-size="10">S{slot}: {label}</text>')
        y += 28
    height = y + 20
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="880" height="{height}">{"".join(lines)}</svg>'


def render_pair_detail_svg(result: dict[str, Any], rack_a: str, rack_b: str) -> str:
    a, b = pair_key(rack_a, rack_b)
    key = f"{a}__{b}"
    details = result.get("pair_details", {}).get(key, [])
    rows = [f'<text x="10" y="18" font-size="14">Pair Detail {rack_a} ↔ {rack_b}</text>']
    for i, d in enumerate(details):
        y = 40 + i * 18
        sa = d["slot_a"]
        sb = d["slot_b"]
        rows.append(
            f'<text x="10" y="{y}" font-size="12">{d["type"]}: {sa["rack_id"]} U{sa["u"]}S{sa["slot"]} ↔ {sb["rack_id"]} U{sb["u"]}S{sb["slot"]} (ports used: {d["used"]})</text>'
        )
    h = 60 + len(details) * 18
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{h}">{"".join(rows)}</svg>'
