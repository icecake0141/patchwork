# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
from __future__ import annotations

import pytest

from models import ProjectInput


def test_model_validation_rejects_unknown_rack_reference() -> None:
    payload = {
        "version": 1,
        "project": {"name": "x"},
        "racks": [{"id": "R1", "name": "A"}],
        "demands": [
            {"id": "D1", "src": "R1", "dst": "R2", "endpoint_type": "utp_rj45", "count": 1}
        ],
    }
    with pytest.raises(ValueError):
        ProjectInput.model_validate(payload)


def test_model_validation_accepts_aggregatable_flag() -> None:
    payload = {
        "version": 1,
        "project": {"name": "x"},
        "racks": [{"id": "R1", "name": "A"}, {"id": "R2", "name": "B"}],
        "demands": [
            {
                "id": "D1",
                "src": "R1",
                "dst": "R2",
                "endpoint_type": "mpo12",
                "count": 1,
                "aggregatable": True,
            }
        ],
    }
    project = ProjectInput.model_validate(payload)
    assert project.demands[0].aggregatable is True
