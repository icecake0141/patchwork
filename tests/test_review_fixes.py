# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Tests covering code-review fixes: pair-key consistency, demand-id uniqueness,
DB rollback on error, upload error handling, pair_details JSON serializability,
and fixed_profiles settings propagation."""

from __future__ import annotations

import json

import pytest

from models import ProjectInput
from services.allocator import allocate, pair_key
from services.render_svg import render_pair_detail_svg, render_rack_panels_svg

# ---------------------------------------------------------------------------
# pair_key / render_pair_detail_svg consistency
# ---------------------------------------------------------------------------


def test_pair_key_natural_sort_order() -> None:
    """pair_key must use natural sort so R2 < R10 (not lexicographic R10 < R2)."""
    assert pair_key("R10", "R2") == ("R2", "R10")
    assert pair_key("R2", "R10") == ("R2", "R10")


def test_render_pair_detail_svg_uses_natural_sort_key() -> None:
    """render_pair_detail_svg must produce non-empty SVG when rack names need
    natural ordering (e.g. R2 / R10)."""
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "pairtest"},
            "racks": [{"id": "R2", "name": "R2"}, {"id": "R10", "name": "R10"}],
            "demands": [
                {"id": "D1", "src": "R2", "dst": "R10", "endpoint_type": "mpo12", "count": 1}
            ],
        }
    )
    result = allocate(project)
    # The pair_detail key in result must match what render_pair_detail_svg looks up
    svg = render_pair_detail_svg(result, "R2", "R10")
    # SVG should contain the port-used line (not just the header)
    assert "ports used: 1" in svg

    # Reverse argument order should produce the same result
    svg_rev = render_pair_detail_svg(result, "R10", "R2")
    assert "ports used: 1" in svg_rev


def test_rack_panel_svg_default_u_label_is_ascending() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "ulabel-default"},
            "racks": [{"id": "R1", "name": "R1", "max_u": 42}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}
            ],
        }
    )
    result = allocate(project)
    svg = render_rack_panels_svg(result, "R1")
    assert "U1</text>" in svg


def test_rack_panel_svg_descending_u_label_mode() -> None:
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "ulabel-desc"},
            "racks": [{"id": "R1", "name": "R1", "max_u": 42}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}
            ],
            "settings": {"panel": {"u_label_mode": "descending"}},
        }
    )
    result = allocate(project)
    svg = render_rack_panels_svg(result, "R1")
    assert "U42</text>" in svg


# ---------------------------------------------------------------------------
# models.py – demand ID uniqueness
# ---------------------------------------------------------------------------


def test_model_validation_rejects_duplicate_demand_ids() -> None:
    payload = {
        "version": 1,
        "project": {"name": "x"},
        "racks": [{"id": "R1", "name": "A"}, {"id": "R2", "name": "B"}],
        "demands": [
            {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 1},
            {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1},
        ],
    }
    with pytest.raises(ValueError, match="demand ids must be unique"):
        ProjectInput.model_validate(payload)


# ---------------------------------------------------------------------------
# db.py – rollback on error
# ---------------------------------------------------------------------------


def test_db_connect_rolls_back_on_exception(tmp_path) -> None:
    from db import Database

    db = Database(str(tmp_path / "test.db"))
    db.init_db()

    # Force an error mid-transaction and verify the connection was rolled back
    with pytest.raises(RuntimeError):
        with db.connect() as conn:
            conn.execute(
                "INSERT INTO project(project_id,name,created_at,updated_at) VALUES(?,?,?,?)",
                ("prj_test", "test", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
            )
            raise RuntimeError("forced error")

    # The insert must NOT have been committed
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM project WHERE project_id=?", ("prj_test",)).fetchone()
    assert row is None


# ---------------------------------------------------------------------------
# app.py – upload error handling
# ---------------------------------------------------------------------------


def _make_client(tmp_db_path: str | None = None):
    import os
    import sys
    import tempfile
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    if tmp_db_path is None:
        fd, tmp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
    os.environ["PATCHWORK_DB"] = tmp_db_path
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_upload_bad_yaml_shows_flash(tmp_path) -> None:
    import io

    client = _make_client(str(tmp_path / "t.db"))
    resp = client.post(
        "/upload",
        data={"project_yaml": (io.BytesIO(b": invalid: yaml: ["), "bad.yaml")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"YAML parse error" in resp.data


def test_upload_invalid_schema_shows_flash(tmp_path) -> None:
    import io

    client = _make_client(str(tmp_path / "t.db"))
    # Valid YAML but missing required 'racks' field
    bad_yaml = b"version: 1\nproject:\n  name: x\ndemands: []\n"
    resp = client.post(
        "/upload",
        data={"project_yaml": (io.BytesIO(bad_yaml), "bad.yaml")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Validation error" in resp.data


def test_upload_stores_only_trial_id_in_session(tmp_path) -> None:
    import io

    client = _make_client(str(tmp_path / "t.db"))
    payload = b"version: 1\nproject:\n  name: sample\nracks:\n  - id: R01\n    name: Rack-01\n  - id: R02\n    name: Rack-02\ndemands:\n  - id: D001\n    src: R01\n    dst: R02\n    endpoint_type: mpo12\n    count: 1\n"
    resp = client.post(
        "/upload",
        data={"project_yaml": (io.BytesIO(payload), "ok.yaml")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/trial")
    with client.session_transaction() as sess:
        assert "trial_id" in sess
        assert not any(str(k).startswith("trial:") for k in sess.keys())


def test_trial_page_shows_bom_table(tmp_path) -> None:
    import io

    client = _make_client(str(tmp_path / "t.db"))
    payload = (
        b"version: 1\n"
        b"project:\n"
        b"  name: sample\n"
        b"racks:\n"
        b"  - id: R01\n"
        b"    name: Rack-01\n"
        b"  - id: R02\n"
        b"    name: Rack-02\n"
        b"demands:\n"
        b"  - id: D001\n"
        b"    src: R01\n"
        b"    dst: R02\n"
        b"    endpoint_type: mpo12\n"
        b"    count: 1\n"
    )
    post_resp = client.post(
        "/upload",
        data={"project_yaml": (io.BytesIO(payload), "ok.yaml")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert post_resp.status_code == 302

    trial_resp = client.get("/trial")
    assert trial_resp.status_code == 200
    assert b"Bill of Materials" in trial_resp.data
    assert b"item_type" in trial_resp.data
    assert b"quantity" in trial_resp.data
    assert b"click a wire or port label to focus it" in trial_resp.data
    assert b"Gap Jump Scale" in trial_resp.data
    assert b"Auto \xc3\x97 1.25" in trial_resp.data


def test_project_detail_shows_bom_table(tmp_path) -> None:
    from db import Database

    db_path = str(tmp_path / "t.db")
    _ = _make_client(db_path)

    payload = {
        "version": 1,
        "project": {"name": "bom-view"},
        "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
        "demands": [{"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}],
    }
    result = allocate(ProjectInput.model_validate(payload))

    db = Database(db_path)
    project_id, revision_id = db.save_revision(
        project_name="bom-view",
        note="",
        input_yaml="version: 1\n",
        result=result,
    )
    assert project_id

    client = _make_client(db_path)
    resp = client.get(f"/projects/{project_id}?revision_id={revision_id}")
    assert resp.status_code == 200
    assert b"Bill of Materials" in resp.data
    assert b"item_type" in resp.data
    assert b"description" in resp.data
    assert b"quantity" in resp.data
    assert b"click a wire or port label to focus it" in resp.data
    assert b"Gap Jump Scale" in resp.data
    assert b"Auto \xc3\x97 1.50" in resp.data


def test_export_wiring_drawio_returns_drawio_xml(tmp_path) -> None:
    from db import Database

    db_path = str(tmp_path / "t.db")
    _ = _make_client(db_path)

    payload = {
        "version": 1,
        "project": {"name": "drawio-export"},
        "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
        "demands": [{"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}],
    }
    result = allocate(ProjectInput.model_validate(payload))

    db = Database(db_path)
    project_id, revision_id = db.save_revision(
        project_name="drawio-export",
        note="",
        input_yaml="version: 1\n",
        result=result,
    )
    assert project_id

    client = _make_client(db_path)
    resp = client.get(f"/revisions/{revision_id}/export/wiring.drawio")

    assert resp.status_code == 200
    assert resp.mimetype == "application/xml"
    assert "attachment;" in resp.headers.get("Content-Disposition", "")
    assert resp.data.startswith(b"<mxfile ")
    assert b"Cable Wiring Diagram" in resp.data
    assert b"shape=rectangle;" in resp.data
    assert b"edgeStyle=none;" in resp.data

    resp_integrated = client.get(f"/revisions/{revision_id}/export/integrated_wiring.drawio")
    assert resp_integrated.status_code == 200
    assert resp_integrated.mimetype == "application/xml"
    assert b"Integrated Wiring (Aggregate)" in resp_integrated.data
    assert b"Integrated Wiring (Detailed)" in resp_integrated.data
    assert b"curved=1;" in resp_integrated.data

    resp_integrated_interactive = client.get(
        f"/revisions/{revision_id}/export/integrated_wiring_interactive.svg?mode=aggregate"
    )
    assert resp_integrated_interactive.status_code == 200
    assert resp_integrated_interactive.mimetype == "image/svg+xml"
    assert b"<foreignObject" in resp_integrated_interactive.data
    assert b'data-role="integrated-media"' in resp_integrated_interactive.data
    assert b'data-role="integrated-rack"' in resp_integrated_interactive.data

    resp_rack = client.get(f"/revisions/{revision_id}/export/rack_occupancy.drawio")
    assert resp_rack.status_code == 200
    assert resp_rack.mimetype == "application/xml"
    assert b'name="Rack Occupancy"' in resp_rack.data
    assert resp_rack.data.count(b"<diagram ") == 1
    assert b"Rack R1 Panel Occupancy" in resp_rack.data
    assert b"Rack R2 Panel Occupancy" in resp_rack.data


# ---------------------------------------------------------------------------
# pair_details JSON round-trip (Bug: SlotRef was not JSON-serialisable)
# ---------------------------------------------------------------------------


def _base_two_racks() -> dict:
    return {
        "version": 1,
        "project": {"name": "rt"},
        "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
        "demands": [],
    }


def test_pair_detail_survives_json_round_trip_mpo() -> None:
    """pair_details must be JSON-serialisable so render_pair_detail_svg works
    after loading a saved revision (json.dumps → json.loads round-trip)."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 3}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    # Simulate the JSON round-trip that happens when reading a saved revision
    deserialized = json.loads(json.dumps(result, default=str))
    svg = render_pair_detail_svg(deserialized, "R1", "R2")
    assert "ports used: 3" in svg


def test_pair_detail_survives_json_round_trip_lc() -> None:
    """Same round-trip check for LC breakout pair_details."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mmf_lc_duplex", "count": 5}
    ]
    result = allocate(ProjectInput.model_validate(payload))
    deserialized = json.loads(json.dumps(result, default=str))
    svg = render_pair_detail_svg(deserialized, "R1", "R2")
    assert "ports used: 5" in svg


# ---------------------------------------------------------------------------
# fixed_profiles settings propagation (Bug: values were hardcoded)
# ---------------------------------------------------------------------------


def test_fixed_profiles_mpo_polarity_applied() -> None:
    """trunk_polarity from settings.fixed_profiles.mpo_e2e must be used for
    MPO12 trunk cables instead of a hardcoded 'B'."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}
    ]
    payload["settings"] = {
        "fixed_profiles": {"mpo_e2e": {"trunk_polarity": "A", "pass_through_variant": "B"}}
    }
    result = allocate(ProjectInput.model_validate(payload))
    cable = result["cables"][0]
    assert cable["polarity_type"] == "A", "trunk_polarity from settings must be used"
    r1_mod = next(m for m in result["modules"] if m["rack_id"] == "R1")
    assert r1_mod["polarity_variant"] == "B", "pass_through_variant from settings must be used"


def test_fixed_profiles_lc_polarity_applied() -> None:
    """trunk_polarity and breakout_module_variant from settings.fixed_profiles.lc_demands
    must be used for LC breakout cables and modules instead of hardcoded values."""
    payload = _base_two_racks()
    payload["demands"] = [
        {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mmf_lc_duplex", "count": 1}
    ]
    payload["settings"] = {
        "fixed_profiles": {"lc_demands": {"trunk_polarity": "B", "breakout_module_variant": "BF"}}
    }
    result = allocate(ProjectInput.model_validate(payload))
    cable = result["cables"][0]
    assert cable["polarity_type"] == "B", "trunk_polarity from settings must be used"
    r1_mod = next(m for m in result["modules"] if m["rack_id"] == "R1")
    assert r1_mod["polarity_variant"] == "BF", "breakout_module_variant from settings must be used"
