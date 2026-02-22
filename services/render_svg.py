# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""SVG rendering utilities for topology, rack occupancy, and pair detail."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from services.allocator import pair_key


MODULE_LABELS = {
    "mpo12_pass_through_12port": "MPO-12 pass-through (12-port)",
    "lc_breakout_2xmpo12_to_12xlcduplex": "2x MPO-12 to 12x LC duplex Break-out",
    "utp_6xrj45": "6x RJ45 UTP",
}


MODULE_COLORS = {
    "empty": "#555555",
    "mpo12_pass_through_12port": "#FF00FF",
    "lc_breakout_2xmpo12_to_12xlcduplex": "#87CEEB",
    "utp_6xrj45": "#90EE90",
}


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

    max_label_chars = len("S1: empty")
    max_slots_per_u = 1
    for panel in rack_panels:
        max_slots_per_u = max(max_slots_per_u, panel["slots_per_u"])
        for slot in range(1, panel["slots_per_u"] + 1):
            mod = by_uslot.get((panel["u"], slot))
            module_type = mod["module_type"] if mod else "empty"
            label = MODULE_LABELS.get(module_type, module_type)
            max_label_chars = max(max_label_chars, len(f"S{slot}: {label}"))

    slot_width = max(180, max_label_chars * 6 + 12)
    slot_gap = 10
    lines = [f'<text x="10" y="18" font-size="14">Rack {rack_id} Panel Occupancy</text>']
    y = 40
    for panel in sorted(rack_panels, key=lambda p: p["u"]):
        lines.append(f'<text x="10" y="{y}" font-size="12">U{panel["u"]}</text>')
        for slot in range(1, panel["slots_per_u"] + 1):
            x = 80 + (slot - 1) * (slot_width + slot_gap)
            mod = by_uslot.get((panel["u"], slot))
            module_type = mod["module_type"] if mod else "empty"
            label = MODULE_LABELS.get(module_type, module_type)
            fill_color = MODULE_COLORS.get(module_type, "#eef")
            lines.append(
                f'<rect x="{x}" y="{y - 12}" width="{slot_width}" height="18" fill="{fill_color}" stroke="#225"/>'
            )
            text_color = "#fff" if module_type == "empty" else "#000"
            lines.append(
                f'<text x="{x + 4}" y="{y}" font-size="10" fill="{text_color}">S{slot}: {label}</text>'
            )
        y += 28
    height = y + 20
    width = 80 + max_slots_per_u * (slot_width + slot_gap) + 20
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">{"".join(lines)}</svg>'


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
