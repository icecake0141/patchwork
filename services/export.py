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
    rows_by_cable: dict[str, dict[str, Any]] = {}

    for session in result.get("sessions", []):
        cable_id = session["cable_id"]
        row = rows_by_cable.get(cable_id)
        if row is None:
            row = {
                "cable_id": cable_id,
                "cable_seq": cable_seq_map.get(cable_id, 0),
                "media": session["media"],
                "src_rack": session["src_rack"],
                "src_u": session["src_u"],
                "src_slot": session["src_slot"],
                "dst_rack": session["dst_rack"],
                "dst_u": session["dst_u"],
                "dst_slot": session["dst_slot"],
                "session_count": 0,
            }
            rows_by_cable[cable_id] = row
        row["session_count"] += 1

    rows = sorted(
        rows_by_cable.values(),
        key=lambda r: (r["cable_seq"] if isinstance(r["cable_seq"], int) else 0, r["cable_id"]),
    )

    media_color = {
        "mmf_lc_duplex": "#2563eb",
        "smf_lc_duplex": "#16a34a",
        "mpo12": "#7c3aed",
        "utp_rj45": "#ea580c",
    }

    row_h = 28
    top = 80
    height = top + len(rows) * row_h + 30
    width = 1200

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        '<text x="20" y="30" font-size="20" font-family="Arial, sans-serif" font-weight="bold">Cable Wiring Diagram</text>',
        '<text x="20" y="52" font-size="12" fill="#4b5563" font-family="Arial, sans-serif">One line per cable_id. Ports indicates how many sessions share the cable.</text>',
        '<text x="20" y="72" font-size="12" font-family="Arial, sans-serif" fill="#111827">Source</text>',
        '<text x="560" y="72" font-size="12" font-family="Arial, sans-serif" fill="#111827">Cable</text>',
        '<text x="930" y="72" font-size="12" font-family="Arial, sans-serif" fill="#111827">Destination</text>',
    ]

    for idx, row in enumerate(rows):
        y = top + idx * row_h
        stroke = media_color.get(row["media"], "#334155")
        src_label = escape(f"{row['src_rack']} U{row['src_u']}S{row['src_slot']}")
        dst_label = escape(f"{row['dst_rack']} U{row['dst_u']}S{row['dst_slot']}")
        cable_label = escape(
            f"#{row['cable_seq']} {row['media']} ({row['session_count']} port{'s' if row['session_count'] != 1 else ''})"
        )

        lines.append(
            f'<line x1="380" y1="{y}" x2="820" y2="{y}" stroke="{stroke}" stroke-width="2"/>'
        )
        lines.append(f'<circle cx="380" cy="{y}" r="4" fill="{stroke}"/>')
        lines.append(f'<circle cx="820" cy="{y}" r="4" fill="{stroke}"/>')
        lines.append(
            f'<text x="20" y="{y + 4}" font-size="12" font-family="Arial, sans-serif" fill="#111827">{src_label}</text>'
        )
        lines.append(
            f'<text x="560" y="{y + 4}" font-size="12" font-family="Arial, sans-serif" fill="#111827">{cable_label}</text>'
        )
        lines.append(
            f'<text x="860" y="{y + 4}" font-size="12" font-family="Arial, sans-serif" fill="#111827">{dst_label}</text>'
        )

    lines.append("</svg>")
    return "".join(lines)
