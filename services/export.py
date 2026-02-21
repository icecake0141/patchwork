# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Export helpers for sessions CSV, BOM CSV, and result JSON."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
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
