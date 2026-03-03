<!--
Copyright 2026 Patchwork Authors
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# Specification

## Scope
Patchwork allocates deterministic rack-to-rack patch wiring from `project.yaml`.

Supported endpoint types:
- `mmf_lc_duplex`
- `smf_lc_duplex`
- `mpo12`
- `utp_rj45`

## Input Model
Top-level fields:
- `version` (default `1`)
- `project`
- `racks`
- `demands`
- `settings`

Validation rules:
- Unknown keys are rejected (`extra="forbid"`).
- `racks[].id` and `demands[].id` must be unique.
- `demands[].src` and `demands[].dst` must differ.
- `demands[].count` must be greater than `0`.
- Rack references must exist.

## Allocation Behavior
- Default slot category order: `mpo_e2e -> lc_mmf -> lc_smf -> utp`.
- Pair sort strategies:
  - `natural_trailing_digits` (default)
  - `lexicographic`
- Panel settings:
  - `slots_per_u` (default `4`)
  - `allocation_direction`: `top_down` (default) or `bottom_up`
  - `u_label_mode`: `ascending` (default) or `descending` (display only)
- `aggregatable=true` is supported for `mpo12`, `mmf_lc_duplex`, `smf_lc_duplex`.

## Output Model
Primary outputs:
- `sessions.csv`
- `bom.csv`
- `result.json`
- `wiring.svg` / `wiring.drawio`
- `integrated_wiring.drawio`
- `integrated_wiring_interactive.svg` (`mode=aggregate|detailed`)
- `rack_occupancy.drawio`

`result.json` includes:
- `panels`, `modules`, `cables`, `sessions`
- `warnings`, `errors`, `metrics`, `pair_details`

## Integrated Wiring View
- Available on Trial and Project Detail pages.
- Route modes in UI: `direct`, `detour`, `highway`, `stagger`.
- Interactive controls:
  - media and rack filters
  - click-to-focus
  - zoom/pan
  - Gap Jump Scale (`Auto`, `Auto x 0.50`, `0.75`, `1.25`, `1.50`, `2.00`)

## Related Docs
- [API](api.en.md)
- [Testing & Validation](testing.en.md)
