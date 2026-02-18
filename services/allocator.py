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

import re
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from math import ceil
from typing import Any

from models import ProjectYaml


def stable_id(canonical: str) -> str:
    return sha256(canonical.encode("utf-8")).hexdigest()[:16]


def natural_sort_key(value: str) -> tuple[int, int, str, str]:
    matched = re.search(r"(\d+)$", value)
    if matched:
        return (0, int(matched.group(1)), value[: matched.start()], value)
    return (1, 0, "", value)


@dataclass(frozen=True)
class SlotRef:
    rack_id: str
    u: int
    slot: int


class RackAllocator:
    def __init__(self, rack_id: str) -> None:
        self.rack_id = rack_id
        self.next_slot_index = 0

    def allocate_slot(self) -> tuple[int, int]:
        self.next_slot_index += 1
        index = self.next_slot_index - 1
        return (index // 4 + 1, index % 4 + 1)


def _ordered_pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if natural_sort_key(a) <= natural_sort_key(b) else (b, a)


def _add_panel_if_needed(
    panels: dict[tuple[str, int], dict[str, object]], rack_id: str, u: int
) -> None:
    key = (rack_id, u)
    if key not in panels:
        canonical = f"panel|{rack_id}|u={u}"
        panels[key] = {
            "panel_id": stable_id(canonical),
            "rack_id": rack_id,
            "u": u,
            "slots_per_u": 4,
        }


def allocate_project(project: ProjectYaml) -> dict[str, Any]:
    rack_allocators = {rack.id: RackAllocator(rack.id) for rack in project.racks}
    panels: dict[tuple[str, int], dict[str, Any]] = {}
    modules: list[dict[str, Any]] = []
    cables: dict[str, dict[str, Any]] = {}
    sessions: list[dict[str, Any]] = []

    by_pair_media: dict[tuple[str, str, str], int] = defaultdict(int)
    for demand in project.demands:
        a, b = _ordered_pair(demand.src, demand.dst)
        by_pair_media[(a, b, demand.endpoint_type)] += demand.count

    # 1) MPO E2E
    for (a, b, media), count in sorted(by_pair_media.items()):
        if media != "mpo12":
            continue
        slots = ceil(count / 12)
        for i in range(slots):
            ua, sa = rack_allocators[a].allocate_slot()
            ub, sb = rack_allocators[b].allocate_slot()
            _add_panel_if_needed(panels, a, ua)
            _add_panel_if_needed(panels, b, ub)
            for rack_id, u, slot, peer in ((a, ua, sa, b), (b, ub, sb, a)):
                module_canonical = (
                    f"module|{rack_id}|u={u}|slot={slot}|mpo12_pass_through_12port|peer={peer}"
                )
                modules.append(
                    {
                        "module_id": stable_id(module_canonical),
                        "rack_id": rack_id,
                        "panel_u": u,
                        "slot": slot,
                        "module_type": "mpo12_pass_through_12port",
                        "fiber_kind": None,
                        "polarity_variant": "A",
                        "peer_rack_id": peer,
                        "dedicated": 1,
                    }
                )
            use_ports = min(12, count - i * 12)
            for port in range(1, use_ports + 1):
                cable_canon = f"cable|mpo12|{a}|{ua}|{sa}|{port}|{b}|{ub}|{sb}|{port}|B"
                cable_id = stable_id(cable_canon)
                cables[cable_id] = {
                    "cable_id": cable_id,
                    "cable_type": "mpo12_trunk",
                    "fiber_kind": None,
                    "polarity_type": "B",
                }
                session_canon = f"media=mpo12|{a}|{ua}|{sa}|{port}|{b}|{ub}|{sb}|{port}|{cable_id}"
                session_id = stable_id(session_canon)
                sessions.append(
                    {
                        "session_id": session_id,
                        "media": "mpo12",
                        "cable_id": cable_id,
                        "adapter_type": "mpo12_pass_through_12port",
                        "src_rack": a,
                        "src_face": "front",
                        "src_u": ua,
                        "src_slot": sa,
                        "src_port": port,
                        "dst_rack": b,
                        "dst_face": "front",
                        "dst_u": ub,
                        "dst_slot": sb,
                        "dst_port": port,
                        "fiber_a": None,
                        "fiber_b": None,
                        "notes": "",
                    }
                )

    # 2) LC MMF then SMF
    lc_order = (("mmf_lc_duplex", "mmf"), ("smf_lc_duplex", "smf"))
    for media, fiber_kind in lc_order:
        for (a, b, endpoint), count in sorted(by_pair_media.items()):
            if endpoint != media:
                continue
            module_count = ceil(count / 12)
            for i in range(module_count):
                ua, sa = rack_allocators[a].allocate_slot()
                ub, sb = rack_allocators[b].allocate_slot()
                _add_panel_if_needed(panels, a, ua)
                _add_panel_if_needed(panels, b, ub)
                for rack_id, u, slot, peer in ((a, ua, sa, b), (b, ub, sb, a)):
                    module_canonical = (
                        f"module|{rack_id}|u={u}|slot={slot}|lc_breakout_2xmpo12_to_12xlcduplex"
                        f"|fiber={fiber_kind}|peer={peer}|AF"
                    )
                    modules.append(
                        {
                            "module_id": stable_id(module_canonical),
                            "rack_id": rack_id,
                            "panel_u": u,
                            "slot": slot,
                            "module_type": "lc_breakout_2xmpo12_to_12xlcduplex",
                            "fiber_kind": fiber_kind,
                            "polarity_variant": "AF",
                            "peer_rack_id": peer,
                            "dedicated": 1,
                        }
                    )
                use_ports = min(12, count - i * 12)
                module_trunks: dict[int, str] = {}
                for mpo_port in (1, 2):
                    cable_canon = (
                        f"cable|{media}|module={i+1}|mpo={mpo_port}|{a}|{ua}|{sa}|{b}|{ub}|{sb}|A"
                    )
                    cable_id = stable_id(cable_canon)
                    cables[cable_id] = {
                        "cable_id": cable_id,
                        "cable_type": "mpo12_trunk",
                        "fiber_kind": fiber_kind,
                        "polarity_type": "A",
                    }
                    module_trunks[mpo_port] = cable_id
                for lc_port in range(1, use_ports + 1):
                    mpo_port = 1 if lc_port <= 6 else 2
                    local = lc_port if lc_port <= 6 else lc_port - 6
                    fiber_a = (local - 1) * 2 + 1
                    fiber_b = fiber_a + 1
                    cable_id = module_trunks[mpo_port]
                    session_canon = (
                        f"media|{media}|{a}|{ua}|{sa}|{lc_port}|{b}|{ub}|{sb}|{lc_port}|"
                        f"{cable_id}|{fiber_a}-{fiber_b}"
                    )
                    sessions.append(
                        {
                            "session_id": stable_id(session_canon),
                            "media": media,
                            "cable_id": cable_id,
                            "adapter_type": "lc_breakout_2xmpo12_to_12xlcduplex",
                            "src_rack": a,
                            "src_face": "front",
                            "src_u": ua,
                            "src_slot": sa,
                            "src_port": lc_port,
                            "dst_rack": b,
                            "dst_face": "front",
                            "dst_u": ub,
                            "dst_slot": sb,
                            "dst_port": lc_port,
                            "fiber_a": fiber_a,
                            "fiber_b": fiber_b,
                            "notes": "",
                        }
                    )

    # 3) UTP
    utp_pair_counts: dict[tuple[str, str], int] = {}
    per_rack_peer: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (a, b, media), count in by_pair_media.items():
        if media != "utp_rj45":
            continue
        utp_pair_counts[(a, b)] = count
        per_rack_peer[a][b] += count
        per_rack_peer[b][a] += count

    utp_assignments: dict[str, dict[str, list[tuple[int, int, int]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for rack in sorted(per_rack_peer, key=natural_sort_key):
        peers = sorted(per_rack_peer[rack], key=natural_sort_key)
        u, slot, port = 0, 0, 6
        for peer in peers:
            remain = per_rack_peer[rack][peer]
            while remain > 0:
                if port == 6:
                    u, slot = rack_allocators[rack].allocate_slot()
                    _add_panel_if_needed(panels, rack, u)
                    module_canonical = f"module|{rack}|u={u}|slot={slot}|utp_6xrj45|shared"
                    modules.append(
                        {
                            "module_id": stable_id(module_canonical),
                            "rack_id": rack,
                            "panel_u": u,
                            "slot": slot,
                            "module_type": "utp_6xrj45",
                            "fiber_kind": None,
                            "polarity_variant": None,
                            "peer_rack_id": None,
                            "dedicated": 0,
                        }
                    )
                    port = 0
                port += 1
                utp_assignments[rack][peer].append((u, slot, port))
                remain -= 1

    for a, b in sorted(utp_pair_counts):
        count = utp_pair_counts[(a, b)]
        left = utp_assignments[a][b]
        right = utp_assignments[b][a]
        for i in range(count):
            ua, sa, pa = left[i]
            ub, sb, pb = right[i]
            cable_canon = f"cable|utp|{a}|{ua}|{sa}|{pa}|{b}|{ub}|{sb}|{pb}"
            cable_id = stable_id(cable_canon)
            cables[cable_id] = {
                "cable_id": cable_id,
                "cable_type": "utp_cable",
                "fiber_kind": None,
                "polarity_type": None,
            }
            session_canon = f"media=utp_rj45|{a}|{ua}|{sa}|{pa}|{b}|{ub}|{sb}|{pb}|{cable_id}"
            sessions.append(
                {
                    "session_id": stable_id(session_canon),
                    "media": "utp_rj45",
                    "cable_id": cable_id,
                    "adapter_type": "utp_6xrj45",
                    "src_rack": a,
                    "src_face": "front",
                    "src_u": ua,
                    "src_slot": sa,
                    "src_port": pa,
                    "dst_rack": b,
                    "dst_face": "front",
                    "dst_u": ub,
                    "dst_slot": sb,
                    "dst_port": pb,
                    "fiber_a": None,
                    "fiber_b": None,
                    "notes": "",
                }
            )

    sessions.sort(key=lambda row: str(row["session_id"]))
    return {
        "project": {"name": project.project.name, "version": project.version},
        "panels": sorted(panels.values(), key=lambda p: (str(p["rack_id"]), int(str(p["u"])))),
        "modules": sorted(
            modules, key=lambda m: (str(m["rack_id"]), int(str(m["panel_u"])), int(str(m["slot"])))
        ),
        "cables": sorted(cables.values(), key=lambda c: str(c["cable_id"])),
        "sessions": sessions,
        "warnings": [],
        "metrics": {
            "panel_count": len(panels),
            "module_count": len(modules),
            "cable_count": len(cables),
            "session_count": len(sessions),
        },
    }
