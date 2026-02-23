# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Export helpers for sessions CSV, BOM CSV, and result JSON."""

from __future__ import annotations

import csv
import io
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from html import escape
from typing import Any

from services.render_svg import rack_slot_width, render_rack_panels_svg

SESSION_COLUMNS = [
    "project_id",
    "revision_id",
    "session_id",
    "media",
    "cable_id",
    "cable_seq",
    "adapter_type",
    "label_a",
    "label_b",
    "src_rack",
    "src_face",
    "src_u",
    "src_slot",
    "src_port",
    "dst_rack",
    "dst_face",
    "dst_u",
    "dst_slot",
    "dst_port",
    "fiber_a",
    "fiber_b",
    "notes",
]

BOM_COLUMNS = [
    "item_type",
    "description",
    "quantity",
]

MEDIA_COLORS = {
    "mmf_lc_duplex": "#2563eb",
    "smf_lc_duplex": "#16a34a",
    "mpo12": "#7c3aed",
    "utp_rj45": "#ea580c",
}

SLOT_PORT_CAPACITY = {
    "utp_6xrj45": 6,
    "mpo12_pass_through_12port": 12,
    "lc_breakout_2xmpo12_to_12xlcduplex": 12,
}

RACK_OCCUPANCY_MODULE_COLORS = {
    "empty": "#555555",
    "mpo12_pass_through_12port": "#FF00FF",
    "lc_breakout_2xmpo12_to_12xlcduplex": "#87CEEB",
    "utp_6xrj45": "#90EE90",
}

MEDIA_LAYOUT_PROFILES: dict[str, dict[str, Any]] = {
    "mmf_lc_duplex": {
        "layout_id": "lc_duplex",
        "port_order": "pair_asc",
        "pair_span": 2,
        "label": "LC pair",
    },
    "smf_lc_duplex": {
        "layout_id": "lc_duplex",
        "port_order": "pair_asc",
        "pair_span": 2,
        "label": "LC pair",
    },
    "mpo12": {
        "layout_id": "mpo12",
        "port_order": "lane_asc",
        "pair_span": 12,
        "label": "MPO lane",
    },
    "utp_rj45": {
        "layout_id": "utp_rj45",
        "port_order": "pin_asc",
        "pair_span": 1,
        "label": "UTP pin",
    },
}

MODULE_LAYOUT_MEDIA = {
    "utp_6xrj45": "utp_rj45",
    "mpo12_pass_through_12port": "mpo12",
    "lc_breakout_2xmpo12_to_12xlcduplex": "mmf_lc_duplex",
}


def _media_layout_profile(media: str) -> dict[str, Any]:
    return MEDIA_LAYOUT_PROFILES.get(
        media,
        {
            "layout_id": "generic",
            "port_order": "asc",
            "pair_span": 1,
            "label": "Generic",
        },
    )


def _module_layout_profile(module_type: str, fiber_kind: str | None = None) -> dict[str, Any]:
    media = MODULE_LAYOUT_MEDIA.get(module_type, "")
    if module_type == "lc_breakout_2xmpo12_to_12xlcduplex" and fiber_kind == "smf":
        media = "smf_lc_duplex"
    return _media_layout_profile(media)


def _media_port_sort_key(media: str, src_port: int, dst_port: int) -> tuple[int, int, int, int]:
    profile = _media_layout_profile(media)
    pair_span = max(1, int(profile.get("pair_span", 1)))
    pair_group = (src_port - 1) // pair_span
    intra_pair = (src_port - 1) % pair_span
    return (pair_group, intra_pair, src_port, dst_port)


def _ordered_ports_for_layout(profile: dict[str, Any], capacity: int) -> list[int]:
    if capacity <= 0:
        return []
    return list(range(1, capacity + 1))


def _slot_state_theme(module_type: str, slot_state: str) -> dict[str, str]:
    base = RACK_OCCUPANCY_MODULE_COLORS.get(module_type, "#94a3b8")
    if slot_state == "full":
        slot_opacity = "0.26"
        front_opacity = "0.18"
        rear_opacity = "0.30"
    elif slot_state == "partial":
        slot_opacity = "0.20"
        front_opacity = "0.14"
        rear_opacity = "0.24"
    else:
        slot_opacity = "0.12"
        front_opacity = "0.09"
        rear_opacity = "0.16"

    return {
        "slot_fill": base,
        "front_fill": base,
        "rear_fill": base,
        "anchor_front_fill": "#ffffff",
        "anchor_rear_fill": "#ffffff",
        "border": base,
        "lane": base,
        "slot_opacity": slot_opacity,
        "front_opacity": front_opacity,
        "rear_opacity": rear_opacity,
    }


def _cubic_point(
    curve: tuple[float, float, float, float, float, float, float, float], t: float
) -> tuple[float, float]:
    x1, y1, c1x, c1y, c2x, c2y, x2, y2 = curve
    mt = 1.0 - t
    x = (mt**3) * x1 + 3.0 * (mt**2) * t * c1x + 3.0 * mt * (t**2) * c2x + (t**3) * x2
    y = (mt**3) * y1 + 3.0 * (mt**2) * t * c1y + 3.0 * mt * (t**2) * c2y + (t**3) * y2
    return (x, y)


def _sample_cubic(
    curve: tuple[float, float, float, float, float, float, float, float],
    steps: int = 28,
) -> list[tuple[float, float]]:
    return [_cubic_point(curve, i / steps) for i in range(steps + 1)]


def _segment_intersection(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> tuple[float, float, float, float] | None:
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    dx12 = x2 - x1
    dy12 = y2 - y1
    dx34 = x4 - x3
    dy34 = y4 - y3
    denom = dx12 * dy34 - dy12 * dx34
    if abs(denom) < 1e-9:
        return None

    dx13 = x3 - x1
    dy13 = y3 - y1
    ua = (dx13 * dy34 - dy13 * dx34) / denom
    ub = (dx13 * dy12 - dy13 * dx12) / denom
    eps = 1e-6
    if not (-eps <= ua <= 1.0 + eps and -eps <= ub <= 1.0 + eps):
        return None

    ix = x1 + ua * dx12
    iy = y1 + ua * dy12
    return (ix, iy, ua, ub)


def _integrated_wire_gap_overlays(wire_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(wire_entries) < 2:
        return []

    sampled: list[dict[str, Any]] = []
    for entry in wire_entries:
        points = _sample_cubic(entry["curve"])
        segments = [
            {
                "p1": points[idx],
                "p2": points[idx + 1],
                "idx": idx,
                "count": len(points) - 1,
            }
            for idx in range(len(points) - 1)
        ]
        sampled.append({"entry": entry, "segments": segments})

    overlays: list[dict[str, Any]] = []
    for under_index in range(len(sampled) - 1):
        under = sampled[under_index]
        for over_index in range(under_index + 1, len(sampled)):
            over = sampled[over_index]

            if under["entry"]["group"] == over["entry"]["group"]:
                continue

            for under_seg in under["segments"]:
                ux1, uy1 = under_seg["p1"]
                ux2, uy2 = under_seg["p2"]
                umin_x, umax_x = min(ux1, ux2), max(ux1, ux2)
                umin_y, umax_y = min(uy1, uy2), max(uy1, uy2)

                for over_seg in over["segments"]:
                    ox1, oy1 = over_seg["p1"]
                    ox2, oy2 = over_seg["p2"]
                    omin_x, omax_x = min(ox1, ox2), max(ox1, ox2)
                    omin_y, omax_y = min(oy1, oy2), max(oy1, oy2)
                    if umax_x < omin_x or omax_x < umin_x or umax_y < omin_y or omax_y < umin_y:
                        continue

                    intersection = _segment_intersection(
                        under_seg["p1"], under_seg["p2"], over_seg["p1"], over_seg["p2"]
                    )
                    if intersection is None:
                        continue

                    ix, iy, ua, ub = intersection
                    under_t = (under_seg["idx"] + ua) / max(1, under_seg["count"])
                    over_t = (over_seg["idx"] + ub) / max(1, over_seg["count"])
                    if under_t < 0.06 or under_t > 0.94 or over_t < 0.06 or over_t > 0.94:
                        continue

                    odx = ox2 - ox1
                    ody = oy2 - oy1
                    over_len = math.hypot(odx, ody)
                    if over_len < 1e-6:
                        continue

                    overlays.append(
                        {
                            "x": ix,
                            "y": iy,
                            "under": under["entry"],
                            "over": over["entry"],
                            "dx": odx / over_len,
                            "dy": ody / over_len,
                        }
                    )

    deduped: list[dict[str, Any]] = []
    for overlay in sorted(overlays, key=lambda o: (o["over"]["order"], o["x"], o["y"])):
        found_near = False
        for existing in deduped:
            if existing["over"]["order"] != overlay["over"]["order"]:
                continue
            if math.hypot(existing["x"] - overlay["x"], existing["y"] - overlay["y"]) < 6.0:
                found_near = True
                break
        if not found_near:
            deduped.append(overlay)

    return deduped


def _integrated_gap_scale(
    wire_count: int,
    overlay_count: int,
    overlays_on_wire: int = 0,
) -> float:
    """Return adaptive scale for SVG crossing gap/bridge size.

    As line density increases, the crossing jump is reduced to avoid visual clutter.
    """
    wire_density = max(0.0, (wire_count - 40.0) / 120.0)
    overlay_density = max(0.0, (overlay_count - 60.0) / 220.0)
    local_density = max(0.0, (overlays_on_wire - 3.0) / 12.0)

    density_score = min(1.0, max(wire_density, overlay_density))
    base_scale = 1.0 - 0.50 * density_score
    local_scale = 1.0 - 0.20 * min(1.0, local_density)
    return max(0.45, min(1.0, base_scale * local_scale))


def sessions_csv(result: dict[str, Any], project_id: str, revision_id: str | None = None) -> str:
    cable_seq_map = {c["cable_id"]: c.get("cable_seq", "") for c in result.get("cables", [])}
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=SESSION_COLUMNS)
    writer.writeheader()
    for s in result["sessions"]:
        row = {
            **s,
            "project_id": project_id,
            "revision_id": revision_id or "",
            "cable_seq": cable_seq_map.get(s["cable_id"], ""),
        }
        writer.writerow({k: row.get(k, "") for k in SESSION_COLUMNS})
    return buf.getvalue()


def bom_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Build Bill of Materials rows for UI and CSV exports."""
    rows: list[dict[str, Any]] = []

    panel_counts: Counter[str] = Counter()
    for p in result.get("panels", []):
        panel_counts[f"1U patch panel ({p['slots_per_u']} slots/U)"] += 1
    for desc, qty in sorted(panel_counts.items()):
        rows.append({"item_type": "panel", "description": desc, "quantity": qty})

    module_counts: Counter[str] = Counter()
    for m in result.get("modules", []):
        module_counts[m["module_type"]] += 1
    for desc, qty in sorted(module_counts.items()):
        rows.append({"item_type": "module", "description": desc, "quantity": qty})

    cable_counts: Counter[str] = Counter()
    for c in result.get("cables", []):
        parts = [c["cable_type"]]
        if c.get("fiber_kind"):
            parts.append(c["fiber_kind"])
        if c.get("polarity_type"):
            parts.append(f"polarity-{c['polarity_type']}")
        cable_counts[" ".join(parts)] += 1
    for desc, qty in sorted(cable_counts.items()):
        rows.append({"item_type": "cable", "description": desc, "quantity": qty})

    return rows


def bom_csv(result: dict[str, Any]) -> str:
    """Generate a Bill of Materials CSV summarising panels, modules, and cables by type."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=BOM_COLUMNS)
    writer.writeheader()
    writer.writerows(bom_rows(result))
    return buf.getvalue()


def result_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def wiring_svg(result: dict[str, Any]) -> str:
    cable_seq_map = {c["cable_id"]: c.get("cable_seq", 0) for c in result.get("cables", [])}

    groups: dict[tuple[str, int, int, str, int, int, str], list[dict[str, Any]]] = {}
    for session in result.get("sessions", []):
        key = (
            session["src_rack"],
            session["src_u"],
            session["src_slot"],
            session["dst_rack"],
            session["dst_u"],
            session["dst_slot"],
            session["media"],
        )
        groups.setdefault(key, []).append(session)

    sorted_group_keys = sorted(groups.keys())
    for key in sorted_group_keys:
        groups[key].sort(key=lambda session: (session["src_port"], session["dst_port"]))

    media_color = {
        "mmf_lc_duplex": "#2563eb",
        "smf_lc_duplex": "#16a34a",
        "mpo12": "#7c3aed",
        "utp_rj45": "#ea580c",
    }

    width = 1360
    top = 110
    group_header_h = 28
    row_h = 18
    group_gap = 16

    height = top + 20
    for key in sorted_group_keys:
        height += group_header_h + len(groups[key]) * row_h + group_gap

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        '<text x="20" y="30" font-size="20" font-family="Arial, sans-serif" font-weight="bold">Cable Wiring Diagram</text>',
        '<text x="20" y="52" font-size="12" fill="#4b5563" font-family="Arial, sans-serif">Grouped by panel/slot pair, sorted by source port number.</text>',
        '<text x="20" y="74" font-size="12" font-family="Arial, sans-serif" fill="#111827">Src panel/slot</text>',
        '<text x="430" y="74" font-size="12" font-family="Arial, sans-serif" fill="#111827">Cable / Media / Port mapping</text>',
        '<text x="1010" y="74" font-size="12" font-family="Arial, sans-serif" fill="#111827">Dst panel/slot</text>',
        '<text x="1120" y="74" font-size="12" font-family="Arial, sans-serif" fill="#111827">Cable ID</text>',
    ]

    y = top
    for src_rack, src_u, src_slot, dst_rack, dst_u, dst_slot, media in sorted_group_keys:
        sessions = groups[(src_rack, src_u, src_slot, dst_rack, dst_u, dst_slot, media)]
        stroke = media_color.get(media, "#334155")

        src_group_label = escape(f"{src_rack} U{src_u}S{src_slot}")
        dst_group_label = escape(f"{dst_rack} U{dst_u}S{dst_slot}")
        group_title = escape(
            f"{media} ({len(sessions)} connection{'s' if len(sessions) != 1 else ''})"
        )

        lines.append(
            f'<rect x="18" y="{y - 16}" width="1324" height="{group_header_h + len(sessions) * row_h}" fill="#f8fafc" stroke="#e2e8f0"/>'
        )
        lines.append(
            f'<text x="24" y="{y}" font-size="12" font-family="Arial, sans-serif" font-weight="bold" fill="#111827">{src_group_label}</text>'
        )
        lines.append(
            f'<text x="430" y="{y}" font-size="12" font-family="Arial, sans-serif" font-weight="bold" fill="#111827">{group_title}</text>'
        )
        lines.append(
            f'<text x="1010" y="{y}" font-size="12" font-family="Arial, sans-serif" font-weight="bold" fill="#111827">{dst_group_label}</text>'
        )

        for index, session in enumerate(sessions):
            line_y = y + 16 + index * row_h
            src_port = session["src_port"]
            dst_port = session["dst_port"]
            cable_seq = cable_seq_map.get(session["cable_id"], "")
            cable_label = escape(f"#{cable_seq} {session['cable_id']}")

            lines.append(
                f'<line x1="360" y1="{line_y - 4}" x2="980" y2="{line_y - 4}" stroke="{stroke}" stroke-width="1.6"/>'
            )
            lines.append(
                f'<text x="24" y="{line_y}" font-size="11" font-family="Arial, sans-serif" fill="#1f2937">P{src_port}</text>'
            )
            lines.append(
                f'<text x="430" y="{line_y}" font-size="11" font-family="Arial, sans-serif" fill="#1f2937">P{src_port}→P{dst_port}</text>'
            )
            lines.append(
                f'<text x="1010" y="{line_y}" font-size="11" font-family="Arial, sans-serif" fill="#1f2937">P{dst_port}</text>'
            )
            lines.append(
                f'<text x="1120" y="{line_y}" font-size="11" font-family="Arial, sans-serif" fill="#1f2937">{cable_label}</text>'
            )

        y += group_header_h + len(sessions) * row_h + group_gap

    lines.append("</svg>")
    return "".join(lines)


def integrated_wiring_svg(
    result: dict[str, Any],
    mode: str = "aggregate",
    media_filter: list[str] | set[str] | tuple[str, ...] | None = None,
    route_mode: str = "direct",
) -> str:
    if mode not in {"aggregate", "detailed"}:
        raise ValueError("mode must be 'aggregate' or 'detailed'")
    if route_mode not in {"direct", "detour", "highway", "stagger"}:
        raise ValueError("route_mode must be one of: direct, detour, highway, stagger")

    selected_media = set(media_filter) if media_filter is not None else set(MEDIA_COLORS.keys())
    cable_seq_map = {c["cable_id"]: c.get("cable_seq", "") for c in result.get("cables", [])}
    slot_used_ports: dict[tuple[str, int, int], set[int]] = defaultdict(set)
    module_capacity_by_slot: dict[tuple[str, int, int], int] = {
        (str(module["rack_id"]), int(module["panel_u"]), int(module["slot"])): SLOT_PORT_CAPACITY.get(
            str(module.get("module_type", "")), 0
        )
        for module in result.get("modules", [])
    }
    module_type_by_slot: dict[tuple[str, int, int], str] = {
        (str(module["rack_id"]), int(module["panel_u"]), int(module["slot"])): str(
            module.get("module_type", "empty")
        )
        for module in result.get("modules", [])
    }
    module_layout_by_slot: dict[tuple[str, int, int], dict[str, Any]] = {
        (str(module["rack_id"]), int(module["panel_u"]), int(module["slot"])): _module_layout_profile(
            str(module.get("module_type", "")),
            str(module.get("fiber_kind")) if module.get("fiber_kind") else None,
        )
        for module in result.get("modules", [])
    }

    grouped_sessions: dict[tuple[str, int, int, str, int, int, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for session in result.get("sessions", []):
        if session.get("media") not in selected_media:
            continue
        group_key = (
            session["src_rack"],
            int(session["src_u"]),
            int(session["src_slot"]),
            session["dst_rack"],
            int(session["dst_u"]),
            int(session["dst_slot"]),
            session["media"],
        )
        grouped_sessions[group_key].append(session)
        slot_used_ports[(session["src_rack"], int(session["src_u"]), int(session["src_slot"]))].add(
            int(session["src_port"])
        )
        slot_used_ports[(session["dst_rack"], int(session["dst_u"]), int(session["dst_slot"]))].add(
            int(session["dst_port"])
        )

    sorted_group_keys = sorted(grouped_sessions.keys())
    for key in sorted_group_keys:
        media = str(key[6])
        grouped_sessions[key].sort(
            key=lambda s: _media_port_sort_key(media, int(s["src_port"]), int(s["dst_port"]))
        )

    max_ports_per_slot = max(
        [
            *(len(ports) for ports in slot_used_ports.values()),
            *(
                module_capacity_by_slot.get((rack_id, u_value, slot_value), 0)
                for rack_id, u_value, slot_value in slot_used_ports.keys()
            ),
        ],
        default=1,
    )
    mapping_row_h = 11
    slot_inner_top = 24
    slot_inner_bottom = 12
    slot_box_h_max = 24 + max_ports_per_slot * mapping_row_h + slot_inner_bottom

    used_slots: set[tuple[str, int, int]] = set()
    for src_rack, src_u, src_slot, dst_rack, dst_u, dst_slot, _media in sorted_group_keys:
        used_slots.add((src_rack, src_u, src_slot))
        used_slots.add((dst_rack, dst_u, dst_slot))

    panels = result.get("panels", [])
    rack_ids = sorted({str(panel["rack_id"]) for panel in panels})
    rack_x = {rack_id: 180 + idx * 420 for idx, rack_id in enumerate(rack_ids)}
    rack_side: dict[str, str] = {}
    peer_positions: dict[str, list[float]] = defaultdict(list)
    for src_rack, _src_u, _src_slot, dst_rack, _dst_u, _dst_slot, _media in sorted_group_keys:
        if src_rack in rack_x and dst_rack in rack_x:
            peer_positions[src_rack].append(float(rack_x[dst_rack]))
            peer_positions[dst_rack].append(float(rack_x[src_rack]))
    for idx, rack_id in enumerate(rack_ids):
        peers = peer_positions.get(rack_id, [])
        if peers:
            avg_peer_x = sum(peers) / len(peers)
            rack_side[rack_id] = "left" if avg_peer_x > rack_x[rack_id] else "right"
        else:
            rack_side[rack_id] = "left" if idx < (len(rack_ids) / 2) else "right"
    max_slots_per_u = max((int(panel.get("slots_per_u", 1)) for panel in panels), default=1)

    max_u = max((int(panel["u"]) for panel in panels), default=1)
    slot_step = max(104, slot_box_h_max + 20)
    u_step = max(320, slot_step * max_slots_per_u + 110)
    top = 110
    rack_y_offset = {
        rack_id: (float(slot_step) if route_mode == "stagger" and idx % 2 == 1 else 0.0)
        for idx, rack_id in enumerate(rack_ids)
    }

    node_positions: dict[tuple[str, int, int], tuple[float, float]] = {}
    panel_defs: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for panel in panels:
        rack_id = str(panel["rack_id"])
        u_value = int(panel["u"])
        slots_per_u = int(panel.get("slots_per_u", 1))
        panel_defs[rack_id].append((u_value, slots_per_u))
        for slot in range(1, slots_per_u + 1):
            panel_y = top + (u_value - 1) * u_step + rack_y_offset[rack_id]
            y = panel_y + 18 + (slot_box_h_max / 2) + (slot - 1) * slot_step
            node_positions[(rack_id, u_value, slot)] = (rack_x[rack_id], y)

    width = max(1680, 360 + len(rack_ids) * 420)
    height = top + max_u * u_step + 220

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" data-role="integrated-wiring">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        '<text x="20" y="30" font-size="20" font-family="Arial, sans-serif" font-weight="bold">Integrated Wiring View</text>',
        '<text x="20" y="52" font-size="12" fill="#4b5563" font-family="Arial, sans-serif">Overlay of Rack Occupancy coordinates with inter-rack wiring.</text>',
        '<text x="20" y="72" font-size="12" fill="#4b5563" font-family="Arial, sans-serif">Grouped by panel/slot pair and sorted by source/destination port.</text>',
        '<text x="20" y="92" font-size="12" fill="#4b5563" font-family="Arial, sans-serif">Direction rule: Source column → Destination column, with media-specific fixed port order.</text>',
        f'<text x="20" y="108" font-size="11" fill="#64748b" font-family="Arial, sans-serif">Routing mode: {escape(route_mode)}</text>',
        '<defs><clipPath id="integrated-viewport-clip"><rect x="0" y="56" width="100%" height="100%"/></clipPath></defs>',
        '<g data-role="viewport" clip-path="url(#integrated-viewport-clip)">',
    ]

    rack_label_lines: list[str] = []

    for rack_id in rack_ids:
        x = rack_x[rack_id]
        rack_label_lines.append(
            f'<rect x="{x - 50}" y="{top - 40}" width="100" height="24" fill="#ffffff" opacity="0.9" class="integrated-rack-element" data-rack="{escape(rack_id)}"/>'
        )
        rack_label_lines.append(
            f'<text x="{x - 32}" y="{top - 24}" font-size="30" font-family="Arial, sans-serif" font-weight="bold" fill="#111827" class="integrated-rack-element" data-rack="{escape(rack_id)}">{escape(rack_id)}</text>'
        )
        for u_value, slots_per_u in sorted(panel_defs[rack_id], key=lambda value: value[0]):
            panel_y = top + (u_value - 1) * u_step + rack_y_offset[rack_id]
            panel_h = 36 + slot_box_h_max + (slots_per_u - 1) * slot_step
            lines.append(
                f'<rect x="{x - 78}" y="{panel_y}" width="156" height="{panel_h}" fill="#f8fafc" stroke="#cbd5e1" class="integrated-rack-element" data-rack="{escape(rack_id)}"/>'
            )
            lines.append(
                f'<text x="{x - 70}" y="{panel_y + 16}" font-size="11" font-family="Arial, sans-serif" fill="#475569" class="integrated-rack-element" data-rack="{escape(rack_id)}">U{u_value}</text>'
            )

    wire_entries: list[dict[str, Any]] = []
    wire_label_lines: list[str] = []
    wire_order = 0
    node_lines: list[str] = []
    slot_anchor_positions: dict[tuple[str, int, int, int], tuple[float, float]] = {}
    slot_side_positions: dict[tuple[str, int, int], tuple[float, float, float]] = {}

    for (rack_id, u_value, slot_value), (x, y) in sorted(node_positions.items()):
        node_label = escape(f"{rack_id}-U{u_value}-S{slot_value}")
        if (rack_id, u_value, slot_value) in used_slots:
            rear_dx = 32 if rack_side[rack_id] == "left" else -32
            front_x = x - rear_dx
            rear_x = x + rear_dx
            slot_side_positions[(rack_id, u_value, slot_value)] = (front_x, rear_x, rear_dx)

            ports = sorted(slot_used_ports.get((rack_id, u_value, slot_value), set()))
            ports_set = set(ports)
            shown_ports = len(ports)
            slot_capacity = module_capacity_by_slot.get((rack_id, u_value, slot_value), shown_ports)
            slot_capacity = max(slot_capacity, shown_ports)
            slot_layout_profile = module_layout_by_slot.get(
                (rack_id, u_value, slot_value),
                _media_layout_profile(""),
            )
            slot_module_type = module_type_by_slot.get((rack_id, u_value, slot_value), "empty")
            slot_port_order = str(slot_layout_profile.get("port_order", "asc"))
            slot_layout_label = str(slot_layout_profile.get("label", "Generic"))
            effective_ports_set = set(ports_set)
            occupancy_text = f"occ {shown_ports}/{slot_capacity}"
            active_mpo_groups: set[int] = set()
            if slot_module_type == "lc_breakout_2xmpo12_to_12xlcduplex":
                active_mpo_groups = {1 if int(port) <= 6 else 2 for port in ports_set}
                effective_ports_set = set()
                for mpo_group in active_mpo_groups:
                    if mpo_group == 1:
                        effective_ports_set.update(range(1, 7))
                    else:
                        effective_ports_set.update(range(7, 13))
                rear_used = len(active_mpo_groups)
                occupancy_text = f"occ rear {rear_used}/2"
                if rear_used == 0:
                    slot_state = "free"
                elif rear_used >= 2:
                    slot_state = "full"
                else:
                    slot_state = "partial"
            else:
                if shown_ports == 0:
                    slot_state = "free"
                elif shown_ports >= slot_capacity:
                    slot_state = "full"
                else:
                    slot_state = "partial"
            slot_theme = _slot_state_theme(
                slot_module_type,
                slot_state,
            )

            box_h = 24 + slot_capacity * mapping_row_h + slot_inner_bottom
            box_y = y - box_h / 2
            box_x = min(front_x, rear_x) - 12
            box_w = abs(rear_x - front_x) + 24
            node_lines.append(
                f'<rect x="{box_x}" y="{box_y}" width="{box_w}" height="{box_h}" fill="{slot_theme["slot_fill"]}" fill-opacity="{slot_theme["slot_opacity"]}" stroke="{slot_theme["border"]}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-slot-state="{slot_state}" data-layout-id="{escape(str(slot_layout_profile.get("layout_id", "generic")))}" data-port-order="{escape(slot_port_order)}"/>'
            )
            col_w = 22
            front_col_x = front_x - col_w / 2
            rear_col_x = rear_x - col_w / 2
            node_lines.append(
                f'<rect x="{front_col_x}" y="{box_y + 18}" width="{col_w}" height="{box_h - 22}" fill="{slot_theme["front_fill"]}" fill-opacity="{slot_theme["front_opacity"]}" stroke="{slot_theme["border"]}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-slot-state="{slot_state}"/>'
            )
            node_lines.append(
                f'<rect x="{rear_col_x}" y="{box_y + 18}" width="{col_w}" height="{box_h - 22}" fill="{slot_theme["rear_fill"]}" fill-opacity="{slot_theme["rear_opacity"]}" stroke="{slot_theme["border"]}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-slot-state="{slot_state}"/>'
            )
            rear_lane_start_y = int(box_y + 19)
            rear_lane_end_y = int(box_y + box_h - 6)
            for lane_y in range(rear_lane_start_y, rear_lane_end_y, 6):
                node_lines.append(
                    f'<line x1="{rear_col_x + 1.2}" y1="{lane_y}" x2="{rear_col_x + col_w - 1.2}" y2="{lane_y + 4.2}" stroke="{slot_theme["lane"]}" stroke-width="0.6" opacity="0.55" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-slot-state="{slot_state}"/>'
                )
            node_lines.append(
                f'<line x1="{x}" y1="{box_y + 18}" x2="{x}" y2="{box_y + box_h - 2}" stroke="#94a3b8" stroke-width="1" class="integrated-rack-element" data-rack="{escape(rack_id)}"/>'
            )
            node_lines.append(
                f'<text x="{x - 8}" y="{box_y - 5}" font-size="12" font-family="Arial, sans-serif" fill="#0f172a" font-weight="bold" class="integrated-rack-element" data-rack="{escape(rack_id)}">S{slot_value}</text>'
            )
            node_lines.append(
                f'<text x="{x + 8}" y="{box_y - 5}" font-size="9" font-family="Arial, sans-serif" fill="#475569" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-slot-state="{slot_state}">{occupancy_text}</text>'
            )
            node_lines.append(
                f'<text x="{x + 68}" y="{box_y - 5}" font-size="8" font-family="Arial, sans-serif" fill="#64748b" class="integrated-rack-element" data-rack="{escape(rack_id)}">{escape(slot_layout_label)} / {escape(slot_port_order)}</text>'
            )
            front_label_x = front_x - 26 if rear_dx > 0 else front_x + 6
            rear_label_x = rear_x + 6 if rear_dx > 0 else rear_x - 28
            node_lines.append(
                f'<text x="{front_label_x}" y="{box_y + 14}" font-size="9" font-family="Arial, sans-serif" fill="#334155" class="integrated-rack-element" data-rack="{escape(rack_id)}">Front</text>'
            )
            node_lines.append(
                f'<text x="{rear_label_x}" y="{box_y + 14}" font-size="9" font-family="Arial, sans-serif" fill="#334155" class="integrated-rack-element" data-rack="{escape(rack_id)}">Rear</text>'
            )

            mapping_y = box_y + slot_inner_top + 6
            ordered_ports = _ordered_ports_for_layout(slot_layout_profile, slot_capacity)
            front_anchor_w = 14.0
            front_anchor_h = 8.0
            front_inner_edge_x = (
                front_x + (front_anchor_w / 2.0) if front_x < rear_x else front_x - (front_anchor_w / 2.0)
            )

            port_row_y = {
                int(port): mapping_y + idx * mapping_row_h for idx, port in enumerate(ordered_ports)
            }
            mpo_group_anchor_y: dict[int, float] = {}
            rear_anchor_w_by_port: dict[int, float] = {}
            rear_outer_edge_x_by_port: dict[int, float] = {}
            rear_inner_edge_x_by_port: dict[int, float] = {}

            if slot_module_type == "lc_breakout_2xmpo12_to_12xlcduplex":
                mpo_groups = {
                    1: [port for port in ordered_ports if int(port) <= 6],
                    2: [port for port in ordered_ports if int(port) >= 7],
                }
                mpo_anchor_w = 22.0
                mpo_anchor_h = 10.0
                for mpo_index, group_ports in mpo_groups.items():
                    if not group_ports:
                        continue
                    group_state = "occupied" if mpo_index in active_mpo_groups else "free"
                    group_opacity = "0.95" if group_state == "occupied" else "0.30"
                    anchor_y = (
                        sum((port_row_y[int(port)] - 3.0) for port in group_ports) / len(group_ports)
                    )
                    mpo_group_anchor_y[mpo_index] = anchor_y
                    mpo_inner_edge_x = (
                        rear_x - (mpo_anchor_w / 2.0)
                        if rear_x > front_x
                        else rear_x + (mpo_anchor_w / 2.0)
                    )
                    mpo_outer_edge_x = (
                        rear_x + (mpo_anchor_w / 2.0)
                        if rear_x > front_x
                        else rear_x - (mpo_anchor_w / 2.0)
                    )
                    node_lines.append(
                        f'<rect x="{rear_x - mpo_anchor_w / 2}" y="{anchor_y - mpo_anchor_h / 2}" width="{mpo_anchor_w}" height="{mpo_anchor_h}" rx="1.2" ry="1.2" fill="{slot_theme["anchor_rear_fill"]}" stroke="{slot_theme["border"]}" opacity="{group_opacity}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-port-state="{group_state}" data-port-anchor="rear"/>'
                    )
                    node_lines.append(
                        f'<line x1="{rear_x - mpo_anchor_w / 2 + 1.0}" y1="{anchor_y - 1.4}" x2="{rear_x + mpo_anchor_w / 2 - 1.0}" y2="{anchor_y + 1.9}" stroke="{slot_theme["lane"]}" stroke-width="0.6" opacity="0.60" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-port-state="{group_state}"/>'
                    )
                    node_lines.append(
                        f'<text x="{rear_x}" y="{anchor_y + 2.4}" font-size="6.2" text-anchor="middle" font-family="Arial, sans-serif" fill="#334155" opacity="{group_opacity}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-port-state="{group_state}" data-anchor-port-label="1">MPO{mpo_index}</text>'
                    )
                    p_range_text = "P1-P6" if mpo_index == 1 else "P7-P12"
                    node_lines.append(
                        f'<text x="{rear_x}" y="{anchor_y + 7.0}" font-size="5.2" text-anchor="middle" font-family="Arial, sans-serif" fill="#475569" opacity="{group_opacity}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-port-state="{group_state}" data-anchor-port-label="1">{p_range_text}</text>'
                    )
                    for port in group_ports:
                        port_key = int(port)
                        rear_anchor_w_by_port[port_key] = mpo_anchor_w
                        rear_outer_edge_x_by_port[port_key] = mpo_outer_edge_x
                        rear_inner_edge_x_by_port[port_key] = mpo_inner_edge_x
                        slot_anchor_positions[(rack_id, u_value, slot_value, port_key)] = (
                            mpo_outer_edge_x,
                            anchor_y,
                        )
            else:
                rear_anchor_w = 14.0
                rear_inner_edge_x = (
                    rear_x - (rear_anchor_w / 2.0) if rear_x > front_x else rear_x + (rear_anchor_w / 2.0)
                )
                rear_outer_edge_x = (
                    rear_x + (rear_anchor_w / 2.0) if rear_x > front_x else rear_x - (rear_anchor_w / 2.0)
                )
                for port in ordered_ports:
                    port_key = int(port)
                    rear_anchor_w_by_port[port_key] = rear_anchor_w
                    rear_outer_edge_x_by_port[port_key] = rear_outer_edge_x
                    rear_inner_edge_x_by_port[port_key] = rear_inner_edge_x
                    slot_anchor_positions[(rack_id, u_value, slot_value, port_key)] = (
                        rear_outer_edge_x,
                        port_row_y[port_key] - 3.0,
                    )

            for idx, port in enumerate(ordered_ports):
                row_y = mapping_y + idx * mapping_row_h
                anchor_y = row_y - 3
                port_state = "occupied" if port in effective_ports_set else "free"
                line_opacity = "1.0" if port_state == "occupied" else "0.30"
                port_key = int(port)
                rear_anchor_w = rear_anchor_w_by_port.get(port_key, 14.0)
                rear_inner_edge_x = rear_inner_edge_x_by_port.get(port_key, rear_x)
                node_lines.append(
                    f'<rect x="{front_x - front_anchor_w / 2}" y="{anchor_y - front_anchor_h / 2}" width="{front_anchor_w}" height="{front_anchor_h}" rx="1.2" ry="1.2" fill="{slot_theme["anchor_front_fill"]}" stroke="{slot_theme["border"]}" opacity="{line_opacity}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-port-state="{port_state}" data-port-anchor="front"/>'
                )
                node_lines.append(
                    f'<text x="{front_x}" y="{anchor_y + 2.2}" font-size="6.6" text-anchor="middle" font-family="Arial, sans-serif" fill="#334155" opacity="{line_opacity}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-port-state="{port_state}" data-anchor-port-label="1">P{port}</text>'
                )
                if slot_module_type != "lc_breakout_2xmpo12_to_12xlcduplex":
                    node_lines.append(
                        f'<rect x="{rear_x - rear_anchor_w / 2}" y="{anchor_y - 4}" width="{rear_anchor_w}" height="8" rx="1.2" ry="1.2" fill="{slot_theme["anchor_rear_fill"]}" stroke="{slot_theme["border"]}" opacity="{line_opacity}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-port-state="{port_state}" data-port-anchor="rear"/>'
                    )
                    node_lines.append(
                        f'<line x1="{rear_x - rear_anchor_w / 2 + 1.0}" y1="{anchor_y - 1.1}" x2="{rear_x + rear_anchor_w / 2 - 1.0}" y2="{anchor_y + 1.6}" stroke="{slot_theme["lane"]}" stroke-width="0.5" opacity="0.60" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-port-state="{port_state}"/>'
                    )
                    node_lines.append(
                        f'<text x="{rear_x}" y="{anchor_y + 2.2}" font-size="6.6" text-anchor="middle" font-family="Arial, sans-serif" fill="#334155" opacity="{line_opacity}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-port-state="{port_state}" data-anchor-port-label="1">P{port}</text>'
                    )

                rear_target_y = (
                    mpo_group_anchor_y[1] if slot_module_type == "lc_breakout_2xmpo12_to_12xlcduplex" and int(port) <= 6
                    else mpo_group_anchor_y[2] if slot_module_type == "lc_breakout_2xmpo12_to_12xlcduplex" and 7 <= int(port) <= 12
                    else anchor_y
                )
                node_lines.append(
                    f'<line x1="{front_inner_edge_x}" y1="{anchor_y}" x2="{rear_inner_edge_x}" y2="{rear_target_y}" stroke="#94a3b8" stroke-width="0.9" opacity="{line_opacity}" class="integrated-rack-element" data-rack="{escape(rack_id)}" data-slot-state="{slot_state}" data-port-state="{port_state}"/>'
                )
        else:
            node_lines.append(
                f'<circle cx="{x}" cy="{y}" r="3.1" fill="#111827" class="integrated-node integrated-rack-element" data-node="{node_label}" data-rack="{escape(rack_id)}"/>'
            )
            node_lines.append(
                f'<text x="{x + 6}" y="{y + 3}" font-size="9" font-family="Arial, sans-serif" fill="#334155" class="integrated-rack-element" data-rack="{escape(rack_id)}">S{slot_value}</text>'
            )

    for group_key in sorted_group_keys:
        src_rack, src_u, src_slot, dst_rack, dst_u, dst_slot, media = group_key
        sessions = grouped_sessions[group_key]
        color = MEDIA_COLORS.get(media, "#334155")

        src_pos = node_positions.get((src_rack, src_u, src_slot))
        dst_pos = node_positions.get((dst_rack, dst_u, dst_slot))
        if not src_pos or not dst_pos:
            continue

        if mode == "aggregate":
            src_ports = [int(s["src_port"]) for s in sessions]
            dst_ports = [int(s["dst_port"]) for s in sessions]
            src_min = min(src_ports)
            src_max = max(src_ports)
            dst_min = min(dst_ports)
            dst_max = max(dst_ports)
            src_anchor_port = sorted(src_ports)[len(src_ports) // 2]
            dst_anchor_port = sorted(dst_ports)[len(dst_ports) // 2]
            cable_count = len({str(s["cable_id"]) for s in sessions})
            if src_min == src_max and dst_min == dst_max:
                port_span_text = f"P{src_min}→P{dst_min}"
            else:
                port_span_text = f"P{src_min}-P{src_max}→P{dst_min}-P{dst_max}"

            rows = [
                {
                    "wire_id": f"{src_rack}-{src_u}-{src_slot}__{dst_rack}-{dst_u}-{dst_slot}__{media}",
                    "media": media,
                    "src_port": src_anchor_port,
                    "dst_port": dst_anchor_port,
                    "port_text": (
                        f"U{src_u}S{src_slot}↔U{dst_u}S{dst_slot} "
                        f"({port_span_text}, {len(sessions)} ses/{cable_count} cab)"
                    ),
                    "label": (
                        f"{src_rack} U{src_u}S{src_slot} ↔ {dst_rack} U{dst_u}S{dst_slot} "
                        f"[{media}] {len(sessions)} sessions / {cable_count} cables"
                    ),
                }
            ]
        else:
            src_module_type = module_type_by_slot.get((src_rack, src_u, src_slot), "empty")
            dst_module_type = module_type_by_slot.get((dst_rack, dst_u, dst_slot), "empty")
            use_mpo_trunk_rows = (
                media.endswith("lc_duplex")
                and src_module_type == "lc_breakout_2xmpo12_to_12xlcduplex"
                and dst_module_type == "lc_breakout_2xmpo12_to_12xlcduplex"
            )

            if use_mpo_trunk_rows:
                mpo_groups: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
                for session in sessions:
                    src_port = int(session["src_port"])
                    dst_port = int(session["dst_port"])
                    src_mpo = 1 if src_port <= 6 else 2
                    dst_mpo = 1 if dst_port <= 6 else 2
                    mpo_groups[(src_mpo, dst_mpo)].append(session)

                rows = []
                for (src_mpo, dst_mpo), mpo_sessions in sorted(mpo_groups.items()):
                    if len(mpo_sessions) > 0:
                        src_anchor_port = 3 if src_mpo == 1 else 9
                        dst_anchor_port = 3 if dst_mpo == 1 else 9
                        trunk_count = len({str(s["cable_id"]) for s in mpo_sessions})
                        rows.append(
                            {
                                "wire_id": (
                                    f"{src_rack}-{src_u}-{src_slot}__{dst_rack}-{dst_u}-{dst_slot}"
                                    f"__{media}__MPO{src_mpo}-{dst_mpo}"
                                ),
                                "media": media,
                                "src_port": src_anchor_port,
                                "dst_port": dst_anchor_port,
                                "port_text": f"MPO{src_mpo}→MPO{dst_mpo}",
                                "src_port_text": f"MPO{src_mpo}",
                                "dst_port_text": f"MPO{dst_mpo}",
                                "label": (
                                    f"MPO{src_mpo}→MPO{dst_mpo} "
                                    f"({len(mpo_sessions)}x LC duplex / {trunk_count} trunks)"
                                ),
                            }
                        )
                    else:
                        rows.extend(
                            {
                                "wire_id": str(session["session_id"]),
                                "media": media,
                                "src_port": int(session["src_port"]),
                                "dst_port": int(session["dst_port"]),
                                "port_text": f"P{session['src_port']}→P{session['dst_port']}",
                                "src_port_text": f"P{session['src_port']}",
                                "dst_port_text": f"P{session['dst_port']}",
                                "label": f"P{session['src_port']}→P{session['dst_port']} #{cable_seq_map.get(session['cable_id'], '')}",
                            }
                            for session in mpo_sessions
                        )
            else:
                rows = [
                    {
                        "wire_id": str(session["session_id"]),
                        "media": media,
                        "src_port": int(session["src_port"]),
                        "dst_port": int(session["dst_port"]),
                        "port_text": f"P{session['src_port']}→P{session['dst_port']}",
                        "src_port_text": f"P{session['src_port']}",
                        "dst_port_text": f"P{session['dst_port']}",
                        "label": f"P{session['src_port']}→P{session['dst_port']} #{cable_seq_map.get(session['cable_id'], '')}",
                    }
                    for session in sessions
                ]

        total = len(rows)
        if total == 0:
            continue

        group_id = escape(f"{src_rack}_{src_u}_{src_slot}__{dst_rack}_{dst_u}_{dst_slot}__{media}")
        src_rack_x = rack_x.get(src_rack, 0.0)
        dst_rack_x = rack_x.get(dst_rack, 0.0)
        min_rack_x = min(src_rack_x, dst_rack_x)
        max_rack_x = max(src_rack_x, dst_rack_x)
        has_between_rack = any(
            min_rack_x < rack_x[candidate] < max_rack_x
            for candidate in rack_ids
            if candidate not in {src_rack, dst_rack}
        )
        for index, row in enumerate(rows):
            lane_offset = (index - (total - 1) / 2) * 8.0
            x1, y1 = src_pos
            x2, y2 = dst_pos
            src_side = slot_side_positions.get((src_rack, src_u, src_slot))
            dst_side = slot_side_positions.get((dst_rack, dst_u, dst_slot))
            if src_side is not None:
                _src_front_x, src_rear_x, src_rear_dx = src_side
            else:
                src_rear_dx = 32 if rack_side[src_rack] == "left" else -32
                src_rear_x = x1 + src_rear_dx
            if dst_side is not None:
                _dst_front_x, dst_rear_x, dst_rear_dx = dst_side
            else:
                dst_rear_dx = 32 if rack_side[dst_rack] == "left" else -32
                dst_rear_x = x2 + dst_rear_dx

            src_anchor = slot_anchor_positions.get((src_rack, src_u, src_slot, int(row["src_port"])))
            dst_anchor = slot_anchor_positions.get((dst_rack, dst_u, dst_slot, int(row["dst_port"])))
            if src_anchor is not None:
                src_rear_x, y1 = src_anchor
            if dst_anchor is not None:
                dst_rear_x, y2 = dst_anchor

            src_snap_x = src_rear_x
            dst_snap_x = dst_rear_x
            curve_strength = max(36.0, abs(dst_snap_x - src_snap_x) * 0.25)
            c1x = src_snap_x + (curve_strength if src_snap_x <= dst_snap_x else -curve_strength)
            c2x = dst_snap_x - (curve_strength if src_snap_x <= dst_snap_x else -curve_strength)
            c1y = y1 + lane_offset
            c2y = y2 + lane_offset

            use_top_route = False
            if route_mode == "highway":
                use_top_route = True
            elif route_mode == "detour" and has_between_rack:
                use_top_route = True

            if use_top_route:
                top_lane_base = 64.0
                top_lane = top_lane_base + (wire_order % 10) * 8.0
                if route_mode == "highway":
                    c1y = y1
                    c2y = y2
                else:
                    c1y = top_lane
                    c2y = top_lane

            wire_id = escape(str(row["wire_id"]))
            stroke_width = 2.2 if mode == "aggregate" else 1.6
            wire_curve: tuple[float, float, float, float, float, float, float, float] | None
            if route_mode == "highway":
                top_lane_base = 64.0
                top_lane = top_lane_base + (wire_order % 10) * 8.0
                path_d = (
                    f"M {src_snap_x} {y1} "
                    f"L {src_snap_x} {top_lane} "
                    f"L {dst_snap_x} {top_lane} "
                    f"L {dst_snap_x} {y2}"
                )
                wire_curve = None
            else:
                wire_curve = (
                    src_snap_x,
                    y1,
                    c1x,
                    c1y,
                    c2x,
                    c2y,
                    dst_snap_x,
                    y2,
                )
                path_d = (
                    f"M {wire_curve[0]} {wire_curve[1]} "
                    f"C {wire_curve[2]} {wire_curve[3]}, {wire_curve[4]} {wire_curve[5]}, {wire_curve[6]} {wire_curve[7]}"
                )
            wire_entries.append(
                {
                    "order": wire_order,
                    "wire_id": str(row["wire_id"]),
                    "media": media,
                    "src_rack": src_rack,
                    "dst_rack": dst_rack,
                    "group": group_id,
                    "color": color,
                    "stroke_width": stroke_width,
                    "label": str(row["label"]),
                    "path_d": path_d,
                    "curve": wire_curve,
                    "port_order": _media_layout_profile(media).get("port_order", "asc"),
                }
            )
            wire_order += 1

            if mode == "aggregate":
                port_text = escape(str(row["port_text"]))
                mid_x = (src_snap_x + dst_snap_x) / 2 + 8
                mid_y = (y1 + y2) / 2 + lane_offset - 6
                wire_label_lines.append(
                    f'<text x="{mid_x}" y="{mid_y}" font-size="10" font-family="Arial, sans-serif" fill="#1f2937" class="integrated-port-label integrated-filterable" data-wire-id="{wire_id}" data-media="{escape(media)}" data-src-rack="{escape(src_rack)}" data-dst-rack="{escape(dst_rack)}">{port_text}</text>'
                )
            else:
                port_text = escape(str(row["port_text"]))
                mid_x = (src_snap_x + dst_snap_x) / 2 + (8 if index % 2 else -8)
                mid_y = (y1 + y2) / 2 + lane_offset - 3 + ((index % 3) - 1) * 7
                wire_label_lines.append(
                    f'<text x="{mid_x}" y="{mid_y}" font-size="9" font-family="Arial, sans-serif" fill="#334155" opacity="0.62" class="integrated-port-label integrated-filterable" data-wire-id="{wire_id}" data-media="{escape(media)}" data-src-rack="{escape(src_rack)}" data-dst-rack="{escape(dst_rack)}">{port_text}</text>'
                )

    lines.extend(node_lines)

    for wire in wire_entries:
        lines.append(
            f'<path d="{wire["path_d"]}" stroke="{wire["color"]}" stroke-width="{wire["stroke_width"]}" fill="none" opacity="0.85" class="integrated-wire integrated-filterable" data-wire-id="{escape(wire["wire_id"])}" data-media="{escape(wire["media"])}" data-src-rack="{escape(wire["src_rack"])}" data-dst-rack="{escape(wire["dst_rack"])}" data-group="{wire["group"]}" data-direction="src-to-dst" data-port-order="{escape(str(wire["port_order"]))}"><title>{escape(wire["label"])} </title></path>'
        )

    curved_wire_entries = [entry for entry in wire_entries if entry.get("curve") is not None]
    overlays = _integrated_wire_gap_overlays(curved_wire_entries)
    overlays_by_over_wire: Counter[str] = Counter(
        str(overlay["over"]["wire_id"]) for overlay in overlays
    )

    for overlay in overlays:
        over_wire = overlay["over"]
        under_wire = overlay["under"]
        scale = _integrated_gap_scale(
            wire_count=len(wire_entries),
            overlay_count=len(overlays),
            overlays_on_wire=overlays_by_over_wire.get(str(over_wire["wire_id"]), 0),
        )
        gap_radius = max(
            2.0,
            max(under_wire["stroke_width"], over_wire["stroke_width"]) * 1.9 * scale,
        )
        bridge_half_len = max(3.0, over_wire["stroke_width"] * 2.8 * scale)
        x = overlay["x"]
        y = overlay["y"]
        dx = overlay["dx"]
        dy = overlay["dy"]
        bx1 = x - dx * bridge_half_len
        by1 = y - dy * bridge_half_len
        bx2 = x + dx * bridge_half_len
        by2 = y + dy * bridge_half_len
        lines.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{gap_radius:.2f}" fill="#ffffff" class="integrated-wire-gap integrated-filterable" data-wire-id="{escape(over_wire["wire_id"])}" data-media="{escape(over_wire["media"])}" data-src-rack="{escape(over_wire["src_rack"])}" data-dst-rack="{escape(over_wire["dst_rack"])}" data-gap-center-x="{x:.2f}" data-gap-center-y="{y:.2f}" data-gap-base-radius="{gap_radius:.3f}" data-gap-auto-scale="{scale:.3f}"/>'
        )
        lines.append(
            f'<line x1="{bx1:.2f}" y1="{by1:.2f}" x2="{bx2:.2f}" y2="{by2:.2f}" stroke="{over_wire["color"]}" stroke-width="{over_wire["stroke_width"]}" stroke-linecap="round" opacity="0.90" class="integrated-wire-overpass integrated-filterable" data-wire-id="{escape(over_wire["wire_id"])}" data-media="{escape(over_wire["media"])}" data-src-rack="{escape(over_wire["src_rack"])}" data-dst-rack="{escape(over_wire["dst_rack"])}" data-gap-center-x="{x:.2f}" data-gap-center-y="{y:.2f}" data-gap-dx="{dx:.5f}" data-gap-dy="{dy:.5f}" data-gap-base-half-len="{bridge_half_len:.3f}" data-gap-auto-scale="{scale:.3f}"/>'
        )

    lines.extend(wire_label_lines)

    lines.extend(rack_label_lines)

    lines.append("</g>")
    lines.append("</svg>")
    return "".join(lines)


def _svg_length_to_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    cleaned = text.replace("px", "")
    if cleaned.endswith("%"):
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


def _tag_name(xml_tag: str) -> str:
    if "}" in xml_tag:
        return xml_tag.rsplit("}", 1)[1]
    return xml_tag


def _parse_svg_path_cubic(
    path_d: str,
) -> tuple[float, float, float, float, float, float, float, float] | None:
    """Parse a simple SVG cubic path: M x1 y1 C c1x c1y, c2x c2y, x2 y2."""
    tokens = re.findall(r"[A-Za-z]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", path_d)
    if len(tokens) < 10:
        return None
    if tokens[0] != "M" or tokens[3] != "C":
        return None
    try:
        x1 = float(tokens[1])
        y1 = float(tokens[2])
        c1x = float(tokens[4])
        c1y = float(tokens[5])
        c2x = float(tokens[6])
        c2y = float(tokens[7])
        x2 = float(tokens[8])
        y2 = float(tokens[9])
    except ValueError:
        return None
    return (x1, y1, c1x, c1y, c2x, c2y, x2, y2)


def _parse_translate(transform: str | None) -> tuple[float, float]:
    if not transform:
        return (0.0, 0.0)
    match = re.search(
        r"translate\(\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(?:[ ,]\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?))?\s*\)",
        transform,
    )
    if not match:
        return (0.0, 0.0)
    tx = float(match.group(1))
    ty = float(match.group(2)) if match.group(2) is not None else 0.0
    return (tx, ty)


def _svg_opacity_to_drawio(value: str | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        opacity = float(text)
    except ValueError:
        return None
    clamped = max(0.0, min(1.0, opacity))
    return int(round(clamped * 100.0))


def _svg_to_mx_graph_model(svg_text: str) -> str:
    root = ET.fromstring(svg_text)
    width = _svg_length_to_float(root.get("width"), 1280.0)
    height = _svg_length_to_float(root.get("height"), 720.0)

    lines = [
        f'<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(width + 120)}" pageHeight="{int(height + 120)}" math="0" shadow="0">',
        "<root>",
        '<mxCell id="0"/>',
        '<mxCell id="1" parent="0"/>',
    ]

    next_id = 2

    def visit_element(element: ET.Element, parent_tx: float = 0.0, parent_ty: float = 0.0) -> None:
        nonlocal next_id
        local_tx, local_ty = _parse_translate(element.get("transform"))
        tx = parent_tx + local_tx
        ty = parent_ty + local_ty
        tag = _tag_name(element.tag)
        class_name = str(element.get("class", ""))
        if "integrated-wire-gap" in class_name or "integrated-wire-overpass" in class_name:
            for child in element:
                visit_element(child, tx, ty)
            return

        if tag == "rect":
            x = _svg_length_to_float(element.get("x"), 0.0) + tx
            y = _svg_length_to_float(element.get("y"), 0.0) + ty
            rect_w = _svg_length_to_float(element.get("width"), 0.0)
            rect_h = _svg_length_to_float(element.get("height"), 0.0)
            fill = element.get("fill", "none")
            stroke = element.get("stroke", "none")
            opacity = _svg_opacity_to_drawio(element.get("opacity"))
            style = (
                "shape=rectangle;whiteSpace=wrap;html=1;rounded=0;"
                f"fillColor={fill};strokeColor={stroke};"
            )
            if opacity is not None:
                style += f"opacity={opacity};"
            lines.append(
                f'<mxCell id="{next_id}" value="" style="{escape(style, quote=True)}" vertex="1" parent="1">'
            )
            lines.append(
                f'<mxGeometry x="{x:.2f}" y="{y:.2f}" width="{rect_w:.2f}" height="{rect_h:.2f}" as="geometry"/>'
            )
            lines.append("</mxCell>")
            next_id += 1

        elif tag == "line":
            x1 = _svg_length_to_float(element.get("x1"), 0.0) + tx
            y1 = _svg_length_to_float(element.get("y1"), 0.0) + ty
            x2 = _svg_length_to_float(element.get("x2"), 0.0) + tx
            y2 = _svg_length_to_float(element.get("y2"), 0.0) + ty
            stroke = element.get("stroke", "#1f2937")
            stroke_width = _svg_length_to_float(element.get("stroke-width"), 1.0)
            opacity = _svg_opacity_to_drawio(element.get("opacity"))
            style = (
                "edgeStyle=none;html=1;rounded=0;"
                f"strokeColor={stroke};strokeWidth={stroke_width:.2f};"
                "endArrow=none;startArrow=none;jumpStyle=arc;jumpSize=6;"
            )
            if opacity is not None:
                style += f"opacity={opacity};"
            lines.append(
                f'<mxCell id="{next_id}" value="" style="{escape(style, quote=True)}" edge="1" parent="1">'
            )
            lines.append('<mxGeometry relative="1" as="geometry">')
            lines.append(f'<mxPoint x="{x1:.2f}" y="{y1:.2f}" as="sourcePoint"/>')
            lines.append(f'<mxPoint x="{x2:.2f}" y="{y2:.2f}" as="targetPoint"/>')
            lines.append("</mxGeometry>")
            lines.append("</mxCell>")
            next_id += 1

        elif tag == "path":
            path_d = element.get("d", "")
            parsed = _parse_svg_path_cubic(path_d)
            if parsed is not None:
                x1, y1, c1x, c1y, c2x, c2y, x2, y2 = parsed
                x1 += tx
                y1 += ty
                c1x += tx
                c1y += ty
                c2x += tx
                c2y += ty
                x2 += tx
                y2 += ty
                stroke = element.get("stroke", "#1f2937")
                stroke_width = _svg_length_to_float(element.get("stroke-width"), 1.0)
                opacity = _svg_opacity_to_drawio(element.get("opacity"))
                style = (
                    "edgeStyle=none;curved=1;html=1;rounded=0;"
                    f"strokeColor={stroke};strokeWidth={stroke_width:.2f};"
                    "endArrow=none;startArrow=none;jumpStyle=arc;jumpSize=6;"
                )
                if opacity is not None:
                    style += f"opacity={opacity};"
                lines.append(
                    f'<mxCell id="{next_id}" value="" style="{escape(style, quote=True)}" edge="1" parent="1">'
                )
                lines.append('<mxGeometry relative="1" as="geometry">')
                lines.append(f'<mxPoint x="{x1:.2f}" y="{y1:.2f}" as="sourcePoint"/>')
                lines.append(f'<mxPoint x="{x2:.2f}" y="{y2:.2f}" as="targetPoint"/>')
                lines.append('<Array as="points">')
                lines.append(f'<mxPoint x="{c1x:.2f}" y="{c1y:.2f}"/>')
                lines.append(f'<mxPoint x="{c2x:.2f}" y="{c2y:.2f}"/>')
                lines.append("</Array>")
                lines.append("</mxGeometry>")
                lines.append("</mxCell>")
                next_id += 1

        elif tag == "text":
            text_value = "".join(element.itertext()).strip()
            if text_value:
                x = _svg_length_to_float(element.get("x"), 0.0) + tx
                y = _svg_length_to_float(element.get("y"), 0.0) + ty
                font_size = _svg_length_to_float(element.get("font-size"), 12.0)
                fill = element.get("fill", "#111827")
                font_family = element.get("font-family", "Arial")
                weight = element.get("font-weight", "normal")
                font_style = "1" if str(weight).lower() == "bold" else "0"
                opacity = _svg_opacity_to_drawio(element.get("opacity"))
                text_w = max(40.0, len(text_value) * font_size * 0.62)
                text_h = max(14.0, font_size * 1.35)
                style = (
                    "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;"
                    f"fontSize={font_size:.0f};fontColor={fill};fontFamily={font_family};fontStyle={font_style};"
                )
                if opacity is not None:
                    style += f"opacity={opacity};"
                lines.append(
                    f'<mxCell id="{next_id}" value="{escape(text_value, quote=True)}" style="{escape(style, quote=True)}" vertex="1" parent="1">'
                )
                lines.append(
                    f'<mxGeometry x="{x:.2f}" y="{max(0.0, y - text_h + 2):.2f}" width="{text_w:.2f}" height="{text_h:.2f}" as="geometry"/>'
                )
                lines.append("</mxCell>")
                next_id += 1

        elif tag == "circle":
            cx = _svg_length_to_float(element.get("cx"), 0.0) + tx
            cy = _svg_length_to_float(element.get("cy"), 0.0) + ty
            radius = _svg_length_to_float(element.get("r"), 0.0)
            fill = element.get("fill", "none")
            stroke = element.get("stroke", "none")
            opacity = _svg_opacity_to_drawio(element.get("opacity"))
            d = radius * 2
            style = f"shape=ellipse;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
            if opacity is not None:
                style += f"opacity={opacity};"
            lines.append(
                f'<mxCell id="{next_id}" value="" style="{escape(style, quote=True)}" vertex="1" parent="1">'
            )
            lines.append(
                f'<mxGeometry x="{cx - radius:.2f}" y="{cy - radius:.2f}" width="{d:.2f}" height="{d:.2f}" as="geometry"/>'
            )
            lines.append("</mxCell>")
            next_id += 1

        for child in element:
            visit_element(child, tx, ty)

    visit_element(root)

    lines.extend(
        [
            "</root>",
            "</mxGraphModel>",
        ]
    )
    return "".join(lines)


def svg_to_drawio(svg_text: str, page_name: str = "Wiring") -> str:
    """Convert SVG text to editable Draw.io (.drawio) XML.

    Supported SVG primitives are mapped into Draw.io cells so that
    shapes and labels remain directly editable after import.
    """
    page_name_escaped = escape(page_name, quote=True)
    graph_model = _svg_to_mx_graph_model(svg_text)
    return (
        '<mxfile host="app.diagrams.net" modified="2026-02-23T00:00:00Z" agent="patchwork" version="22.1.0">'
        f'<diagram id="wiring" name="{page_name_escaped}">{graph_model}</diagram>'
        "</mxfile>"
    )


def svgs_to_drawio(pages: list[tuple[str, str]]) -> str:
    """Build a multi-page Draw.io document from SVG pages."""
    diagrams = []
    for index, (page_name, svg_text) in enumerate(pages, start=1):
        page_name_escaped = escape(page_name, quote=True)
        graph_model = _svg_to_mx_graph_model(svg_text)
        diagrams.append(
            f'<diagram id="page_{index}" name="{page_name_escaped}">{graph_model}</diagram>'
        )

    return (
        '<mxfile host="app.diagrams.net" modified="2026-02-23T00:00:00Z" agent="patchwork" version="22.1.0">'
        + "".join(diagrams)
        + "</mxfile>"
    )


def wiring_drawio(result: dict[str, Any]) -> str:
    """Build a Draw.io file from the generated wiring SVG."""
    return svg_to_drawio(wiring_svg(result), page_name="Cable Wiring")


def integrated_wiring_drawio(result: dict[str, Any]) -> str:
    """Build a multi-page Draw.io file for Integrated Wiring View modes."""
    pages = [
        ("Integrated Wiring (Aggregate)", integrated_wiring_svg(result, mode="aggregate")),
        ("Integrated Wiring (Detailed)", integrated_wiring_svg(result, mode="detailed")),
    ]
    return svgs_to_drawio(pages)


def integrated_wiring_interactive_svg(result: dict[str, Any], mode: str = "aggregate") -> str:
    """Build standalone integrated wiring SVG with checkbox filters embedded."""
    if mode not in {"aggregate", "detailed"}:
        raise ValueError("mode must be 'aggregate' or 'detailed'")

    base_svg = integrated_wiring_svg(result, mode=mode)
    root = ET.fromstring(base_svg)
    width = _svg_length_to_float(root.get("width"), 1680.0)
    height = _svg_length_to_float(root.get("height"), 860.0)

    media_types = sorted(
        {str(s.get("media", "")) for s in result.get("sessions", []) if s.get("media")}
    )
    rack_ids = sorted({str(panel["rack_id"]) for panel in result.get("panels", [])})

    media_controls = "".join(
        f'<label style="display:inline-flex;gap:4px;align-items:center;"><input type="checkbox" data-role="integrated-media" value="{escape(media, quote=True)}" checked="checked" />{escape(media)}</label>'
        for media in media_types
    )
    rack_controls = "".join(
        f'<label style="display:inline-flex;gap:4px;align-items:center;"><input type="checkbox" data-role="integrated-rack" value="{escape(rack_id, quote=True)}" checked="checked" />{escape(rack_id)}</label>'
        for rack_id in rack_ids
    )
    port_state_controls = "".join(
        [
            '<label style="display:inline-flex;gap:4px;align-items:center;"><input type="checkbox" data-role="integrated-port-state" value="occupied" checked="checked" />occupied</label>',
            '<label style="display:inline-flex;gap:4px;align-items:center;"><input type="checkbox" data-role="integrated-port-state" value="free" checked="checked" />free</label>',
        ]
    )
    anchor_label_controls = (
        '<label style="display:inline-flex;gap:4px;align-items:center;"><input type="checkbox" data-role="integrated-anchor-label-toggle" checked="checked" />show P# in anchor box</label>'
    )
    legend_items = "".join(
        f'<span style="display:inline-flex;gap:4px;align-items:center;"><span style="width:10px;height:10px;border-radius:2px;border:1px solid #9ca3af;background:{MEDIA_COLORS.get(media, "#334155")};"></span>{escape(media)}</span>'
        for media in media_types
    )

    controls_w = max(320.0, width - 32.0)
    media_controls_object = (
        f'<foreignObject x="16" y="8" width="{controls_w:.0f}" height="28">'
        '<div xmlns="http://www.w3.org/1999/xhtml" style="font-family: Arial, sans-serif; font-size: 11px; color: #111827; display: flex; gap: 10px; align-items: center; background: #ffffff; border: 1px solid #d1d5db; border-radius: 6px; padding: 3px 8px; overflow-x: auto; overflow-y: hidden; white-space: nowrap;">'
        '<span style="font-weight: 700;">Media Filter</span>'
        f"{media_controls}"
        "</div>"
        "</foreignObject>"
    )

    rack_controls_object = (
        f'<foreignObject x="16" y="40" width="{controls_w:.0f}" height="28">'
        '<div xmlns="http://www.w3.org/1999/xhtml" style="font-family: Arial, sans-serif; font-size: 11px; color: #111827; display: flex; gap: 10px; align-items: center; background: #ffffff; border: 1px solid #d1d5db; border-radius: 6px; padding: 3px 8px; overflow-x: auto; overflow-y: hidden; white-space: nowrap;">'
        '<span style="font-weight: 700;">Rack Filter</span>'
        f"{rack_controls}"
        "</div>"
        "</foreignObject>"
    )

    legend_object = (
        f'<foreignObject x="16" y="72" width="{controls_w:.0f}" height="28">'
        '<div xmlns="http://www.w3.org/1999/xhtml" style="font-family: Arial, sans-serif; font-size: 11px; color: #111827; display: flex; gap: 10px; align-items: center; background: #ffffff; border: 1px solid #d1d5db; border-radius: 6px; padding: 3px 8px; overflow-x: auto; overflow-y: hidden; white-space: nowrap;">'
        '<span style="font-weight: 700;">Legend</span>'
        f"{legend_items}"
        "</div>"
        "</foreignObject>"
    )

    port_state_object = (
        f'<foreignObject x="16" y="104" width="{controls_w:.0f}" height="28">'
        '<div xmlns="http://www.w3.org/1999/xhtml" style="font-family: Arial, sans-serif; font-size: 11px; color: #111827; display: flex; gap: 10px; align-items: center; background: #ffffff; border: 1px solid #d1d5db; border-radius: 6px; padding: 3px 8px; overflow-x: auto; overflow-y: hidden; white-space: nowrap;">'
        '<span style="font-weight: 700;">Port State</span>'
        f"{port_state_controls}"
        "</div>"
        "</foreignObject>"
    )

    anchor_label_object = (
        f'<foreignObject x="16" y="136" width="{controls_w:.0f}" height="28">'
        '<div xmlns="http://www.w3.org/1999/xhtml" style="font-family: Arial, sans-serif; font-size: 11px; color: #111827; display: flex; gap: 10px; align-items: center; background: #ffffff; border: 1px solid #d1d5db; border-radius: 6px; padding: 3px 8px; overflow-x: auto; overflow-y: hidden; white-space: nowrap;">'
        '<span style="font-weight: 700;">Anchor Label</span>'
        f"{anchor_label_controls}"
        "</div>"
        "</foreignObject>"
    )

    script = (
        "<script><![CDATA[(function(){"
        "const svg=(document.currentScript&&document.currentScript.ownerSVGElement)||document.documentElement;"
        "const getChecked=(selector)=>new Set(Array.from(svg.querySelectorAll(selector)).filter((el)=>el.checked).map((el)=>el.value));"
        "let highlightedWireId='';"
        "const apply=()=>{"
        "const selectedMedia=getChecked('input[data-role=\"integrated-media\"]');"
        "const selectedRacks=getChecked('input[data-role=\"integrated-rack\"]');"
        "const selectedPortStates=getChecked('input[data-role=\"integrated-port-state\"]');"
        "const showAnchorLabels=Array.from(svg.querySelectorAll('input[data-role=\"integrated-anchor-label-toggle\"]')).some((el)=>el.checked);"
        "let hasVisibleHighlighted=false;"
        "const wires=Array.from(svg.querySelectorAll('.integrated-filterable'));"
        "wires.forEach((wire)=>{"
        "const media=wire.getAttribute('data-media')||'';"
        "const srcRack=wire.getAttribute('data-src-rack')||'';"
        "const dstRack=wire.getAttribute('data-dst-rack')||'';"
        "const wireId=wire.getAttribute('data-wire-id')||'';"
        "const mediaVisible=selectedMedia.size===0?false:selectedMedia.has(media);"
        "const rackVisible=selectedRacks.has(srcRack)&&selectedRacks.has(dstRack);"
        "const visible=mediaVisible&&rackVisible;"
        "wire.style.display=visible?'':'none';"
        "if(visible&&highlightedWireId&&wireId===highlightedWireId){hasVisibleHighlighted=true;}"
        "});"
        "if(highlightedWireId&&!hasVisibleHighlighted){highlightedWireId='';}"
        "wires.forEach((wire)=>{"
        "const wireId=wire.getAttribute('data-wire-id')||'';"
        "if(!highlightedWireId||!wireId){wire.style.opacity='';return;}"
        "wire.style.opacity=wireId===highlightedWireId?'1':'0.12';"
        "});"
        "svg.querySelectorAll('.integrated-rack-element').forEach((el)=>{"
        "const rack=el.getAttribute('data-rack')||'';"
        "el.style.display=selectedRacks.has(rack)?'':'';"
        "});"
        "svg.querySelectorAll('[data-port-state]').forEach((el)=>{"
        "const rack=el.getAttribute('data-rack')||'';"
        "const portState=el.getAttribute('data-port-state')||'';"
        "const rackVisible=!rack||selectedRacks.has(rack);"
        "const stateVisible=selectedPortStates.has(portState);"
        "el.style.display=rackVisible&&stateVisible?'':'none';"
        "});"
        "svg.querySelectorAll('[data-anchor-port-label]').forEach((el)=>{"
        "const rack=el.getAttribute('data-rack')||'';"
        "const portState=el.getAttribute('data-port-state')||'';"
        "const rackVisible=!rack||selectedRacks.has(rack);"
        "const stateVisible=selectedPortStates.has(portState);"
        "el.style.display=showAnchorLabels&&rackVisible&&stateVisible?'':'none';"
        "});"
        "};"
        "svg.querySelectorAll('input[data-role=\"integrated-media\"],input[data-role=\"integrated-rack\"],input[data-role=\"integrated-port-state\"],input[data-role=\"integrated-anchor-label-toggle\"]').forEach((el)=>el.addEventListener('change',apply));"
        "svg.addEventListener('click',(event)=>{"
        "const target=event.target.closest('.integrated-filterable');"
        "if(!target){highlightedWireId='';apply();return;}"
        "const wireId=target.getAttribute('data-wire-id')||'';"
        "if(!wireId){return;}"
        "highlightedWireId=highlightedWireId===wireId?'':wireId;"
        "apply();"
        "});"
        "apply();"
        "})();]]></script>"
    )

    title_texts = {
        "Integrated Wiring View",
        "Overlay of Rack Occupancy coordinates with inter-rack wiring.",
        "Grouped by panel/slot pair and sorted by source/destination port.",
        "Direction rule: Source column → Destination column, with media-specific fixed port order.",
    }
    content_parts: list[str] = []
    for child in list(root):
        tag = _tag_name(child.tag)
        if tag == "rect":
            if (
                (child.get("x") in {"0", "0.0"})
                and (child.get("y") in {"0", "0.0"})
                and (child.get("fill") == "#ffffff")
            ):
                continue
        if tag == "text":
            text_value = "".join(child.itertext()).strip()
            if text_value in title_texts:
                continue
        content_parts.append(ET.tostring(child, encoding="unicode"))
    content_inner = "".join(content_parts)

    controls_block_h = 168.0
    title_y = controls_block_h + 6.0
    title_h = 96.0
    diagram_y = title_y + title_h + 8.0
    shift_y = diagram_y
    new_height = height + shift_y + 8.0
    diagram_h = max(100.0, new_height - diagram_y - 10.0)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{new_height:.0f}" viewBox="0 0 {width:.0f} {new_height:.0f}" data-role="integrated-wiring">'
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>'
        f'<rect x="10" y="4" width="{max(60.0, width - 20.0):.0f}" height="{controls_block_h:.0f}" fill="#f8fafc" stroke="#d1d5db"/>'
        f'<text x="18" y="16" font-size="11" font-family="Arial, sans-serif" font-weight="bold" fill="#0f172a">Controls</text>'
        f'<rect x="10" y="{title_y:.0f}" width="{max(60.0, width - 20.0):.0f}" height="{title_h:.0f}" fill="#ffffff" stroke="#d1d5db"/>'
        f'<text x="20" y="{title_y + 38:.0f}" font-size="38" font-family="Arial, sans-serif" font-weight="bold" fill="#111827">Integrated Wiring View</text>'
        f'<text x="20" y="{title_y + 56:.0f}" font-size="12" fill="#4b5563" font-family="Arial, sans-serif">Overlay of Rack Occupancy coordinates with inter-rack wiring.</text>'
        f'<text x="20" y="{title_y + 72:.0f}" font-size="12" fill="#4b5563" font-family="Arial, sans-serif">Grouped by panel/slot pair and sorted by source/destination port.</text>'
        f'<text x="20" y="{title_y + 88:.0f}" font-size="12" fill="#4b5563" font-family="Arial, sans-serif">Direction rule: Source column → Destination column, with media-specific fixed port order.</text>'
        f'<rect x="10" y="{diagram_y:.0f}" width="{max(60.0, width - 20.0):.0f}" height="{diagram_h:.0f}" fill="#ffffff" stroke="#d1d5db"/>'
        f'<text x="18" y="{diagram_y + 14:.0f}" font-size="11" font-family="Arial, sans-serif" font-weight="bold" fill="#0f172a">Wiring Diagram</text>'
        f"{media_controls_object}"
        f"{rack_controls_object}"
        f"{legend_object}"
        f"{port_state_object}"
        f"{anchor_label_object}"
        f'<g transform="translate(0,{shift_y:.0f})">{content_inner}</g>'
        f"{script}"
        "</svg>"
    )


def rack_occupancy_drawio(result: dict[str, Any]) -> str:
    """Build a single-page Draw.io file for Rack Occupancy across all racks."""
    rack_ids = sorted({str(panel["rack_id"]) for panel in result.get("panels", [])})
    if not rack_ids:
        return svg_to_drawio(
            '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="120"><text x="16" y="48" font-size="16" fill="#111827">No rack occupancy data available</text></svg>',
            page_name="Rack Occupancy",
        )

    global_slot_width = rack_slot_width(result)
    rack_svgs = [
        render_rack_panels_svg(result, rack_id, slot_width=global_slot_width)
        for rack_id in rack_ids
    ]
    parsed_roots = [ET.fromstring(svg_text) for svg_text in rack_svgs]
    rack_sizes = [
        (
            _svg_length_to_float(root.get("width"), 900.0),
            _svg_length_to_float(root.get("height"), 300.0),
        )
        for root in parsed_roots
    ]

    gap = 40.0
    margin = 20.0
    total_width = margin * 2 + max((width for width, _ in rack_sizes), default=900.0)
    total_height = (
        margin * 2 + sum(height for _, height in rack_sizes) + gap * max(0, len(rack_sizes) - 1)
    )

    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width:.0f}" height="{total_height:.0f}" viewBox="0 0 {total_width:.0f} {total_height:.0f}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
    ]

    cursor_y = margin
    for svg_text, (rack_w, _rack_h) in zip(rack_svgs, rack_sizes, strict=False):
        start_index = svg_text.find(">")
        end_index = svg_text.rfind("</svg>")
        inner = (
            svg_text[start_index + 1 : end_index] if start_index != -1 and end_index != -1 else ""
        )
        centered_x = margin + max(0.0, (total_width - margin * 2 - rack_w) / 2)
        chunks.append(f'<g transform="translate({centered_x:.1f},{cursor_y:.1f})">{inner}</g>')
        cursor_y += _rack_h + gap

    chunks.append("</svg>")
    combined_svg = "".join(chunks)
    return svg_to_drawio(combined_svg, page_name="Rack Occupancy")
