# Copyright 2026 Patchwork Contributors
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from db import init_db


def test_init_db_creates_tables(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    init_db(str(db_path))
    assert db_path.exists()
