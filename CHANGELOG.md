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

# Changelog

## Unreleased
- Added GitHub Actions CI workflow to run linting, formatting checks, type checks, tests, and pre-commit hooks.
- Added editable Draw.io exports for wiring, integrated wiring (Aggregate/Detailed pages), and rack occupancy (single-sheet).
- Added Draw.io edge line-jump styling (`jumpStyle=arc`, `jumpSize=6`) to improve crossing readability.
- Added integrated interactive SVG export and in-page interaction upgrades:
    media/rack filters, click-to-focus highlighting, and Gap Jump Scale controls.
- Added BoM table visibility in Trial/Project UI and reorganized download links with grouped English descriptions.

## 0.1.0
- Rebuilt the application from scratch based on the v0 design spec.
- Added deterministic allocator for MPO/LC/UTP, exports, and SVG rendering.
- Added Flask WebUI flow for upload/trial/save/project/diff.
- Added SQLite persistence schema aligned with specification.
