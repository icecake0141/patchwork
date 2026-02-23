# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.
from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path

from app import create_app
from db import Database
from services.export import bom_csv, sessions_csv


def _upload_and_get_result(sample_file: Path, db_path: str) -> dict:
    os.environ["PATCHWORK_DB"] = db_path
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.post(
        "/upload",
        data={"project_yaml": (io.BytesIO(sample_file.read_bytes()), sample_file.name)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200

    with client.session_transaction() as sess:
        trial_id = sess.get("trial_id")
    assert trial_id is not None

    trial = Database(db_path).get_trial(trial_id)
    assert trial is not None
    return json.loads(trial["result_json"])


def test_onboarding_simple_2rack_matches_expected_outputs(tmp_path) -> None:
    sample = Path(__file__).resolve().parents[1] / "examples/onboarding/simple-2rack.yaml"
    result = _upload_and_get_result(sample, str(tmp_path / "simple.db"))

    assert result["metrics"]["session_count"] == 18
    assert result["metrics"]["rack_count"] == 2
    assert result["errors"] == []

    sessions = result["sessions"]
    media_set = {s["media"] for s in sessions}
    pair_set = {tuple(sorted((s["src_rack"], s["dst_rack"]))) for s in sessions}

    assert media_set == {"mmf_lc_duplex", "utp_rj45"}
    assert pair_set == {("R01", "R02")}

    sessions_rows = list(csv.DictReader(io.StringIO(sessions_csv(result, "prj_test", "rev_test"))))
    assert len(sessions_rows) == 18

    bom_rows = list(csv.DictReader(io.StringIO(bom_csv(result))))
    assert {row["item_type"] for row in bom_rows} >= {"panel", "module", "cable"}


def test_onboarding_mixed_4rack_matches_expected_outputs(tmp_path) -> None:
    sample = Path(__file__).resolve().parents[1] / "examples/onboarding/mixed-4rack.yaml"
    result = _upload_and_get_result(sample, str(tmp_path / "mixed.db"))

    assert result["metrics"]["session_count"] == 45
    assert result["metrics"]["rack_count"] == 4
    assert result["errors"] == []

    sessions = result["sessions"]
    media_set = {s["media"] for s in sessions}
    pair_set = {tuple(sorted((s["src_rack"], s["dst_rack"]))) for s in sessions}

    assert media_set == {"mmf_lc_duplex", "mpo12", "utp_rj45"}
    assert pair_set == {("R01", "R02"), ("R01", "R03"), ("R02", "R04"), ("R03", "R04")}

    sessions_rows = list(csv.DictReader(io.StringIO(sessions_csv(result, "prj_test", "rev_test"))))
    assert len(sessions_rows) == 45

    bom_rows = list(csv.DictReader(io.StringIO(bom_csv(result))))
    assert {row["item_type"] for row in bom_rows} >= {"panel", "module", "cable"}
