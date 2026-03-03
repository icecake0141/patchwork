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

# User Guide

## Basic Flow
1. Open `/upload`.
2. Upload `project.yaml`.
3. Review results in `/trial`.
4. Save a revision from `/save`.
5. Open `/projects/<project_id>` and export artifacts.

## Download Groups (Project Detail)
- Raw Data: `sessions.csv`, `bom.csv`, `result.json`
- Cable Wiring Diagram: `wiring.svg`, `wiring.drawio`
- Integrated Wiring View: `integrated_wiring.drawio`
- Integrated Wiring View (Interactive):
  - `integrated_wiring_interactive.svg?mode=aggregate`
  - `integrated_wiring_interactive.svg?mode=detailed`
- Rack Occupancy: `rack_occupancy.drawio`

## Integrated Wiring Interactions
- Click-to-focus on route or label.
- Click same target again (or blank area) to clear focus.
- Filter by media and rack.
- Zoom/pan with mouse interactions.
- Gap Jump Scale options: `Auto`, `Auto x 0.50`, `0.75`, `1.25`, `1.50`, `2.00`.

## Notes
- Draw.io exports are editable but do not include interactive filtering/focus behavior.
- Interactive SVG is for browser inspection, not Draw.io editing.
