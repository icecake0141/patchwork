# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Export helpers for sessions CSV, BOM CSV, and result JSON."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from html import escape
from typing import Any

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


def bom_csv(result: dict[str, Any]) -> str:
    """Generate a Bill of Materials CSV summarising panels, modules, and cables by type."""
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

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=BOM_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
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

    width = 1280
    top = 88
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
        '<text x="1030" y="74" font-size="12" font-family="Arial, sans-serif" fill="#111827">Dst panel/slot</text>',
    ]

    y = top
    for src_rack, src_u, src_slot, dst_rack, dst_u, dst_slot, media in sorted_group_keys:
        sessions = groups[(src_rack, src_u, src_slot, dst_rack, dst_u, dst_slot, media)]
        stroke = media_color.get(media, "#334155")

        src_group_label = escape(f"{src_rack} U{src_u}S{src_slot}")
        dst_group_label = escape(f"{dst_rack} U{dst_u}S{dst_slot}")
        group_title = escape(f"{media} ({len(sessions)} connection{'s' if len(sessions) != 1 else ''})")

        lines.append(
            f'<rect x="18" y="{y - 16}" width="1244" height="{group_header_h + len(sessions) * row_h}" fill="#f8fafc" stroke="#e2e8f0"/>'
        )
        lines.append(
            f'<text x="24" y="{y}" font-size="12" font-family="Arial, sans-serif" font-weight="bold" fill="#111827">{src_group_label}</text>'
        )
        lines.append(
            f'<text x="430" y="{y}" font-size="12" font-family="Arial, sans-serif" font-weight="bold" fill="#111827">{group_title}</text>'
        )
        lines.append(
            f'<text x="1030" y="{y}" font-size="12" font-family="Arial, sans-serif" font-weight="bold" fill="#111827">{dst_group_label}</text>'
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
                f'<text x="430" y="{line_y}" font-size="11" font-family="Arial, sans-serif" fill="#1f2937">{cable_label}</text>'
            )
            lines.append(
                f'<text x="1030" y="{line_y}" font-size="11" font-family="Arial, sans-serif" fill="#1f2937">P{dst_port}</text>'
            )

        y += group_header_h + len(sessions) * row_h + group_gap

    lines.append("</svg>")
    return "".join(lines)


def integrated_wiring_svg(
    result: dict[str, Any],
    mode: str = "aggregate",
    media_filter: list[str] | set[str] | tuple[str, ...] | None = None,
) -> str:
    if mode not in {"aggregate", "detailed"}:
        raise ValueError("mode must be 'aggregate' or 'detailed'")

    selected_media = set(media_filter) if media_filter is not None else set(MEDIA_COLORS.keys())
    cable_seq_map = {c["cable_id"]: c.get("cable_seq", "") for c in result.get("cables", [])}
    slot_used_ports: dict[tuple[str, int, int], set[int]] = defaultdict(set)

    grouped_sessions: dict[tuple[str, int, int, str, int, int, str], list[dict[str, Any]]] = defaultdict(
        list
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
        grouped_sessions[key].sort(key=lambda s: (int(s["src_port"]), int(s["dst_port"])))

    max_ports_per_slot = max((len(ports) for ports in slot_used_ports.values()), default=1)
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

    node_positions: dict[tuple[str, int, int], tuple[float, float]] = {}
    panel_defs: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for panel in panels:
        rack_id = str(panel["rack_id"])
        u_value = int(panel["u"])
        slots_per_u = int(panel.get("slots_per_u", 1))
        panel_defs[rack_id].append((u_value, slots_per_u))
        for slot in range(1, slots_per_u + 1):
            panel_y = top + (u_value - 1) * u_step
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
        '<defs><clipPath id="integrated-viewport-clip"><rect x="0" y="92" width="100%" height="100%"/></clipPath></defs>',
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
            panel_y = top + (u_value - 1) * u_step
            panel_h = 36 + slot_box_h_max + (slots_per_u - 1) * slot_step
            lines.append(
                f'<rect x="{x - 78}" y="{panel_y}" width="156" height="{panel_h}" fill="#f8fafc" stroke="#cbd5e1" class="integrated-rack-element" data-rack="{escape(rack_id)}"/>'
            )
            lines.append(
                f'<text x="{x - 70}" y="{panel_y + 16}" font-size="11" font-family="Arial, sans-serif" fill="#475569" class="integrated-rack-element" data-rack="{escape(rack_id)}">U{u_value}</text>'
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
            by_cable: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for session in sessions:
                by_cable[str(session["cable_id"])].append(session)
            aggregate_rows: list[dict[str, Any]] = []
            for cable_id, cable_sessions in by_cable.items():
                cable_sessions.sort(key=lambda s: (int(s["src_port"]), int(s["dst_port"])))
                first = cable_sessions[0]
                src_ports = [int(s["src_port"]) for s in cable_sessions]
                dst_ports = [int(s["dst_port"]) for s in cable_sessions]
                src_min = min(src_ports)
                src_max = max(src_ports)
                dst_min = min(dst_ports)
                dst_max = max(dst_ports)
                src_port_text = f"P{src_min}" if src_min == src_max else f"P{src_min}-{src_max}"
                dst_port_text = f"P{dst_min}" if dst_min == dst_max else f"P{dst_min}-{dst_max}"
                port_text = (
                    f"P{src_min}→P{dst_min}"
                    if src_min == src_max and dst_min == dst_max
                    else f"P{src_min}-{src_max}→P{dst_min}-{dst_max}"
                )
                aggregate_rows.append(
                    {
                        "wire_id": cable_id,
                        "media": media,
                        "src_port": int(first["src_port"]),
                        "dst_port": int(first["dst_port"]),
                        "port_text": port_text,
                        "src_port_text": src_port_text,
                        "dst_port_text": dst_port_text,
                        "label": f"#{cable_seq_map.get(cable_id, '')} {cable_id} ({len(cable_sessions)} session{'s' if len(cable_sessions) != 1 else ''})",
                    }
                )
            aggregate_rows.sort(key=lambda row: (row["src_port"], row["dst_port"]))
            rows = aggregate_rows
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

        group_id = escape(
            f"{src_rack}_{src_u}_{src_slot}__{dst_rack}_{dst_u}_{dst_slot}__{media}"
        )
        for index, row in enumerate(rows):
            lane_offset = (index - (total - 1) / 2) * 8.0
            x1, y1 = src_pos
            x2, y2 = dst_pos
            src_rear_dx = 32 if rack_side[src_rack] == "left" else -32
            dst_rear_dx = 32 if rack_side[dst_rack] == "left" else -32
            src_rear_x = x1 + src_rear_dx
            dst_rear_x = x2 + dst_rear_dx
            src_snap_x = src_rear_x + (12 if src_rear_dx > 0 else -12)
            dst_snap_x = dst_rear_x + (12 if dst_rear_dx > 0 else -12)
            curve_strength = max(36.0, abs(dst_snap_x - src_snap_x) * 0.25)
            c1x = src_snap_x + (curve_strength if src_snap_x <= dst_snap_x else -curve_strength)
            c2x = dst_snap_x - (curve_strength if src_snap_x <= dst_snap_x else -curve_strength)
            c1y = y1 + lane_offset
            c2y = y2 + lane_offset

            wire_id = escape(str(row["wire_id"]))
            label = escape(str(row["label"]))
            lines.append(
                f'<path d="M {src_snap_x} {y1 + lane_offset} C {c1x} {c1y}, {c2x} {c2y}, {dst_snap_x} {y2 + lane_offset}" stroke="{color}" stroke-width="1.6" fill="none" opacity="0.85" class="integrated-wire integrated-filterable" data-wire-id="{wire_id}" data-media="{escape(media)}" data-src-rack="{escape(src_rack)}" data-dst-rack="{escape(dst_rack)}" data-group="{group_id}"><title>{label}</title></path>'
            )
            if mode == "aggregate":
                port_text = escape(str(row["port_text"]))
                mid_x = (src_snap_x + dst_snap_x) / 2 + 6 + (10 if index % 2 else -10)
                mid_y = (y1 + y2) / 2 + lane_offset - 4 + ((index % 3) - 1) * 9
                lines.append(
                    f'<text x="{mid_x}" y="{mid_y}" font-size="10" font-family="Arial, sans-serif" fill="#1f2937" class="integrated-port-label integrated-filterable" data-wire-id="{wire_id}" data-media="{escape(media)}" data-src-rack="{escape(src_rack)}" data-dst-rack="{escape(dst_rack)}">{port_text}</text>'
                )

    for (rack_id, u_value, slot_value), (x, y) in sorted(node_positions.items()):
        node_label = escape(f"{rack_id}-U{u_value}-S{slot_value}")
        if (rack_id, u_value, slot_value) in used_slots:
            rear_dx = 32 if rack_side[rack_id] == "left" else -32
            front_x = x - rear_dx
            rear_x = x + rear_dx
            ports = sorted(slot_used_ports.get((rack_id, u_value, slot_value), set()))
            shown_ports = len(ports)
            box_h = 24 + shown_ports * mapping_row_h + slot_inner_bottom
            box_y = y - box_h / 2
            box_x = min(front_x, rear_x) - 12
            box_w = abs(rear_x - front_x) + 24
            lines.append(
                f'<rect x="{box_x}" y="{box_y}" width="{box_w}" height="{box_h}" fill="none" stroke="#94a3b8" class="integrated-rack-element" data-rack="{escape(rack_id)}"/>'
            )
            lines.append(
                f'<line x1="{x}" y1="{box_y}" x2="{x}" y2="{box_y + box_h}" stroke="#94a3b8" stroke-width="1" class="integrated-rack-element" data-rack="{escape(rack_id)}"/>'
            )
            lines.append(
                f'<text x="{x - 8}" y="{box_y - 5}" font-size="12" font-family="Arial, sans-serif" fill="#0f172a" font-weight="bold" class="integrated-rack-element" data-rack="{escape(rack_id)}">S{slot_value}</text>'
            )
            front_label_x = front_x - 26 if rear_dx > 0 else front_x + 6
            rear_label_x = rear_x + 6 if rear_dx > 0 else rear_x - 28
            lines.append(
                f'<text x="{front_label_x}" y="{box_y + 14}" font-size="9" font-family="Arial, sans-serif" fill="#334155" class="integrated-rack-element" data-rack="{escape(rack_id)}">Front</text>'
            )
            lines.append(
                f'<text x="{rear_label_x}" y="{box_y + 14}" font-size="9" font-family="Arial, sans-serif" fill="#334155" class="integrated-rack-element" data-rack="{escape(rack_id)}">Rear</text>'
            )
            mapping_y = box_y + slot_inner_top + 6
            for idx, port in enumerate(ports):
                row_y = mapping_y + idx * mapping_row_h
                lines.append(
                    f'<text x="{front_x - (30 if rear_dx > 0 else -6)}" y="{row_y}" font-size="9" font-family="Arial, sans-serif" fill="#0f172a" class="integrated-port-label integrated-rack-element" data-rack="{escape(rack_id)}">P{port}</text>'
                )
                lines.append(
                    f'<line x1="{front_x}" y1="{row_y - 3}" x2="{rear_x}" y2="{row_y - 3}" stroke="#94a3b8" stroke-width="0.9" class="integrated-rack-element" data-rack="{escape(rack_id)}"/>'
                )
                lines.append(
                    f'<text x="{rear_x + (6 if rear_dx > 0 else -28)}" y="{row_y}" font-size="9" font-family="Arial, sans-serif" fill="#0f172a" class="integrated-port-label integrated-rack-element" data-rack="{escape(rack_id)}">P{port}</text>'
                )
        else:
            lines.append(
                f'<circle cx="{x}" cy="{y}" r="3.1" fill="#111827" class="integrated-node integrated-rack-element" data-node="{node_label}" data-rack="{escape(rack_id)}"/>'
            )
            lines.append(
                f'<text x="{x + 6}" y="{y + 3}" font-size="9" font-family="Arial, sans-serif" fill="#334155" class="integrated-rack-element" data-rack="{escape(rack_id)}">S{slot_value}</text>'
            )

    lines.extend(rack_label_lines)

    lines.append("</g>")
    lines.append("</svg>")
    return "".join(lines)
