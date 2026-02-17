# Copyright 2026 Patchwork Authors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("patchwork.db")


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    ddl = """
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
  FOREIGN KEY(project_id) REFERENCES project(project_id)
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
    with get_connection() as connection:
        connection.executescript(ddl)
        connection.commit()
