# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

from db import Database
from models import ProjectInput
from services.allocator import allocate


def test_db_save_revision(tmp_path) -> None:
    db = Database(str(tmp_path / "test.db"))
    db.init_db()
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "db"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 1}
            ],
        }
    )
    result = allocate(project)
    project_id, revision_id = db.save_revision("db", "note", "x: y", result)
    assert project_id.startswith("prj_")
    assert db.get_revision(revision_id) is not None
