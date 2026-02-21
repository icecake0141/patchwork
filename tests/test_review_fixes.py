# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Tests covering code-review fixes: pair-key consistency, demand-id uniqueness,
DB rollback on error, and upload error handling."""

from __future__ import annotations

import pytest

from models import ProjectInput
from services.allocator import allocate, pair_key
from services.render_svg import render_pair_detail_svg

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
