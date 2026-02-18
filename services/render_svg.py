# Copyright 2026 Patchwork Contributors
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations


def render_trial_svg(result: dict) -> str:
    rows = result.get("allocations", [])
    row_height = 30
    height = 40 + (len(rows) * row_height)
    blocks = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{}">'.format(
            height
        ),
        '<rect x="0" y="0" width="900" height="{}" fill="#f9fafb"/>'.format(height),
    ]

    for i, row in enumerate(rows):
        y = 25 + i * row_height
        blocks.append(
            f'<text x="20" y="{y}" font-size="14" fill="#111827">{row["worker"]} → {row["task"]} (score={row["score"]})</text>'
        )

    blocks.append("</svg>")
    return "".join(blocks)
