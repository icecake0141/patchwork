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

import pytest

from models import ProjectYaml


def _base_project() -> dict[str, object]:
    return {
        "version": 1,
        "project": {"name": "p1"},
        "racks": [{"id": "R01", "name": "Rack 1"}, {"id": "R02", "name": "Rack 2"}],
        "demands": [
            {
                "id": "D1",
                "src": "R01",
                "dst": "R02",
                "endpoint_type": "mpo12",
                "count": 1,
            }
        ],
    }


def test_rejects_duplicate_rack_ids() -> None:
    payload = _base_project()
    payload["racks"] = [{"id": "R01", "name": "A"}, {"id": "R01", "name": "B"}]
    with pytest.raises(ValueError, match="Rack IDs must be unique"):
        ProjectYaml.model_validate(payload)


def test_rejects_unknown_endpoint_type() -> None:
    payload = _base_project()
    payload["demands"] = [
        {
            "id": "D1",
            "src": "R01",
            "dst": "R02",
            "endpoint_type": "fc32",
            "count": 1,
        }
    ]
    with pytest.raises(ValueError, match="Unsupported endpoint_type"):
        ProjectYaml.model_validate(payload)


def test_rejects_self_loop_demand() -> None:
    payload = _base_project()
    payload["demands"] = [
        {
            "id": "D1",
            "src": "R01",
            "dst": "R01",
            "endpoint_type": "mpo12",
            "count": 1,
        }
    ]
    with pytest.raises(ValueError, match="src and dst must differ"):
        ProjectYaml.model_validate(payload)
