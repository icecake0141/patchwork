<<<<<<< HEAD
# Copyright 2026 Patchwork Authors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
=======
# Copyright 2026 Patchwork Contributors
# SPDX-License-Identifier: Apache-2.0
#
>>>>>>> origin/main
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

import csv
<<<<<<< HEAD
import io
import json
from hashlib import sha256


def result_json_payload(project_yaml_text: str, result: dict[str, object]) -> str:
    payload = dict(result)
    payload["input_hash"] = sha256(project_yaml_text.encode("utf-8")).hexdigest()
    return json.dumps(payload, indent=2, sort_keys=True)


def sessions_csv(result: dict[str, object], project_id: str, revision_id: str | None = None) -> str:
    output = io.StringIO()
    columns = [
        "project_id",
        "revision_id",
        "session_id",
        "media",
        "cable_id",
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
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in result["sessions"]:
        session = dict(row)
        session["project_id"] = project_id
        session["revision_id"] = revision_id or ""
        session["label_a"] = (
            f"{session['src_rack']}U{session['src_u']}S{session['src_slot']}P{session['src_port']}"
        )
        session["label_b"] = (
            f"{session['dst_rack']}U{session['dst_u']}S{session['dst_slot']}P{session['dst_port']}"
        )
        writer.writerow({col: session.get(col, "") for col in columns})
    return output.getvalue()
=======
import json
from pathlib import Path


def export_csv(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=["worker", "task", "score"])
        writer.writeheader()
        for row in result.get("allocations", []):
            writer.writerow(row)


def export_result_json(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
>>>>>>> origin/main
