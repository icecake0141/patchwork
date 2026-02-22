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


def test_db_save_revision_twice_with_same_result(tmp_path) -> None:
    db = Database(str(tmp_path / "test.db"))
    db.init_db()
    project = ProjectInput.model_validate(
        {
            "version": 1,
            "project": {"name": "db"},
            "racks": [{"id": "R1", "name": "R1"}, {"id": "R2", "name": "R2"}],
            "demands": [
                {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "mpo12", "count": 1}
            ],
        }
    )
    result = allocate(project)
    project_id_1, revision_id_1 = db.save_revision("db", "note-1", "x: y", result)
    project_id_2, revision_id_2 = db.save_revision("db", "note-2", "x: y", result)

    assert project_id_1 == project_id_2
    assert revision_id_1 != revision_id_2

    revisions = db.list_revisions(project_id_1)
    assert len(revisions) == 2
