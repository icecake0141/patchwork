# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Flask WebUI for patchwork rack-to-rack cabling assistant."""

from __future__ import annotations

import json
import os
from typing import Any
from uuid import uuid4

import yaml
from flask import Flask, Response, flash, redirect, render_template, request, session, url_for
from pydantic import ValidationError
from yaml import YAMLError

from db import Database
from models import ProjectInput
from services.allocator import allocate
from services.export import (
    bom_csv,
    bom_rows,
    integrated_wiring_drawio,
    integrated_wiring_interactive_svg,
    integrated_wiring_svg,
    rack_occupancy_drawio,
    result_json,
    sessions_csv,
    wiring_drawio,
    wiring_svg,
)
from services.render_svg import rack_slot_width, render_pair_detail_svg, render_rack_panels_svg


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
            db.save_trial(trial_id, raw, result)
            return redirect(url_for("trial"))
        projects = db.list_projects()
        return render_template("upload.html", projects=projects)

    @app.get("/trial")
    def trial() -> str | Response:
        trial_id = session.get("trial_id")
        if not trial_id:
            flash("No active trial")
            return redirect(url_for("upload"))
        trial = db.get_trial(trial_id)
        if not trial:
            flash("No active trial")
            return redirect(url_for("upload"))
        result = json.loads(trial["result_json"])
        topology_counts: dict[tuple[str, str, str], int] = {}
        for session_row in result["sessions"]:
            rack_a, rack_b = sorted((session_row["src_rack"], session_row["dst_rack"]))
            key = (rack_a, rack_b, session_row["media"])
            topology_counts[key] = topology_counts.get(key, 0) + 1
        topology_rows = [
            {"rack_a": rack_a, "rack_b": rack_b, "media": media, "count": count}
            for (rack_a, rack_b, media), count in sorted(topology_counts.items())
        ]
        bom_table_rows = bom_rows(result)
        racks = sorted({p["rack_id"] for p in result["panels"]})
        uniform_slot_width = rack_slot_width(result)
        rack_svgs = {
            rack: render_rack_panels_svg(result, rack, slot_width=uniform_slot_width)
            for rack in racks
        }
        wiring_svg_text = wiring_svg(result)
        integrated_wiring_svgs = {
            "aggregate": integrated_wiring_svg(result, mode="aggregate"),
            "detailed": integrated_wiring_svg(result, mode="detailed"),
        }
        integrated_media_types = ["mmf_lc_duplex", "smf_lc_duplex", "mpo12", "utp_rj45"]
        integrated_racks = sorted({str(panel["rack_id"]) for panel in result.get("panels", [])})
        return render_template(
            "trial.html",
            result=result,
            topology_rows=topology_rows,
            bom_rows=bom_table_rows,
            rack_svgs=rack_svgs,
            wiring_svg=wiring_svg_text,
            integrated_wiring_svgs=integrated_wiring_svgs,
            integrated_media_types=integrated_media_types,
            integrated_racks=integrated_racks,
        )

    @app.post("/save")
    def save() -> Response:
        trial_id = session.get("trial_id")
        if not trial_id:
            flash("No active trial")
            return redirect(url_for("upload"))
        trial = db.get_trial(trial_id)
        if not trial:
            flash("No active trial")
            return redirect(url_for("upload"))
        project_name = (
            request.form.get("project_name", "untitled-project").strip() or "untitled-project"
        )
        note = request.form.get("note")
        input_yaml = trial["input_yaml"]
        result = json.loads(trial["result_json"])
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
        topology_rows: list[dict[str, str | int]] = []
        bom_table_rows: list[dict[str, Any]] = []
        rack_svgs: dict[str, str] = {}
        wiring_svg_text = ""
        integrated_wiring_svgs = {"aggregate": "", "detailed": ""}
        integrated_media_types = ["mmf_lc_duplex", "smf_lc_duplex", "mpo12", "utp_rj45"]
        integrated_racks: list[str] = []
        if result:
            topology_counts: dict[tuple[str, str, str], int] = {}
            for session_row in result["sessions"]:
                rack_a, rack_b = sorted((session_row["src_rack"], session_row["dst_rack"]))
                key = (rack_a, rack_b, session_row["media"])
                topology_counts[key] = topology_counts.get(key, 0) + 1
            topology_rows = [
                {"rack_a": rack_a, "rack_b": rack_b, "media": media, "count": count}
                for (rack_a, rack_b, media), count in sorted(topology_counts.items())
            ]
            bom_table_rows = bom_rows(result)
            racks = sorted({panel["rack_id"] for panel in result["panels"]})
            uniform_slot_width = rack_slot_width(result)
            rack_svgs = {
                rack: render_rack_panels_svg(result, rack, slot_width=uniform_slot_width)
                for rack in racks
            }
            wiring_svg_text = wiring_svg(result)
            integrated_wiring_svgs = {
                "aggregate": integrated_wiring_svg(result, mode="aggregate"),
                "detailed": integrated_wiring_svg(result, mode="detailed"),
            }
            integrated_racks = sorted({str(panel["rack_id"]) for panel in result.get("panels", [])})
        return render_template(
            "project_detail.html",
            project_id=project_id,
            revisions=revisions,
            chosen=chosen,
            result=result,
            topology_rows=topology_rows,
            bom_rows=bom_table_rows,
            rack_svgs=rack_svgs,
            wiring_svg=wiring_svg_text,
            integrated_wiring_svgs=integrated_wiring_svgs,
            integrated_media_types=integrated_media_types,
            integrated_racks=integrated_racks,
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

    @app.get("/revisions/<revision_id>/export/bom.csv")
    def export_bom(revision_id: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        result = json.loads(rev["result_json"])
        csv_text = bom_csv(result)
        return Response(
            csv_text,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={revision_id}_bom.csv"},
        )

    @app.get("/revisions/<revision_id>/export/result.json")
    def export_result(revision_id: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        return Response(result_json(json.loads(rev["result_json"])), mimetype="application/json")

    @app.get("/revisions/<revision_id>/export/wiring.svg")
    def export_wiring_svg(revision_id: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        result = json.loads(rev["result_json"])
        svg_text = wiring_svg(result)
        return Response(
            svg_text,
            mimetype="image/svg+xml",
            headers={"Content-Disposition": f"attachment; filename={revision_id}_wiring.svg"},
        )

    @app.get("/revisions/<revision_id>/export/wiring.drawio")
    def export_wiring_drawio(revision_id: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        result = json.loads(rev["result_json"])
        drawio_text = wiring_drawio(result)
        return Response(
            drawio_text,
            mimetype="application/xml",
            headers={"Content-Disposition": f"attachment; filename={revision_id}_wiring.drawio"},
        )

    @app.get("/revisions/<revision_id>/export/integrated_wiring.drawio")
    def export_integrated_wiring_drawio(revision_id: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        result = json.loads(rev["result_json"])
        drawio_text = integrated_wiring_drawio(result)
        return Response(
            drawio_text,
            mimetype="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename={revision_id}_integrated_wiring.drawio"
            },
        )

    @app.get("/revisions/<revision_id>/export/integrated_wiring_interactive.svg")
    def export_integrated_wiring_interactive_svg(revision_id: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        mode = request.args.get("mode", "aggregate")
        if mode not in {"aggregate", "detailed"}:
            mode = "aggregate"
        result = json.loads(rev["result_json"])
        svg_text = integrated_wiring_interactive_svg(result, mode=mode)
        return Response(
            svg_text,
            mimetype="image/svg+xml",
            headers={
                "Content-Disposition": f"attachment; filename={revision_id}_integrated_wiring_{mode}_interactive.svg"
            },
        )

    @app.get("/revisions/<revision_id>/export/rack_occupancy.drawio")
    def export_rack_occupancy_drawio(revision_id: str) -> Response:
        rev = db.get_revision(revision_id)
        if not rev:
            return Response("not found", status=404)
        result = json.loads(rev["result_json"])
        drawio_text = rack_occupancy_drawio(result)
        return Response(
            drawio_text,
            mimetype="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename={revision_id}_rack_occupancy.drawio"
            },
        )

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
