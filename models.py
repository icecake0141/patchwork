# Copyright 2026 Patchwork Contributors
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator


class AllocationInput(BaseModel):
    project_name: str = Field(min_length=1)
    workers: list[str] = Field(min_length=1)
    tasks: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique(self) -> "AllocationInput":
        if len(set(self.workers)) != len(self.workers):
            raise ValueError("workers に重複があります")
        if len(set(self.tasks)) != len(self.tasks):
            raise ValueError("tasks に重複があります")
        return self

    @classmethod
    def model_validate_yaml(cls, raw_yaml: str) -> "AllocationInput":
        try:
            payload: Any = yaml.safe_load(raw_yaml)
        except yaml.YAMLError as exc:
            raise ValueError(f"YAML parse failed: {exc}") from exc

        if not isinstance(payload, dict):
            raise ValueError("YAMLのトップレベルはオブジェクトである必要があります")

        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(exc.errors()) from exc
