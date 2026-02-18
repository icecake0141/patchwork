# Copyright 2026 Patchwork Contributors
# SPDX-License-Identifier: Apache-2.0
#
# This file was created or modified with the assistance of an AI (Large Language Model).
# Review required for correctness, security, and licensing.

from __future__ import annotations

from models import AllocationInput


def run_trial_allocation(data: AllocationInput) -> dict:
    allocations = []
    workers = data.workers
    for i, task in enumerate(data.tasks):
        worker = workers[i % len(workers)]
        allocations.append(
            {
                "worker": worker,
                "task": task,
                "score": round(1.0 - ((i % len(workers)) * 0.1), 2),
            }
        )

    return {
        "project_name": data.project_name,
        "summary": {
            "workers": len(data.workers),
            "tasks": len(data.tasks),
            "allocations": len(allocations),
        },
        "allocations": allocations,
    }
