# Copyright 2026 Patchwork Contributors
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from models import AllocationInput


def test_model_validate_yaml_success() -> None:
    raw = """
project_name: demo
workers: [alice, bob]
tasks: [task1, task2]
"""
    data = AllocationInput.model_validate_yaml(raw)
    assert data.project_name == "demo"
    assert data.workers == ["alice", "bob"]


def test_model_validate_yaml_duplicate_worker() -> None:
    raw = """
project_name: demo
workers: [alice, alice]
tasks: [task1]
"""
    try:
        AllocationInput.model_validate_yaml(raw)
        assert False, "expected ValueError"
    except ValueError:
        assert True
