<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model). Review for correctness and security.
-->

# Integrated Wiring User Guide (One Page)

This page summarizes the newly added capabilities for daily users:

- Download table structure on Project detail page
- Click-to-focus behavior in Integrated Wiring View
- Gap Jump Scale behavior
- Draw.io line jump behavior

## Download Table Structure

Project detail page groups downloads by purpose:

- Raw Data
  - `sessions.csv`: session-level connection table
  - `bom.csv`: Bill of Materials summary
  - `result.json`: full structured allocation result
- Cable Wiring Diagram
  - `wiring.svg`
  - `wiring.drawio`
- Integrated Wiring View
  - `integrated_wiring.drawio` (Aggregate + Detailed pages)
- Integrated Wiring View (Interactive)
  - `integrated_wiring_interactive.svg?mode=aggregate`
  - `integrated_wiring_interactive.svg?mode=detailed`
- Rack Occupancy
  - `rack_occupancy.drawio`

## Integrated Wiring: Click Highlight

- Click a wire or port label to focus related paths.
- Non-related paths are dimmed.
- Click the same target again (or blank area) to clear.
- Works in Trial page, Project detail page, and downloadable interactive SVG.

## Gap Jump Scale

- Default is `Auto`.
- User-selectable multipliers:
  - `Auto × 0.50`
  - `Auto × 0.75`
  - `Auto × 1.25`
  - `Auto × 1.50`
  - `Auto × 2.00`
- Purpose: adjust visual crossing-gap intensity while preserving adaptive baseline.

## Draw.io Line Jump

Draw.io edge exports include:

- `jumpStyle=arc`
- `jumpSize=6`

This improves readability at edge crossings in diagrams.net without adding interactive behavior.

## Fixed Spec: Output Feature Matrix

| Capability | `wiring.svg` | `wiring.drawio` | `integrated_wiring.drawio` | `integrated_wiring_interactive.svg` |
|---|---|---|---|---|
| Primary purpose | Static cable diagram | Editable cable diagram in diagrams.net | Editable integrated view (Aggregate + Detailed pages) | Interactive integrated SVG in browser |
| Editable nodes/edges | No | Yes | Yes | No (SVG DOM interaction only) |
| Draw.io line jump (`jumpStyle=arc`, `jumpSize=6`) | N/A | Yes | Yes | N/A |
| Mode switch (Aggregate / Detailed) | No | No | Yes (page-level) | Yes (in-SVG controls) |
| Media filter controls | No | No | No | Yes |
| Rack filter controls | No | No | No | Yes |
| Click-to-focus highlight | No | No | No | Yes |
| Gap Jump Scale selector | No | No | No | Yes |
| Hover/zoom/pan | No | Via diagrams.net tools | Via diagrams.net tools | Yes (embedded script) |

## Known Constraints / Next Steps

- Draw.io exports are optimized for editability and crossing readability, but do not include interactive filters/focus behavior.
- Interactive SVG focuses on in-browser exploration; it is not intended to become an editable Draw.io graph.
- Future work candidates:
  - Add visual regression snapshots for integrated controls.
  - Add scenario-based E2E acceptance checks in CI artifacts.
