# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).
"""Deterministic allocation engine for rack-to-rack patch design."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from math import ceil
from typing import Any

from models import ProjectInput

# Maps each slot category to the (endpoint_type, fiber_kind) pairs it covers.
# "utp" is handled inline in the priority loop and has no entries here.
_CATEGORY_ENDPOINTS: dict[str, list[tuple[str, str | None]]] = {
    "mpo_e2e": [("mpo12", None)],
    "lc_mmf": [("mmf_lc_duplex", "mmf")],
    "lc_smf": [("smf_lc_duplex", "smf")],
    "utp": [],
}


def natural_sort_key(value: str) -> tuple[int, Any, str]:
    match = re.search(r"(\d+)$", value)
    if not match:
        return (1, value, value)
    return (0, int(match.group(1)), value)


def pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b), key=natural_sort_key))  # type: ignore[return-value]


def deterministic_id(prefix: str, canonical: str, length: int = 16) -> str:
    return f"{prefix}_{sha256(canonical.encode('utf-8')).hexdigest()[:length]}"


def label(rack: str, u: int, slot: int, port: int) -> str:
    return f"{rack}U{u}S{slot}P{port}"


LC_FIBER_MAP = {
    1: (1, 2),
    2: (3, 4),
    3: (5, 6),
    4: (7, 8),
    5: (9, 10),
    6: (11, 12),
}


def _normalize_mpo_pass_through_variant(variant: str | None) -> str:
    if not variant:
        return "B"
    compact = "".join(ch for ch in str(variant).upper() if ch.isalnum())
    if compact in {"TYPEB", "B"}:
        return "B"
    return "B"


def _complement_mpo_pass_through_variant(variant: str) -> str:
    normalized = _normalize_mpo_pass_through_variant(variant)
    return normalized


def _normalize_lc_breakout_variant(variant: str | None) -> str:
    if not variant:
        return "AF"
    compact = "".join(ch for ch in str(variant).upper() if ch.isalnum())
    if compact in {"TYPEA", "A"}:
        return "A"
    if compact in {"TYPEAF", "AF"}:
        return "AF"
    return str(variant)


def _complement_lc_breakout_variant(variant: str) -> str:
    normalized = _normalize_lc_breakout_variant(variant)
    if normalized == "A":
        return "AF"
    if normalized == "AF":
        return "A"
    return normalized


def _map_mpo_pass_through_dst_core(
    src_core: int,
    src_variant: str,
    dst_variant: str,
) -> int:
    _ = _normalize_mpo_pass_through_variant(src_variant)
    _ = _normalize_mpo_pass_through_variant(dst_variant)
    return 13 - src_core


@dataclass
class SlotRef:
    rack_id: str
    u: int
    slot: int


class RackOverflowError(Exception):
    """Raised when a rack's U capacity is exceeded."""


class RackSlotAllocator:
    def __init__(
        self,
        rack_id: str,
        slots_per_u: int = 4,
        max_u: int = 42,
        allocation_direction: str = "top_down",
    ):
        self.rack_id = rack_id
        self.slots_per_u = slots_per_u
        self.max_u = max_u
        self.allocation_direction = allocation_direction
        self.next_index = 0
        self.panels: set[int] = set()

    def reserve_slot(self) -> SlotRef:
        self.next_index += 1
        idx = self.next_index
        panel_index = (idx - 1) // self.slots_per_u  # 0-based panel number
        slot = (idx - 1) % self.slots_per_u + 1
        if self.allocation_direction == "bottom_up":
            u = self.max_u - panel_index
            if u < 1:
                raise RackOverflowError(
                    f"Rack {self.rack_id}: allocation requires U{u} which is below minimum U1"
                )
        else:
            u = panel_index + 1
            if u > self.max_u:
                raise RackOverflowError(
                    f"Rack {self.rack_id}: required U{u} exceeds max_u={self.max_u}"
                )
        self.panels.add(u)
        return SlotRef(self.rack_id, u, slot)


def _build_cable(
    media: str,
    src: SlotRef,
    src_port: int,
    dst: SlotRef,
    dst_port: int,
    polarity: str | None,
    fiber_kind: str | None = None,
) -> dict[str, Any]:
    cable_type = "utp_cable" if media == "utp_rj45" else "mpo12_trunk"
    canonical = f"{media}|{src.rack_id}|{src.u}|{src.slot}|{src_port}|{dst.rack_id}|{dst.u}|{dst.slot}|{dst_port}|{polarity or ''}"
    cable_id = deterministic_id("cab", canonical)
    return {
        "cable_id": cable_id,
        "cable_type": cable_type,
        "fiber_kind": fiber_kind,
        "polarity_type": polarity,
    }


def _session(
    media: str,
    cable_id: str,
    adapter_type: str,
    src: SlotRef,
    src_port: int,
    dst: SlotRef,
    dst_port: int,
    fiber_pair: tuple[int, int] | None = None,
    src_core: int | None = None,
    dst_core: int | None = None,
) -> dict[str, Any]:
    canonical = (
        f"{media}|{src.rack_id}|{src.u}|{src.slot}|{src_port}|"
        f"{dst.rack_id}|{dst.u}|{dst.slot}|{dst_port}|{cable_id}|{fiber_pair or ''}|"
        f"{src_core if src_core is not None else ''}|{dst_core if dst_core is not None else ''}"
    )
    session_id = deterministic_id("ses", canonical)
    return {
        "session_id": session_id,
        "media": media,
        "cable_id": cable_id,
        "adapter_type": adapter_type,
        "label_a": label(src.rack_id, src.u, src.slot, src_port),
        "label_b": label(dst.rack_id, dst.u, dst.slot, dst_port),
        "src_rack": src.rack_id,
        "src_face": "front",
        "src_u": src.u,
        "src_slot": src.slot,
        "src_port": src_port,
        "dst_rack": dst.rack_id,
        "dst_face": "front",
        "dst_u": dst.u,
        "dst_slot": dst.slot,
        "dst_port": dst_port,
        "src_core": src_core,
        "dst_core": dst_core,
        "fiber_a": fiber_pair[0] if fiber_pair else None,
        "fiber_b": fiber_pair[1] if fiber_pair else None,
        "notes": "",
    }


def allocate(project: ProjectInput) -> dict[str, Any]:
    rack_allocators = {
        rack.id: RackSlotAllocator(
            rack.id,
            project.settings.panel.slots_per_u,
            rack.max_u,
            project.settings.panel.allocation_direction,
        )
        for rack in project.racks
    }
    modules: list[dict[str, Any]] = []
    cables: dict[str, dict[str, Any]] = {}
    sessions: list[dict[str, Any]] = []
    warnings: list[str] = []
    pair_details: dict[str, list[dict[str, Any]]] = defaultdict(list)

    fp = project.settings.fixed_profiles
    mpo_polarity = "B"
    mpo_variant = _normalize_mpo_pass_through_variant(fp.mpo_e2e.get("pass_through_variant", "B"))
    lc_polarity = fp.lc_demands.get("trunk_polarity", "A")
    lc_variant = _normalize_lc_breakout_variant(fp.lc_demands.get("breakout_module_variant", "AF"))

    normalized_demands: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for d in project.demands:
        pk = pair_key(d.src, d.dst)
        normalized_demands[pk][d.endpoint_type] += d.count

    peer_sort_strategy = project.settings.ordering.peer_sort
    pair_sort_key = str if peer_sort_strategy == "lexicographic" else natural_sort_key
    sorted_pairs = sorted(
        normalized_demands.keys(),
        key=lambda p: (pair_sort_key(p[0]), pair_sort_key(p[1])),
    )

    errors: list[str] = []
    priority = project.settings.ordering.slot_category_priority

    # UTP: aggregate counts by rack-peer pair (used when "utp" appears in priority)
    rack_peer_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (a, b), payload in normalized_demands.items():
        utp = payload.get("utp_rj45", 0)
        if utp:
            rack_peer_counts[a][b] += utp
            rack_peer_counts[b][a] += utp

    utp_ports: dict[str, dict[str, list[tuple[SlotRef, int]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for category in priority:
        if category == "utp":
            # Allocate UTP slots at this priority position
            for rack_id, peer_counts in rack_peer_counts.items():
                peers = sorted(
                    peer_counts.keys(),
                    key=str if peer_sort_strategy == "lexicographic" else natural_sort_key,
                )
                current_slot: SlotRef | None = None
                used_in_slot = 0
                for peer in peers:
                    remaining = peer_counts[peer]
                    while remaining > 0:
                        if current_slot is None or used_in_slot == 6:
                            try:
                                current_slot = rack_allocators[rack_id].reserve_slot()
                            except RackOverflowError as exc:
                                errors.append(str(exc))
                                remaining = 0
                                break
                            used_in_slot = 0
                            modules.append(
                                {
                                    "module_id": deterministic_id(
                                        "mod",
                                        f"{rack_id}|{current_slot.u}|{current_slot.slot}|utp",
                                    ),
                                    "rack_id": rack_id,
                                    "panel_u": current_slot.u,
                                    "slot": current_slot.slot,
                                    "module_type": "utp_6xrj45",
                                    "fiber_kind": None,
                                    "polarity_variant": None,
                                    "peer_rack_id": None,
                                    "dedicated": 0,
                                }
                            )
                        port = used_in_slot + 1
                        utp_ports[rack_id][peer].append((current_slot, port))
                        used_in_slot += 1
                        remaining -= 1
            continue

        for endpoint, fiber_kind in _CATEGORY_ENDPOINTS[category]:
            for a, b in sorted_pairs:
                count = normalized_demands[(a, b)].get(endpoint, 0)
                if not count:
                    continue
                slots_needed = ceil(count / 12)
                for i in range(slots_needed):
                    try:
                        slot_a = rack_allocators[a].reserve_slot()
                        slot_b = rack_allocators[b].reserve_slot()
                    except RackOverflowError as exc:
                        errors.append(str(exc))
                        break
                    if endpoint == "mpo12":
                        module_type = "mpo12_pass_through_12port"
                        variant_a = mpo_variant
                        variant_b = _complement_mpo_pass_through_variant(mpo_variant)
                        modules.extend(
                            [
                                {
                                    "module_id": deterministic_id(
                                        "mod", f"{a}|{slot_a.u}|{slot_a.slot}|mpo|{b}|{i + 1}"
                                    ),
                                    "rack_id": a,
                                    "panel_u": slot_a.u,
                                    "slot": slot_a.slot,
                                    "module_type": module_type,
                                    "fiber_kind": None,
                                    "polarity_variant": variant_a,
                                    "peer_rack_id": b,
                                    "dedicated": 1,
                                },
                                {
                                    "module_id": deterministic_id(
                                        "mod", f"{b}|{slot_b.u}|{slot_b.slot}|mpo|{a}|{i + 1}"
                                    ),
                                    "rack_id": b,
                                    "panel_u": slot_b.u,
                                    "slot": slot_b.slot,
                                    "module_type": module_type,
                                    "fiber_kind": None,
                                    "polarity_variant": variant_b,
                                    "peer_rack_id": a,
                                    "dedicated": 1,
                                },
                            ]
                        )
                        used = min(12, count - i * 12)
                        pair_details[f"{a}__{b}"].append(
                            {
                                "type": "mpo12",
                                "slot_a": {
                                    "rack_id": slot_a.rack_id,
                                    "u": slot_a.u,
                                    "slot": slot_a.slot,
                                },
                                "slot_b": {
                                    "rack_id": slot_b.rack_id,
                                    "u": slot_b.u,
                                    "slot": slot_b.slot,
                                },
                                "used": used,
                            }
                        )
                        for port in range(1, used + 1):
                            src_port = port
                            dst_port = src_port
                            src_core = src_port
                            dst_core = _map_mpo_pass_through_dst_core(
                                src_core,
                                src_variant=variant_a,
                                dst_variant=variant_b,
                            )
                            cable = _build_cable(
                                "mpo12", slot_a, src_port, slot_b, dst_port, polarity=mpo_polarity
                            )
                            cables.setdefault(cable["cable_id"], cable)
                            sessions.append(
                                _session(
                                    "mpo12",
                                    cable["cable_id"],
                                    module_type,
                                    slot_a,
                                    src_port,
                                    slot_b,
                                    dst_port,
                                    src_core=src_core,
                                    dst_core=dst_core,
                                )
                            )
                    else:
                        # LC breakout (mmf or smf)
                        module_type = "lc_breakout_2xmpo12_to_12xlcduplex"
                        variant_a = lc_variant
                        variant_b = _complement_lc_breakout_variant(lc_variant)
                        modules.extend(
                            [
                                {
                                    "module_id": deterministic_id(
                                        "mod",
                                        f"{a}|{slot_a.u}|{slot_a.slot}|{endpoint}|{b}|{i + 1}",
                                    ),
                                    "rack_id": a,
                                    "panel_u": slot_a.u,
                                    "slot": slot_a.slot,
                                    "module_type": module_type,
                                    "fiber_kind": fiber_kind,
                                    "polarity_variant": variant_a,
                                    "peer_rack_id": b,
                                    "dedicated": 1,
                                },
                                {
                                    "module_id": deterministic_id(
                                        "mod",
                                        f"{b}|{slot_b.u}|{slot_b.slot}|{endpoint}|{a}|{i + 1}",
                                    ),
                                    "rack_id": b,
                                    "panel_u": slot_b.u,
                                    "slot": slot_b.slot,
                                    "module_type": module_type,
                                    "fiber_kind": fiber_kind,
                                    "polarity_variant": variant_b,
                                    "peer_rack_id": a,
                                    "dedicated": 1,
                                },
                            ]
                        )
                        used = min(12, count - i * 12)
                        pair_details[f"{a}__{b}"].append(
                            {
                                "type": endpoint,
                                "slot_a": {
                                    "rack_id": slot_a.rack_id,
                                    "u": slot_a.u,
                                    "slot": slot_a.slot,
                                },
                                "slot_b": {
                                    "rack_id": slot_b.rack_id,
                                    "u": slot_b.u,
                                    "slot": slot_b.slot,
                                },
                                "used": used,
                            }
                        )
                        trunk_by_mpo: dict[int, str] = {}
                        for mpo_port in (1, 2):
                            cable = _build_cable(
                                endpoint,
                                slot_a,
                                mpo_port,
                                slot_b,
                                mpo_port,
                                polarity=lc_polarity,
                                fiber_kind=fiber_kind,
                            )
                            cables.setdefault(cable["cable_id"], cable)
                            trunk_by_mpo[mpo_port] = cable["cable_id"]
                        for lc_port in range(1, used + 1):
                            mpo_port = 1 if lc_port <= 6 else 2
                            mpo_local = lc_port if lc_port <= 6 else lc_port - 6
                            fibers = LC_FIBER_MAP[mpo_local]
                            sessions.append(
                                _session(
                                    endpoint,
                                    trunk_by_mpo[mpo_port],
                                    module_type,
                                    slot_a,
                                    lc_port,
                                    slot_b,
                                    lc_port,
                                    fiber_pair=fibers,
                                )
                            )

    for a, b in sorted_pairs:
        count = normalized_demands[(a, b)].get("utp_rj45", 0)
        if not count:
            continue
        a_ports = utp_ports[a][b]
        b_ports = utp_ports[b][a]
        if len(a_ports) != len(b_ports):
            warnings.append(f"UTP allocation mismatch for pair {a}-{b}")
        for idx in range(min(len(a_ports), len(b_ports))):
            slot_a, port_a = a_ports[idx]
            slot_b, port_b = b_ports[idx]
            cable = _build_cable("utp_rj45", slot_a, port_a, slot_b, port_b, polarity=None)
            cables.setdefault(cable["cable_id"], cable)
            sessions.append(
                _session(
                    "utp_rj45", cable["cable_id"], "utp_6xrj45", slot_a, port_a, slot_b, port_b
                )
            )

    panels: list[dict[str, Any]] = []
    for rack_id, allocator in rack_allocators.items():
        for u in sorted(allocator.panels):
            panels.append(
                {
                    "panel_id": deterministic_id(
                        "pan", f"{rack_id}|{u}|{project.settings.panel.slots_per_u}"
                    ),
                    "rack_id": rack_id,
                    "u": u,
                    "slots_per_u": project.settings.panel.slots_per_u,
                }
            )

    sorted_cables = sorted(cables.values(), key=lambda c: c["cable_id"])
    for seq, cable in enumerate(sorted_cables, start=1):
        cable["cable_seq"] = seq

    input_hash = sha256(
        json.dumps(project.model_dump(), sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "project": project.model_dump(),
        "input_hash": input_hash,
        "panels": sorted(panels, key=lambda p: (natural_sort_key(p["rack_id"]), p["u"])),
        "modules": sorted(
            modules, key=lambda m: (natural_sort_key(m["rack_id"]), m["panel_u"], m["slot"])
        ),
        "cables": sorted_cables,
        "sessions": sorted(sessions, key=lambda s: s["session_id"]),
        "warnings": warnings,
        "errors": errors,
        "metrics": {
            "rack_count": len(project.racks),
            "panel_count": len(panels),
            "module_count": len(modules),
            "cable_count": len(cables),
            "session_count": len(sessions),
        },
        "pair_details": pair_details,
    }
