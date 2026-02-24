# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Input models and validation for patchwork project.yaml."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SUPPORTED_ENDPOINT_TYPES = {"mmf_lc_duplex", "smf_lc_duplex", "mpo12", "utp_rj45"}
SUPPORTED_SLOT_CATEGORIES = {"mpo_e2e", "lc_mmf", "lc_smf", "utp"}
SUPPORTED_PEER_SORT_STRATEGIES = {"natural_trailing_digits", "lexicographic"}
SUPPORTED_ALLOCATION_DIRECTIONS = {"top_down", "bottom_up"}


class ProjectMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    note: str | None = None


class RackModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    max_u: int = Field(default=42, gt=0)


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
        default_factory=lambda: {"trunk_polarity": "B", "pass_through_variant": "B"}
    )


class Ordering(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_category_priority: list[str] = Field(
        default_factory=lambda: ["mpo_e2e", "lc_mmf", "lc_smf", "utp"]
    )
    peer_sort: str = "natural_trailing_digits"

    @model_validator(mode="after")
    def validate_slot_category_priority(self) -> "Ordering":
        unknown = [c for c in self.slot_category_priority if c not in SUPPORTED_SLOT_CATEGORIES]
        if unknown:
            raise ValueError(
                f"unknown slot_category_priority entries: {unknown}; "
                f"allowed: {sorted(SUPPORTED_SLOT_CATEGORIES)}"
            )
        if self.peer_sort not in SUPPORTED_PEER_SORT_STRATEGIES:
            raise ValueError(
                f"unsupported peer_sort strategy: {self.peer_sort!r}; "
                f"allowed: {sorted(SUPPORTED_PEER_SORT_STRATEGIES)}"
            )
        return self


class PanelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slots_per_u: int = 4
    allocation_direction: str = "top_down"
    u_label_mode: Literal["ascending", "descending"] = "ascending"

    @model_validator(mode="after")
    def validate_allocation_direction(self) -> "PanelSettings":
        if self.allocation_direction not in SUPPORTED_ALLOCATION_DIRECTIONS:
            raise ValueError(
                f"unsupported allocation_direction: {self.allocation_direction!r}; "
                f"allowed: {sorted(SUPPORTED_ALLOCATION_DIRECTIONS)}"
            )
        return self


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
        demand_ids = [demand.id for demand in self.demands]
        if len(set(demand_ids)) != len(demand_ids):
            raise ValueError("demand ids must be unique")
        rack_set = set(rack_ids)
        for demand in self.demands:
            if demand.src not in rack_set or demand.dst not in rack_set:
                raise ValueError(f"demand {demand.id} references unknown rack")
            if demand.endpoint_type not in SUPPORTED_ENDPOINT_TYPES:
                raise ValueError(f"unsupported endpoint_type in demand {demand.id}")
        return self
