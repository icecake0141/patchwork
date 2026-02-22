# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""SQLite persistence layer for project revisions and generated artifacts."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS project (
  project_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revision (
  revision_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  note TEXT,
  input_yaml TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  result_json TEXT NOT NULL,
  FOREIGN KEY(project_id) REFERENCES project(project_id)
);
CREATE TABLE IF NOT EXISTS trial (
    trial_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    input_yaml TEXT NOT NULL,
    result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS panel (
  panel_id TEXT PRIMARY KEY,
  revision_id TEXT NOT NULL,
  rack_id TEXT NOT NULL,
  u INTEGER NOT NULL,
  slots_per_u INTEGER NOT NULL DEFAULT 4,
  FOREIGN KEY(revision_id) REFERENCES revision(revision_id)
);
CREATE TABLE IF NOT EXISTS module (
  module_id TEXT PRIMARY KEY,
  revision_id TEXT NOT NULL,
  rack_id TEXT NOT NULL,
  panel_u INTEGER NOT NULL,
  slot INTEGER NOT NULL,
  module_type TEXT NOT NULL,
  fiber_kind TEXT,
  polarity_variant TEXT,
  peer_rack_id TEXT,
  dedicated INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY(revision_id) REFERENCES revision(revision_id)
);
CREATE TABLE IF NOT EXISTS cable (
  cable_id TEXT PRIMARY KEY,
  revision_id TEXT NOT NULL,
  cable_type TEXT NOT NULL,
  fiber_kind TEXT,
  polarity_type TEXT,
  FOREIGN KEY(revision_id) REFERENCES revision(revision_id)
);
CREATE TABLE IF NOT EXISTS session (
  session_id TEXT PRIMARY KEY,
  revision_id TEXT NOT NULL,
  media TEXT NOT NULL,
  cable_id TEXT NOT NULL,
  adapter_type TEXT NOT NULL,
  label_a TEXT NOT NULL,
  label_b TEXT NOT NULL,
  src_rack TEXT NOT NULL,
  src_face TEXT NOT NULL,
  src_u INTEGER NOT NULL,
  src_slot INTEGER NOT NULL,
  src_port INTEGER NOT NULL,
  dst_rack TEXT NOT NULL,
  dst_face TEXT NOT NULL,
  dst_u INTEGER NOT NULL,
  dst_slot INTEGER NOT NULL,
  dst_port INTEGER NOT NULL,
  fiber_a INTEGER,
  fiber_b INTEGER,
  notes TEXT,
  FOREIGN KEY(revision_id) REFERENCES revision(revision_id),
  FOREIGN KEY(cable_id) REFERENCES cable(cable_id)
);
CREATE INDEX IF NOT EXISTS idx_session_revision ON session(revision_id);
CREATE INDEX IF NOT EXISTS idx_module_revision_rack ON module(revision_id, rack_id);
CREATE INDEX IF NOT EXISTS idx_panel_revision_rack ON panel(revision_id, rack_id);
"""


class Database:
    def __init__(self, path: str = "patchwork.db"):
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def save_revision(
        self, project_name: str, note: str | None, input_yaml: str, result: dict[str, Any]
    ) -> tuple[str, str]:
        now = datetime.now(timezone.utc).isoformat()
        project_id = f"prj_{sha256(project_name.encode('utf-8')).hexdigest()[:16]}"
        revision_id = (
            f"rev_{sha256((project_name + now + input_yaml).encode('utf-8')).hexdigest()[:16]}"
        )
        input_hash = result["input_hash"]
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO project(project_id,name,created_at,updated_at) VALUES(?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET updated_at=excluded.updated_at,name=excluded.name",
                (project_id, project_name, now, now),
            )
            conn.execute(
                "INSERT INTO revision(revision_id,project_id,created_at,note,input_yaml,input_hash,result_json) VALUES(?,?,?,?,?,?,?)",
                (
                    revision_id,
                    project_id,
                    now,
                    note or "",
                    input_yaml,
                    input_hash,
                    json.dumps(result, default=str),
                ),
            )
            for panel in result["panels"]:
                conn.execute(
                    "INSERT INTO panel(panel_id,revision_id,rack_id,u,slots_per_u) VALUES(?,?,?,?,?)",
                    (
                        panel["panel_id"],
                        revision_id,
                        panel["rack_id"],
                        panel["u"],
                        panel["slots_per_u"],
                    ),
                )
            for module in result["modules"]:
                conn.execute(
                    "INSERT INTO module(module_id,revision_id,rack_id,panel_u,slot,module_type,fiber_kind,polarity_variant,peer_rack_id,dedicated) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        module["module_id"],
                        revision_id,
                        module["rack_id"],
                        module["panel_u"],
                        module["slot"],
                        module["module_type"],
                        module["fiber_kind"],
                        module["polarity_variant"],
                        module["peer_rack_id"],
                        module["dedicated"],
                    ),
                )
            for cable in result["cables"]:
                conn.execute(
                    "INSERT INTO cable(cable_id,revision_id,cable_type,fiber_kind,polarity_type) VALUES(?,?,?,?,?)",
                    (
                        cable["cable_id"],
                        revision_id,
                        cable["cable_type"],
                        cable["fiber_kind"],
                        cable["polarity_type"],
                    ),
                )
            for session in result["sessions"]:
                conn.execute(
                    "INSERT INTO session(session_id,revision_id,media,cable_id,adapter_type,label_a,label_b,src_rack,src_face,src_u,src_slot,src_port,dst_rack,dst_face,dst_u,dst_slot,dst_port,fiber_a,fiber_b,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        session["session_id"],
                        revision_id,
                        session["media"],
                        session["cable_id"],
                        session["adapter_type"],
                        session["label_a"],
                        session["label_b"],
                        session["src_rack"],
                        session["src_face"],
                        session["src_u"],
                        session["src_slot"],
                        session["src_port"],
                        session["dst_rack"],
                        session["dst_face"],
                        session["dst_u"],
                        session["dst_slot"],
                        session["dst_port"],
                        session["fiber_a"],
                        session["fiber_b"],
                        session["notes"],
                    ),
                )
        return project_id, revision_id

    def list_projects(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM project ORDER BY updated_at DESC").fetchall()

    def list_revisions(self, project_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM revision WHERE project_id=? ORDER BY created_at DESC", (project_id,)
            ).fetchall()

    def get_revision(self, revision_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT * FROM revision WHERE revision_id=?", (revision_id,)
            ).fetchone()

    def save_trial(self, trial_id: str, input_yaml: str, result: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO trial(trial_id,created_at,input_yaml,result_json) VALUES(?,?,?,?)",
                (trial_id, now, input_yaml, json.dumps(result, default=str)),
            )

    def get_trial(self, trial_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute("SELECT * FROM trial WHERE trial_id=?", (trial_id,)).fetchone()
