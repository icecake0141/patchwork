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

# API

## Web Endpoints
- `GET /` -> redirect to `/upload`
- `GET /upload`
- `POST /upload` (`project_yaml` multipart field)
- `GET /trial`
- `POST /save`
- `GET /projects/<project_id>?revision_id=<optional>`
- `GET /diff/<project_id>?rev1=<id>&rev2=<id>`
- `GET /pair-svg/<revision_id>/<rack_a>/<rack_b>`

## Export Endpoints
- `GET /revisions/<revision_id>/export/sessions.csv`
- `GET /revisions/<revision_id>/export/bom.csv`
- `GET /revisions/<revision_id>/export/result.json`
- `GET /revisions/<revision_id>/export/wiring.svg`
- `GET /revisions/<revision_id>/export/wiring.drawio`
- `GET /revisions/<revision_id>/export/integrated_wiring.drawio`
- `GET /revisions/<revision_id>/export/integrated_wiring_interactive.svg?mode=aggregate|detailed`
- `GET /revisions/<revision_id>/export/rack_occupancy.drawio`

## Runtime Constraints
- Max upload payload: `1 MiB` (`MAX_CONTENT_LENGTH = 1024 * 1024`)
- Session secret: environment `SECRET_KEY`, fallback `dev-secret`

## Core Python API
- `services.allocator.allocate(project: ProjectInput) -> dict[str, Any]`

The return payload includes:
- `project`, `input_hash`
- `panels`, `modules`, `cables`, `sessions`
- `warnings`, `errors`, `metrics`, `pair_details`

## Diff Rules
Logical diff key:
- `session_id`

Physical diff key:
- `(media, src_rack, src_face, src_u, src_slot, src_port, dst_rack, dst_face, dst_u, dst_slot, dst_port)`

## Related Docs
- [Specification](specification.en.md)
- [User Guide](user-guide.en.md)
