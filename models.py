# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Input models and validation for patchwork project.yaml."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SUPPORTED_ENDPOINT_TYPES = {"mmf_lc_duplex", "smf_lc_duplex", "mpo12", "utp_rj45"}


class ProjectMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    note: str | None = None


class RackModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str


class DemandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    src: str
    dst: str
    endpoint_type: Literal["mmf_lc_duplex", "smf_lc_duplex", "mpo12", "utp_rj45"]
    count: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_src_dst(self) -> "DemandModel":
        if self.src == self.dst:
            raise ValueError("src and dst must be different")
        return self


class FixedProfiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lc_demands: dict[str, str] = Field(
        default_factory=lambda: {"trunk_polarity": "A", "breakout_module_variant": "AF"}
    )
    mpo_e2e: dict[str, str] = Field(
        default_factory=lambda: {"trunk_polarity": "B", "pass_through_variant": "A"}
    )


class Ordering(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_category_priority: list[str] = Field(
        default_factory=lambda: ["mpo_e2e", "lc_mmf", "lc_smf", "utp"]
    )
    peer_sort: str = "natural_trailing_digits"


class PanelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slots_per_u: int = 4
    allocation_direction: str = "top_down"


class SettingsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixed_profiles: FixedProfiles = Field(default_factory=FixedProfiles)
    ordering: Ordering = Field(default_factory=Ordering)
    panel: PanelSettings = Field(default_factory=PanelSettings)


class ProjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    project: ProjectMeta
    racks: list[RackModel]
    demands: list[DemandModel]
    settings: SettingsModel = Field(default_factory=SettingsModel)

    @model_validator(mode="after")
    def validate_references(self) -> "ProjectInput":
        rack_ids = [rack.id for rack in self.racks]
        if len(set(rack_ids)) != len(rack_ids):
            raise ValueError("rack ids must be unique")
        rack_set = set(rack_ids)
        for demand in self.demands:
            if demand.src not in rack_set or demand.dst not in rack_set:
                raise ValueError(f"demand {demand.id} references unknown rack")
            if demand.endpoint_type not in SUPPORTED_ENDPOINT_TYPES:
                raise ValueError(f"unsupported endpoint_type in demand {demand.id}")
        return self
