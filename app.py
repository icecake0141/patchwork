# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Flask WebUI for patchwork rack-to-rack cabling assistant."""

from __future__ import annotations

import json
import os
from uuid import uuid4

import yaml
from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from pydantic import ValidationError
from yaml import YAMLError

from db import Database
from models import ProjectInput
from services.allocator import allocate
from services.export import result_json, sessions_csv
from services.render_svg import render_pair_detail_svg, render_rack_panels_svg, render_topology_svg


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

    db = Database(os.environ.get("PATCHWORK_DB", "patchwork.db"))
    db.init_db()

    @app.get("/")
    def index() -> str:
        return redirect(url_for("upload"))

    @app.route("/upload", methods=["GET", "POST"])
    def upload() -> str | Response:
        if request.method == "POST":
            file = request.files.get("project_yaml")
            if not file or not file.filename:
                flash("Please select project.yaml")
                return redirect(url_for("upload"))
            raw = file.read().decode("utf-8")
            try:
                data = yaml.safe_load(raw)
            except YAMLError as exc:
                flash(f"YAML parse error: {exc}")
                return redirect(url_for("upload"))
            try:
                project = ProjectInput.model_validate(data)
            except ValidationError as exc:
                flash(f"Validation error: {exc.error_count()} error(s) — {exc.errors()[0]['msg']}")
                return redirect(url_for("upload"))
            trial_id = str(uuid4())
            result = allocate(project)
            session["trial_id"] = trial_id
            session[f"trial:{trial_id}:input_yaml"] = raw
            session[f"trial:{trial_id}:result"] = json.dumps(result, default=str)
            return redirect(url_for("trial"))
        projects = db.list_projects()
        return render_template("upload.html", projects=projects)

    @app.get("/trial")
    def trial() -> str | Response:
        trial_id = session.get("trial_id")
        if not trial_id:
            flash("No active trial")
            return redirect(url_for("upload"))
        result = json.loads(session[f"trial:{trial_id}:result"])
        topology_svg = render_topology_svg(result)
        racks = sorted({p["rack_id"] for p in result["panels"]})
        rack_svgs = {rack: render_rack_panels_svg(result, rack) for rack in racks}
        return render_template(
            "trial.html", result=result, topology_svg=topology_svg, rack_svgs=rack_svgs
        )

    @app.post("/save")
    def save() -> Response:
        trial_id = session.get("trial_id")
        if not trial_id:
            flash("No active trial")
            return redirect(url_for("upload"))
        project_name = (
            request.form.get("project_name", "untitled-project").strip() or "untitled-project"
        )
        note = request.form.get("note")
        input_yaml = session[f"trial:{trial_id}:input_yaml"]
        result = json.loads(session[f"trial:{trial_id}:result"])
        project_id, revision_id = db.save_revision(project_name, note, input_yaml, result)
        flash(f"Saved revision {revision_id}")
        return redirect(url_for("project_detail", project_id=project_id, revision_id=revision_id))

    @app.get("/projects/<project_id>")
    def project_detail(project_id: str) -> str:
        revision_id = request.args.get("revision_id")
        revisions = db.list_revisions(project_id)
        chosen = (
            db.get_revision(revision_id) if revision_id else (revisions[0] if revisions else None)
        )
        result = json.loads(chosen["result_json"]) if chosen else None
        return render_template(
            "project_detail.html",
            project_id=project_id,
            revisions=revisions,
            chosen=chosen,
            result=result,
        )

    @app.get("/revisions/<revision_id>/export/sessions.csv")
    def export_sessions(revision_id: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        result = json.loads(rev["result_json"])
        csv_text = sessions_csv(result, rev["project_id"], revision_id)
        return Response(
            csv_text,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={revision_id}_sessions.csv"},
        )

    @app.get("/revisions/<revision_id>/export/result.json")
    def export_result(revision_id: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        return Response(result_json(json.loads(rev["result_json"])), mimetype="application/json")

    @app.get("/diff/<project_id>")
    def diff(project_id: str) -> str:
        rev1_id = request.args.get("rev1")
        rev2_id = request.args.get("rev2")
        revisions = db.list_revisions(project_id)
        logical: dict[str, list[dict[str, str]]] = {"added": [], "removed": [], "modified": []}
        physical: dict[str, list[dict[str, str]]] = {"added": [], "removed": [], "collisions": []}
        if rev1_id and rev2_id:
            rev1 = db.get_revision(rev1_id)
            rev2 = db.get_revision(rev2_id)
            if rev1 and rev2:
                s1 = {s["session_id"]: s for s in json.loads(rev1["result_json"])["sessions"]}
                s2 = {s["session_id"]: s for s in json.loads(rev2["result_json"])["sessions"]}
                logical["added"] = [s2[k] for k in sorted(set(s2) - set(s1))]
                logical["removed"] = [s1[k] for k in sorted(set(s1) - set(s2))]
                logical["modified"] = [s2[k] for k in sorted(set(s1) & set(s2)) if s1[k] != s2[k]]
                p1 = {
                    (
                        s["media"],
                        s["src_rack"],
                        s["src_face"],
                        s["src_u"],
                        s["src_slot"],
                        s["src_port"],
                        s["dst_rack"],
                        s["dst_face"],
                        s["dst_u"],
                        s["dst_slot"],
                        s["dst_port"],
                    ): s
                    for s in s1.values()
                }
                p2 = {
                    (
                        s["media"],
                        s["src_rack"],
                        s["src_face"],
                        s["src_u"],
                        s["src_slot"],
                        s["src_port"],
                        s["dst_rack"],
                        s["dst_face"],
                        s["dst_u"],
                        s["dst_slot"],
                        s["dst_port"],
                    ): s
                    for s in s2.values()
                }
                physical["added"] = [p2[k] for k in sorted(set(p2) - set(p1))]
                physical["removed"] = [p1[k] for k in sorted(set(p1) - set(p2))]
                physical["collisions"] = [
                    p2[k]
                    for k in sorted(set(p1) & set(p2))
                    if p1[k]["session_id"] != p2[k]["session_id"]
                ]
        return render_template(
            "diff.html",
            project_id=project_id,
            revisions=revisions,
            logical=logical,
            physical=physical,
            rev1_id=rev1_id,
            rev2_id=rev2_id,
        )

    @app.get("/pair-svg/<revision_id>/<rack_a>/<rack_b>")
    def pair_svg(revision_id: str, rack_a: str, rack_b: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        result = json.loads(rev["result_json"])
        return Response(render_pair_detail_svg(result, rack_a, rack_b), mimetype="image/svg+xml")

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5000, debug=True)
