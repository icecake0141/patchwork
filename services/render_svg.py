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

from collections import defaultdict


def render_topology_svg(result: dict[str, object]) -> str:
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    for session in result["sessions"]:
        pair = tuple(sorted((session["src_rack"], session["dst_rack"])))
        key = (pair[0], pair[1], session["media"])
        counts[key] += 1

    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600">']
    lines.append('<text x="20" y="30" font-size="20">Rack Topology</text>')
    y = 60
    for (a, b, media), count in sorted(counts.items()):
        lines.append(f'<text x="20" y="{y}" font-size="14">{a} ↔ {b}: {media} x {count}</text>')
        y += 20
    lines.append("</svg>")
    return "\n".join(lines)


def render_rack_panels_svg(result: dict[str, object], rack_id: str) -> str:
    modules = [m for m in result["modules"] if m["rack_id"] == rack_id]
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="800">']
    lines.append(f'<text x="20" y="30" font-size="20">Rack {rack_id} Panels</text>')
    y = 60
    for module in sorted(modules, key=lambda m: (m["panel_u"], m["slot"])):
        lines.append(
            f'<text x="20" y="{y}" font-size="14">'
            f"U{module['panel_u']} S{module['slot']} {module['module_type']}"
            "</text>"
        )
        y += 18
    lines.append("</svg>")
    return "\n".join(lines)


def render_pair_detail_svg(result: dict[str, object], rack_a: str, rack_b: str) -> str:
    sessions = [
        s
        for s in result["sessions"]
        if set((s["src_rack"], s["dst_rack"])) == set((rack_a, rack_b))
    ]
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="900">']
    lines.append(f'<text x="20" y="30" font-size="20">Pair Detail {rack_a} ↔ {rack_b}</text>')
    y = 60
    for session in sorted(
        sessions, key=lambda s: (s["media"], s["src_u"], s["src_slot"], s["src_port"])
    ):
        lines.append(
            f'<text x="20" y="{y}" font-size="13">'
            f"{session['media']} U{session['src_u']}S{session['src_slot']}P{session['src_port']}"
            f" ↔ U{session['dst_u']}S{session['dst_slot']}P{session['dst_port']}"
            "</text>"
        )
        y += 16
    lines.append("</svg>")
    return "\n".join(lines)
