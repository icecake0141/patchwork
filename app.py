# Copyright 2026 Patchwork Contributors
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

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
    app.run(host="0.0.0.0", port=5000, debug=True)
