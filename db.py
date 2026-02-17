# Copyright 2026 Patchwork Contributors
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS trials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        input_yaml TEXT NOT NULL,
        result_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'trial',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source_trial_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'saved',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(source_trial_id) REFERENCES trials(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS allocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        worker TEXT NOT NULL,
        task TEXT NOT NULL,
        score REAL NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(project_id) REFERENCES projects(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_trials_created_at ON trials(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_projects_source_trial_id ON projects(source_trial_id)",
    "CREATE INDEX IF NOT EXISTS idx_allocations_project_id ON allocations(project_id)",
]


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        for ddl in DDL_STATEMENTS:
            conn.execute(ddl)
        conn.commit()


@contextmanager
def get_db_connection(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()
