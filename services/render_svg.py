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
    "lc_breakout_2xmpo12_to_12xlcduplex": "#00FFFF",
    "utp_6xrj45": "#90EE90",
}


def _split_slot_label(slot: int, label: str) -> tuple[str, str | None]:
    prefix = f"S{slot}: "
    if " Type-" in label:
        base, variant = label.split(" Type-", 1)
        return f"{prefix}{base}", f"Type-{variant}"

    first_line_limit = 28
    if len(prefix) + len(label) <= first_line_limit:
        return f"{prefix}{label}", None

    split_at = label.rfind(" ", 0, max(1, first_line_limit - len(prefix)))
    if split_at <= 0:
        split_at = label.find(" ")
    if split_at <= 0:
        return f"{prefix}{label}", None
    first = label[:split_at].rstrip()
    second = label[split_at + 1 :].lstrip()
    return f"{prefix}{first}", second or None


def _normalize_mpo_pass_through_variant(variant: str | None) -> str:
    if not variant:
        return "B"
    compact = "".join(ch for ch in str(variant).upper() if ch.isalnum())
    if compact in {"TYPEA", "A"}:
        return "A"
    if compact in {"TYPEAF", "AF"}:
        return "AF"
    if compact in {"TYPEB", "B"}:
        return "B"
    return str(variant)


def _module_display_label(module: dict[str, Any] | None) -> str:
    if not module:
        return MODULE_LABELS["empty"] if "empty" in MODULE_LABELS else "empty"
    module_type = module["module_type"]
    label = MODULE_LABELS.get(module_type, module_type)
    if module_type not in {
        "mpo12_pass_through_12port",
        "lc_breakout_2xmpo12_to_12xlcduplex",
    }:
        return label
    variant = _normalize_mpo_pass_through_variant(module.get("polarity_variant"))
    if variant in {"A", "AF", "B"}:
        return f"{label} Type-{variant}"
    return f"{label} {variant}"


def _module_fill_color(module: dict[str, Any] | None) -> str:
    if not module:
        return MODULE_COLORS.get("empty", "#eef")
    module_type = str(module.get("module_type", "empty"))
    fiber_kind = str(module.get("fiber_kind") or "").lower()
    if module_type == "lc_breakout_2xmpo12_to_12xlcduplex":
        return "#FFD600" if fiber_kind == "smf" else "#00FFFF"
    if module_type == "mpo12_pass_through_12port":
        return "#FFD600" if fiber_kind == "smf" else "#FF00FF"
    return MODULE_COLORS.get(module_type, "#eef")


def rack_slot_width(result: dict[str, Any], rack_id: str | None = None) -> int:
    panels = [p for p in result["panels"] if rack_id is None or p["rack_id"] == rack_id]
    modules = [m for m in result["modules"] if rack_id is None or m["rack_id"] == rack_id]
    by_rack_uslot = {(m["rack_id"], m["panel_u"], m["slot"]): m for m in modules}

    max_label_chars = len("S1: empty")
    for panel in panels:
        panel_rack = panel["rack_id"]
        for slot in range(1, panel["slots_per_u"] + 1):
            mod = by_rack_uslot.get((panel_rack, panel["u"], slot))
            label = _module_display_label(mod)
            line1, line2 = _split_slot_label(slot, label)
            max_label_chars = max(max_label_chars, len(line1), len(line2 or ""))

    return max(90, int(max_label_chars * 5 + 10))


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
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}"><text x="10" y="15" font-size="14">Rack Topology (Demands)</text>{rows}</svg>'


def render_rack_panels_svg(
    result: dict[str, Any], rack_id: str, slot_width: int | None = None
) -> str:
    rack_panels = [p for p in result["panels"] if p["rack_id"] == rack_id]
    modules = [m for m in result["modules"] if m["rack_id"] == rack_id]
    by_uslot = {(m["panel_u"], m["slot"]): m for m in modules}
    project = result.get("project", {})
    panel_settings = project.get("settings", {}).get("panel", {})
    u_label_mode = panel_settings.get("u_label_mode", "ascending")
    racks = project.get("racks", [])
    rack_max_u = next((r.get("max_u", 42) for r in racks if r.get("id") == rack_id), 42)

    max_slots_per_u = 1
    for panel in rack_panels:
        max_slots_per_u = max(max_slots_per_u, panel["slots_per_u"])
    effective_slot_width = (
        slot_width if slot_width is not None else rack_slot_width(result, rack_id)
    )
    slot_gap = 10
    lines = [f'<text x="10" y="18" font-size="14">Rack {rack_id} Panel Occupancy</text>']
    y = 40
    for panel in sorted(rack_panels, key=lambda p: p["u"]):
        if u_label_mode == "descending":
            label_u = rack_max_u - panel["u"] + 1
        else:
            label_u = panel["u"]
        lines.append(f'<text x="10" y="{y}" font-size="12">U{label_u}</text>')
        for slot in range(1, panel["slots_per_u"] + 1):
            x = 80 + (slot - 1) * (effective_slot_width + slot_gap)
            mod = by_uslot.get((panel["u"], slot))
            module_type = mod["module_type"] if mod else "empty"
            label = _module_display_label(mod)
            fill_color = _module_fill_color(mod)
            lines.append(
                f'<rect x="{x}" y="{y - 14}" width="{effective_slot_width}" height="28" fill="{fill_color}" stroke="#225"><title>S{slot}: {label}</title></rect>'
            )
            text_color = "#fff" if module_type == "empty" else "#000"
            line1, line2 = _split_slot_label(slot, label)
            lines.append(f'<text x="{x + 4}" y="{y - 2}" font-size="9" fill="{text_color}">{line1}</text>')
            if line2:
                lines.append(
                    f'<text x="{x + 4}" y="{y + 8}" font-size="9" fill="{text_color}">{line2}</text>'
                )
        y += 34
    height = y + 20
    width = 80 + max_slots_per_u * (effective_slot_width + slot_gap) + 40
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
