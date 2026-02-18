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

<<<<<<< HEAD
from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import yaml
from flask import Flask, redirect, render_template, request, session, url_for

from db import get_connection, init_db
from models import ProjectYaml
from services.allocator import allocate_project, stable_id
from services.export import result_json_payload, sessions_csv
from services.render_svg import render_pair_detail_svg, render_rack_panels_svg, render_topology_svg

app = Flask(__name__)
app.secret_key = "dev-only-secret"
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
TRIAL_RESULTS: dict[str, dict[str, object]] = {}


@app.get("/")
def index() -> str:
    return redirect(url_for("upload"))


@app.route("/upload", methods=["GET", "POST"])
def upload() -> str:
    if request.method == "GET":
        return render_template("upload.html")

    uploaded = request.files.get("project_yaml")
    if uploaded is None:
        return render_template("upload.html", error="project.yaml を選択してください")

    text = uploaded.read().decode("utf-8")
    try:
        parsed = yaml.safe_load(text)
        project = ProjectYaml.model_validate(parsed)
    except Exception as exc:  # noqa: BLE001
        return render_template("upload.html", error=str(exc))

    result = allocate_project(project)
    result["project_yaml"] = text
    result["input_hash"] = sha256(text.encode("utf-8")).hexdigest()
    result["topology_svg"] = render_topology_svg(result)
    rack_ids = [rack.id for rack in project.racks]
    result["rack_svgs"] = {rack_id: render_rack_panels_svg(result, rack_id) for rack_id in rack_ids}
    pair_keys = {
        tuple(sorted((session_row["src_rack"], session_row["dst_rack"])))
        for session_row in result["sessions"]
    }
    result["pair_svgs"] = {f"{a}__{b}": render_pair_detail_svg(result, a, b) for a, b in pair_keys}
    trial_id = str(uuid4())
    TRIAL_RESULTS[trial_id] = result
    session["trial_id"] = trial_id
    return redirect(url_for("trial"))


@app.get("/trial")
def trial() -> str:
    trial_id = session.get("trial_id")
    if trial_id is None or trial_id not in TRIAL_RESULTS:
        return redirect(url_for("upload"))
    result = TRIAL_RESULTS[trial_id]
    return render_template("trial.html", result=result, trial_id=trial_id)


@app.post("/save")
def save() -> str:
    trial_id = session.get("trial_id")
    if trial_id is None or trial_id not in TRIAL_RESULTS:
        return redirect(url_for("upload"))

    project_name = request.form.get("project_name", "unnamed-project")
    note = request.form.get("note", "")
    result = TRIAL_RESULTS[trial_id]
    timestamp = datetime.now(timezone.utc).isoformat()
    project_id = stable_id(f"project|{project_name}")
    revision_id = stable_id(f"revision|{project_id}|{timestamp}|{result['input_hash']}")

    with get_connection() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO project(project_id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (project_id, project_name, timestamp, timestamp),
        )
        connection.execute(
            "UPDATE project SET updated_at = ? WHERE project_id = ?",
            (timestamp, project_id),
        )
        connection.execute(
            "INSERT INTO revision(revision_id, project_id, created_at, note, input_yaml, input_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (
                revision_id,
                project_id,
                timestamp,
                note,
                result["project_yaml"],
                result["input_hash"],
            ),
        )

        for panel in result["panels"]:
            connection.execute(
                "INSERT INTO panel(panel_id, revision_id, rack_id, u, slots_per_u) VALUES (?, ?, ?, ?, ?)",
                (
                    panel["panel_id"],
                    revision_id,
                    panel["rack_id"],
                    panel["u"],
                    panel["slots_per_u"],
                ),
            )
        for module in result["modules"]:
            connection.execute(
                "INSERT INTO module(module_id, revision_id, rack_id, panel_u, slot, module_type, fiber_kind, polarity_variant, peer_rack_id, dedicated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    module["module_id"],
                    revision_id,
                    module["rack_id"],
                    module["panel_u"],
                    module["slot"],
                    module["module_type"],
                    module["fiber_kind"],
                    module["polarity_variant"],
                    module["peer_rack_id"],
                    module["dedicated"],
                ),
            )
        for cable in result["cables"]:
            connection.execute(
                "INSERT INTO cable(cable_id, revision_id, cable_type, fiber_kind, polarity_type) VALUES (?, ?, ?, ?, ?)",
                (
                    cable["cable_id"],
                    revision_id,
                    cable["cable_type"],
                    cable["fiber_kind"],
                    cable["polarity_type"],
                ),
            )
        for session_row in result["sessions"]:
            label_a = f"{session_row['src_rack']}U{session_row['src_u']}S{session_row['src_slot']}P{session_row['src_port']}"
            label_b = f"{session_row['dst_rack']}U{session_row['dst_u']}S{session_row['dst_slot']}P{session_row['dst_port']}"
            connection.execute(
                "INSERT INTO session(session_id, revision_id, media, cable_id, adapter_type, label_a, label_b, src_rack, src_face, src_u, src_slot, src_port, dst_rack, dst_face, dst_u, dst_slot, dst_port, fiber_a, fiber_b, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session_row["session_id"],
                    revision_id,
                    session_row["media"],
                    session_row["cable_id"],
                    session_row["adapter_type"],
                    label_a,
                    label_b,
                    session_row["src_rack"],
                    session_row["src_face"],
                    session_row["src_u"],
                    session_row["src_slot"],
                    session_row["src_port"],
                    session_row["dst_rack"],
                    session_row["dst_face"],
                    session_row["dst_u"],
                    session_row["dst_slot"],
                    session_row["dst_port"],
                    session_row["fiber_a"],
                    session_row["fiber_b"],
                    session_row["notes"],
                ),
            )
        connection.commit()

    return redirect(url_for("project_detail", project_id=project_id))


@app.get("/projects/<project_id>")
def project_detail(project_id: str) -> str:
    with get_connection() as connection:
        project_row = connection.execute(
            "SELECT project_id, name, created_at, updated_at FROM project WHERE project_id = ?",
            (project_id,),
        ).fetchone()
        if project_row is None:
            return redirect(url_for("upload"))
        revisions = connection.execute(
            "SELECT revision_id, created_at, note FROM revision WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    return render_template("project_detail.html", project=project_row, revisions=revisions)


@app.get("/projects/<project_id>/revisions/<revision_id>")
def revision_detail(project_id: str, revision_id: str) -> str:
    with get_connection() as connection:
        revision = connection.execute(
            "SELECT revision_id, input_yaml, input_hash FROM revision WHERE revision_id = ? AND project_id = ?",
            (revision_id, project_id),
        ).fetchone()
        sessions = connection.execute(
            "SELECT * FROM session WHERE revision_id = ? ORDER BY session_id LIMIT 200",
            (revision_id,),
        ).fetchall()
    if revision is None:
        return redirect(url_for("project_detail", project_id=project_id))
    return render_template("revision_detail.html", revision=revision, sessions=sessions)


@app.get("/projects/<project_id>/diff")
def revision_diff(project_id: str) -> str:
    rev1 = request.args.get("rev1")
    rev2 = request.args.get("rev2")
    if rev1 is None or rev2 is None:
        return redirect(url_for("project_detail", project_id=project_id))

    with get_connection() as connection:
        left = connection.execute("SELECT * FROM session WHERE revision_id = ?", (rev1,)).fetchall()
        right = connection.execute(
            "SELECT * FROM session WHERE revision_id = ?", (rev2,)
        ).fetchall()

    left_by_id = {row["session_id"]: dict(row) for row in left}
    right_by_id = {row["session_id"]: dict(row) for row in right}
    added = sorted(set(right_by_id) - set(left_by_id))
    removed = sorted(set(left_by_id) - set(right_by_id))
    modified = [
        sid
        for sid in sorted(set(left_by_id).intersection(right_by_id))
        if left_by_id[sid] != right_by_id[sid]
    ]

    def physical_key(row: dict[str, object]) -> tuple[object, ...]:
        return (
            row["media"],
            row["src_rack"],
            row["src_face"],
            row["src_u"],
            row["src_slot"],
            row["src_port"],
            row["dst_rack"],
            row["dst_face"],
            row["dst_u"],
            row["dst_slot"],
            row["dst_port"],
        )

    left_phys = {physical_key(v): k for k, v in left_by_id.items()}
    right_phys = {physical_key(v): k for k, v in right_by_id.items()}
    physical_added = sorted(set(right_phys) - set(left_phys))
    physical_removed = sorted(set(left_phys) - set(right_phys))
    collisions = [
        k for k in set(left_phys).intersection(right_phys) if left_phys[k] != right_phys[k]
    ]

    return render_template(
        "diff.html",
        project_id=project_id,
        rev1=rev1,
        rev2=rev2,
        logical={"added": added, "removed": removed, "modified": modified},
        physical={"added": physical_added, "removed": physical_removed, "collisions": collisions},
    )


@app.get("/trial/export/result.json")
def trial_export_result_json() -> tuple[str, int, dict[str, str]]:
    trial_id = session.get("trial_id")
    if trial_id is None or trial_id not in TRIAL_RESULTS:
        return ("not found", 404, {})
    result = TRIAL_RESULTS[trial_id]
    return (
        result_json_payload(str(result["project_yaml"]), result),
        200,
        {"Content-Type": "application/json"},
    )


@app.get("/trial/export/sessions.csv")
def trial_export_sessions_csv() -> tuple[str, int, dict[str, str]]:
    trial_id = session.get("trial_id")
    if trial_id is None or trial_id not in TRIAL_RESULTS:
        return ("not found", 404, {})
    result = TRIAL_RESULTS[trial_id]
    project_id = stable_id(f"project|{result['project']['name']}")
    return (sessions_csv(result, project_id), 200, {"Content-Type": "text/csv"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    init_db()
=======
import json
import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

from db import get_db_connection, init_db
from models import AllocationInput
from services.allocator import run_trial_allocation
from services.export import export_csv, export_result_json
from services.render_svg import render_trial_svg

BASE_DIR = Path(__file__).resolve().parent
EXPORT_DIR = BASE_DIR / "exports"


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
    app.config["DATABASE_PATH"] = str(BASE_DIR / "patchwork.db")
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    init_db(app.config["DATABASE_PATH"])
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index():
        return redirect(url_for("upload"))

    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        if request.method == "POST":
            yaml_file = request.files.get("yaml_file")
            if not yaml_file:
                flash("YAMLファイルを選択してください", "error")
                return redirect(url_for("upload"))
            try:
                payload = yaml_file.read().decode("utf-8")
                parsed = AllocationInput.model_validate_yaml(payload)
            except Exception as exc:  # noqa: BLE001
                flash(f"入力エラー: {exc}", "error")
                return redirect(url_for("upload"))

            trial_result = run_trial_allocation(parsed)
            with get_db_connection(app.config["DATABASE_PATH"]) as conn:
                cursor = conn.execute(
                    "INSERT INTO trials (name, input_yaml, result_json, status) VALUES (?, ?, ?, ?)",
                    (
                        parsed.project_name,
                        payload,
                        json.dumps(trial_result, ensure_ascii=False),
                        "trial",
                    ),
                )
                conn.commit()
                session["trial_id"] = cursor.lastrowid

            return redirect(url_for("trial"))

        return render_template("upload.html")

    @app.get("/trial")
    def trial():
        trial_id = session.get("trial_id")
        if not trial_id:
            flash("trial_id が見つかりません。先に Upload を実行してください", "error")
            return redirect(url_for("upload"))

        with get_db_connection(app.config["DATABASE_PATH"]) as conn:
            row = conn.execute(
                "SELECT id, name, result_json FROM trials WHERE id = ?", (trial_id,)
            ).fetchone()
        if not row:
            flash("Trialデータが存在しません", "error")
            return redirect(url_for("upload"))

        result = json.loads(row["result_json"])
        svg = render_trial_svg(result)
        return render_template("trial.html", trial=row, result=result, svg=svg)

    @app.post("/save")
    def save():
        trial_id = session.get("trial_id")
        if not trial_id:
            flash("保存対象の Trial がありません", "error")
            return redirect(url_for("upload"))

        with get_db_connection(app.config["DATABASE_PATH"]) as conn:
            trial = conn.execute(
                "SELECT * FROM trials WHERE id = ?", (trial_id,)
            ).fetchone()
            if not trial:
                flash("Trialデータが存在しません", "error")
                return redirect(url_for("upload"))

            project_cursor = conn.execute(
                "INSERT INTO projects (name, source_trial_id, status) VALUES (?, ?, ?)",
                (trial["name"], trial_id, "saved"),
            )
            project_id = project_cursor.lastrowid

            result = json.loads(trial["result_json"])
            for entry in result.get("allocations", []):
                conn.execute(
                    "INSERT INTO allocations (project_id, worker, task, score) VALUES (?, ?, ?, ?)",
                    (project_id, entry["worker"], entry["task"], float(entry["score"])),
                )
            conn.commit()

        export_csv(result, EXPORT_DIR / f"project_{project_id}.csv")
        export_result_json(result, EXPORT_DIR / f"project_{project_id}.json")
        return render_template("save.html", project_id=project_id)

    @app.get("/projects/<int:project_id>")
    def project_detail(project_id: int):
        with get_db_connection(app.config["DATABASE_PATH"]) as conn:
            project = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            allocations = conn.execute(
                "SELECT worker, task, score FROM allocations WHERE project_id = ? ORDER BY id",
                (project_id,),
            ).fetchall()

        if not project:
            flash("Projectが見つかりません", "error")
            return redirect(url_for("upload"))

        return render_template(
            "project_detail.html", project=project, allocations=allocations
        )

    return app


app = create_app()


if __name__ == "__main__":
>>>>>>> origin/main
    app.run(host="0.0.0.0", port=5000, debug=True)
