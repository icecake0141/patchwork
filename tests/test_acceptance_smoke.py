# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _make_client(tmp_db_path: str):
    os.environ["PATCHWORK_DB"] = tmp_db_path
    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _upload_trial(client, yaml_path: Path) -> None:
    payload = yaml_path.read_bytes()
    response = client.post(
        "/upload",
        data={"project_yaml": (io.BytesIO(payload), yaml_path.name)},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/trial")


def _save_and_get_revision_and_project(client, project_name: str) -> tuple[str, str]:
    save_response = client.post(
        "/save",
        data={"project_name": project_name, "note": "acceptance-smoke"},
        follow_redirects=False,
    )
    assert save_response.status_code == 302
    location = save_response.headers["Location"]
    parsed = urlparse(location)
    project_id = parsed.path.rsplit("/", 1)[-1]
    query = parse_qs(parsed.query)
    revision_ids = query.get("revision_id", [])
    assert revision_ids
    assert project_id
    return revision_ids[0], project_id


@pytest.mark.parametrize(
    ("yaml_rel_path", "scenario_name"),
    [
        ("examples/quick-start/sample-project-3rack-35links.yaml", "small"),
        ("examples/sample-project-3rack-mixed-38links.yaml", "medium"),
        ("examples/quick-start/sample-project-10rack-200links.yaml", "high-density"),
    ],
)
def test_acceptance_smoke_ui_and_exports_by_scenario(
    yaml_rel_path: str, scenario_name: str
) -> None:
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        client = _make_client(db_path)
        yaml_path = ROOT / yaml_rel_path

        _upload_trial(client, yaml_path)

        trial_response = client.get("/trial")
        assert trial_response.status_code == 200
        assert b"Integrated Wiring View" in trial_response.data
        assert (
            b"Tip: click wire/label to focus. Click again or blank area to clear."
            in trial_response.data
        )
        assert b"Gap Jump Scale" in trial_response.data
        assert b"Port State" in trial_response.data
        assert b"occupied" in trial_response.data
        assert b"free" in trial_response.data
        assert b"Auto \xc3\x97 0.50" in trial_response.data
        assert b"Auto \xc3\x97 2.00" in trial_response.data

        revision_id, project_id = _save_and_get_revision_and_project(
            client, f"acceptance-{scenario_name}"
        )

        project_response = client.get(f"/projects/{project_id}?revision_id={revision_id}")

        assert project_response.status_code == 200
        assert b"downloads" in project_response.data
        assert b"Integrated Wiring View (Interactive)" in project_response.data

        sessions_csv_response = client.get(f"/revisions/{revision_id}/export/sessions.csv")
        assert sessions_csv_response.status_code == 200
        assert b"session_id" in sessions_csv_response.data

        wiring_drawio_response = client.get(f"/revisions/{revision_id}/export/wiring.drawio")
        assert wiring_drawio_response.status_code == 200
        assert b"<mxfile" in wiring_drawio_response.data
        assert b"jumpStyle=arc" in wiring_drawio_response.data

        interactive_svg_response = client.get(
            f"/revisions/{revision_id}/export/integrated_wiring_interactive.svg?mode=aggregate"
        )
        assert interactive_svg_response.status_code == 200
        assert b'data-role="integrated-wir' in interactive_svg_response.data
        assert b"<script" in interactive_svg_response.data
        assert b"highlightedWireId" in interactive_svg_response.data
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass
