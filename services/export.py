# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Export helpers for sessions CSV, BOM CSV, and result JSON."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
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
