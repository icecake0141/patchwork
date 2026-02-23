<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model).
Review required for correctness, security, and licensing.
-->

# Onboarding Guide for First-Time Users (EN)

This guide explains **what to input** and **what output you get** with two practical patterns.

## Recommended reading order (Table of Contents)
1. Goal and expected outcome
2. Minimal input structure (`project.yaml`)
3. Pattern A — Simple 2-rack project
4. Pattern B — Mixed 4-rack project
5. How to read outputs (`result.json`, `sessions.csv`, `bom.csv`, wiring views)
6. Common validation errors
7. Next steps

## 1) Goal and expected outcome
- You can prepare a valid `project.yaml` from scratch.
- You can predict the shape of generated outputs before running allocation.
- You can read trial/project outputs quickly and verify design intent.

## 2) Minimal input structure (`project.yaml`)
A valid input includes:
- `version`
- `project`
- `racks`
- `demands`
- optional `settings`

For complete field reference, see `examples/quick-start/README.md` and `docs/api.md`.

## 3) Pattern A — Simple 2-rack project
- Document: [Simple 2-rack scenario](scenarios/simple-2rack.en.md)
- Input file: `examples/onboarding/simple-2rack.yaml`
- Use when: starting with one rack pair and one or two media types.

## 4) Pattern B — Mixed 4-rack project
- Document: [Mixed 4-rack scenario](scenarios/mixed-4rack.en.md)
- Input file: `examples/onboarding/mixed-4rack.yaml`
- Use when: validating peer ordering and mixed media in a slightly larger topology.

## 5) How to read outputs
- `result.json`: full allocation model (`panels`, `modules`, `cables`, `sessions`, `metrics`).
- `sessions.csv`: one row per connection (port-level schedule).
- `bom.csv`: required hardware quantities by item type.
- `wiring.svg` / `integrated_wiring.drawio` / `rack_occupancy.drawio`: visual inspection artifacts.

## 6) Common validation errors
- Duplicate rack IDs or demand IDs.
- `src` equals `dst` in a demand.
- `src`/`dst` references an undefined rack.
- Unsupported `endpoint_type` or invalid settings values.

## 7) Next steps
- Run with Web UI (`/upload`) using either onboarding sample.
- Compare generated outputs against expectations in scenario docs.
- Move to your production-like project definition.

## 日本語版
- [オンボーディングガイド（日本語）](README.ja.md)
