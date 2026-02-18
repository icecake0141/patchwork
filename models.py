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

from dataclasses import dataclass
from typing import Any

VALID_ENDPOINT_TYPES = {"mmf_lc_duplex", "smf_lc_duplex", "mpo12", "utp_rj45"}


@dataclass(frozen=True)
class Rack:
    id: str
    name: str


@dataclass(frozen=True)
class Demand:
    id: str
    src: str
    dst: str
    endpoint_type: str
    count: int


@dataclass(frozen=True)
class ProjectInfo:
    name: str
    note: str | None = None


@dataclass(frozen=True)
class ProjectYaml:
    version: int
    project: ProjectInfo
    racks: list[Rack]
    demands: list[Demand]

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "ProjectYaml":
        version_raw = data.get("version")
        version = int(version_raw) if version_raw is not None else 0
        if version != 1:
            raise ValueError("version must be 1")

        project_raw = data.get("project")
        if not isinstance(project_raw, dict) or "name" not in project_raw:
            raise ValueError("project.name is required")
        project = ProjectInfo(name=str(project_raw["name"]), note=project_raw.get("note"))

        racks_raw = data.get("racks")
        if not isinstance(racks_raw, list) or len(racks_raw) == 0:
            raise ValueError("racks must be a non-empty list")

        racks: list[Rack] = []
        for raw in racks_raw:
            if not isinstance(raw, dict):
                raise ValueError("rack must be object")
            if "id" not in raw or "name" not in raw:
                raise ValueError("rack.id and rack.name are required")
            racks.append(Rack(id=str(raw["id"]), name=str(raw["name"])))

        demands_raw = data.get("demands")
        if not isinstance(demands_raw, list):
            raise ValueError("demands must be list")

        demands: list[Demand] = []
        for raw in demands_raw:
            if not isinstance(raw, dict):
                raise ValueError("demand must be object")
            endpoint_type = str(raw.get("endpoint_type", ""))
            count = int(raw.get("count", 0))
            if endpoint_type not in VALID_ENDPOINT_TYPES:
                raise ValueError(f"Unsupported endpoint_type: {endpoint_type}")
            if count <= 0:
                raise ValueError("count must be positive")
            if "id" not in raw or "src" not in raw or "dst" not in raw:
                raise ValueError("demand.id/src/dst are required")
            demands.append(
                Demand(
                    id=str(raw["id"]),
                    src=str(raw["src"]),
                    dst=str(raw["dst"]),
                    endpoint_type=endpoint_type,
                    count=count,
                )
            )

        rack_ids = [rack.id for rack in racks]
        if len(set(rack_ids)) != len(rack_ids):
            raise ValueError("Rack IDs must be unique")

        known = set(rack_ids)
        for demand in demands:
            if demand.src == demand.dst:
                raise ValueError(f"Demand {demand.id}: src and dst must differ")
            if demand.src not in known or demand.dst not in known:
                raise ValueError(f"Demand {demand.id}: src/dst must reference known racks")

        return cls(version=version, project=project, racks=racks, demands=demands)
