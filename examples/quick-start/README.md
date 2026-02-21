<!-- SPDX-License-Identifier: Apache-2.0 -->
<!--
This file was created or modified with the assistance of an AI (Large Language Model). Review for correctness and security.
-->

# Quick Start (Example)

This quick-start demonstrates a minimal workflow to run Patchwork locally and process a sample project.

## Prerequisites
- Python 3.10+
- virtualenv

## Steps

### 1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the app (Flask WebUI)
```bash
python app.py
```
Open http://localhost:5000/upload

### 4. Upload the sample project file

Upload `examples/quick-start/sample-project.yaml` via the Web UI at http://localhost:5000/upload.

### 5. Export / view results

After allocation, use the UI to download:
- `sessions.csv` — per-port patch wiring schedule
- `bom.csv` — Bill of Materials (panels, modules, cables)
- `result.json` — full structured allocation result

---

## Input Format — `project.yaml`

A `project.yaml` file describes racks, demands, and optional settings.

### Top-level fields

| Field      | Type    | Required | Description |
|------------|---------|----------|-------------|
| `version`  | integer | Yes      | Schema version. Must be `1`. |
| `project`  | object  | Yes      | Project metadata (`name`, optional `note`). |
| `racks`    | list    | Yes      | Rack definitions (see below). |
| `demands`  | list    | Yes      | Cabling demands (see below). |
| `settings` | object  | No       | Allocation settings (defaults shown below). |

### `racks` items

| Field    | Type    | Required | Description |
|----------|---------|----------|-------------|
| `id`     | string  | Yes      | Unique rack identifier (e.g. `R01`). |
| `name`   | string  | Yes      | Human-readable rack name. |
| `max_u`  | integer | No       | Rack height in U. Default: `42`. |

### `demands` items

| Field           | Type    | Required | Description |
|-----------------|---------|----------|-------------|
| `id`            | string  | Yes      | Unique demand identifier (e.g. `D001`). |
| `src`           | string  | Yes      | Source rack `id`. |
| `dst`           | string  | Yes      | Destination rack `id`. |
| `endpoint_type` | string  | Yes      | Connection type. One of: `mmf_lc_duplex`, `smf_lc_duplex`, `mpo12`, `utp_rj45`. |
| `count`         | integer | Yes      | Number of connections required (> 0). |

### `settings` (optional, all fields have defaults)

```yaml
settings:
  fixed_profiles:
    lc_demands:
      trunk_polarity: A          # "A" or "B"
      breakout_module_variant: AF
    mpo_e2e:
      trunk_polarity: B
      pass_through_variant: A
  ordering:
    slot_category_priority: [mpo_e2e, lc_mmf, lc_smf, utp]
    peer_sort: natural_trailing_digits
  panel:
    slots_per_u: 4               # Slots per 1U patch panel
    allocation_direction: top_down
```

### Sample `project.yaml`

```yaml
version: 1
project:
  name: example-dc-cabling
  note: optional free-text note
racks:
  - id: R01
    name: Rack-01
    max_u: 42
  - id: R02
    name: Rack-02
    max_u: 42
  - id: R03
    name: Rack-03
    max_u: 42
demands:
  - id: D001
    src: R01
    dst: R02
    endpoint_type: mmf_lc_duplex
    count: 13
  - id: D002
    src: R01
    dst: R02
    endpoint_type: mpo12
    count: 14
  - id: D003
    src: R01
    dst: R03
    endpoint_type: utp_rj45
    count: 8
```

See `sample-project.yaml` in this directory for the full version including `settings`.

---

## Output Files

### `sessions.csv`

One row per port-to-port patch connection. Columns:

| Column        | Description |
|---------------|-------------|
| `project_id`  | Saved project identifier. |
| `revision_id` | Saved revision identifier. |
| `session_id`  | Deterministic unique ID for this port assignment. |
| `media`       | Connection type (`mmf_lc_duplex`, `smf_lc_duplex`, `mpo12`, `utp_rj45`). |
| `cable_id`    | Cable identifier (shared across ports on the same cable). |
| `cable_seq`   | Sequential cable number for ordering. |
| `adapter_type`| Panel module type used at both ends. |
| `label_a`     | Source label (format: `{rack}U{u}S{slot}P{port}`). |
| `label_b`     | Destination label. |
| `src_rack`    | Source rack ID. |
| `src_face`    | Panel face (`front`). |
| `src_u`       | Panel U position (1-indexed from top). |
| `src_slot`    | Slot within the U (1-indexed). |
| `src_port`    | Port within the slot (1-indexed). |
| `dst_rack`    | Destination rack ID. |
| `dst_face`    | Panel face (`front`). |
| `dst_u`       | Panel U position. |
| `dst_slot`    | Slot within the U. |
| `dst_port`    | Port within the slot. |
| `fiber_a`     | Fiber strand number at source (LC only). |
| `fiber_b`     | Fiber strand number at destination (LC only). |
| `notes`       | Free-text notes (empty by default). |

Sample `sessions.csv` excerpt:
```
project_id,revision_id,session_id,media,cable_id,cable_seq,adapter_type,label_a,label_b,src_rack,src_face,src_u,src_slot,src_port,dst_rack,dst_face,dst_u,dst_slot,dst_port,fiber_a,fiber_b,notes
proj-001,rev-001,ses_068520420be33f56,utp_rj45,cab_94e2c52c9cbef746,17,utp_6xrj45,R01U2S1P4,R03U1S1P4,R01,front,2,1,4,R03,front,1,1,4,,,
proj-001,rev-001,ses_19814ea7921f293f,mpo12,cab_8c311bef72761e4c,16,mpo12_pass_through_12port,R01U1S1P10,R02U1S1P10,R01,front,1,1,10,R02,front,1,1,10,,,
```

---

### `bom.csv`

Bill of Materials summarising required physical hardware. Columns:

| Column        | Description |
|---------------|-------------|
| `item_type`   | Category: `panel`, `module`, or `cable`. |
| `description` | Item description including type variant. |
| `quantity`    | Total quantity required. |

Sample `bom.csv` for the above project:
```
item_type,description,quantity
panel,1U patch panel (4 slots/U),4
module,lc_breakout_2xmpo12_to_12xlcduplex,4
module,mpo12_pass_through_12port,4
module,utp_6xrj45,4
cable,mpo12_trunk mmf polarity-A,4
cable,mpo12_trunk polarity-B,14
cable,utp_cable,8
```

---

### `result.json`

Structured JSON with full allocation details. Top-level keys:

| Key            | Description |
|----------------|-------------|
| `project`      | Echo of the validated input project definition. |
| `input_hash`   | SHA-256 of the canonical input (for change detection). |
| `panels`       | List of 1U panels allocated across racks. |
| `modules`      | List of port modules inserted into panels. |
| `cables`       | List of physical trunk cables with type and polarity. |
| `sessions`     | List of port-to-port patch assignments (same data as `sessions.csv`). |
| `warnings`     | Non-fatal allocation warnings. |
| `errors`       | Fatal errors (e.g. rack overflow). |
| `metrics`      | Summary counts: `rack_count`, `panel_count`, `module_count`, `cable_count`, `session_count`. |
| `pair_details` | Per rack-pair slot usage details. |

Sample `result.json` metrics section:
```json
{
  "rack_count": 3,
  "panel_count": 4,
  "module_count": 12,
  "cable_count": 26,
  "session_count": 35
}
```
