# Overview

This implementation follows the v0 design spec for rack-to-rack cabling allocation:

- Supported media: MMF/SMF LC duplex, MPO12, UTP RJ45.
- Slot category priority: MPO E2E → LC MMF → LC SMF → UTP.
- Mixed-in-U allocation is enabled by contiguous slot reservation.
- Deterministic IDs use SHA-256 canonical strings.
- Saved revisions persist generated `panel/module/cable/session` rows in SQLite.

## Settings: `ordering.peer_sort`

The `ordering.peer_sort` setting controls how rack-peer pairs are ordered during
allocation. The value is read from the project YAML under `settings.ordering.peer_sort`.

Supported values:

| Value | Behaviour |
|---|---|
| `natural_trailing_digits` (default) | Sorts rack IDs by the trailing numeric suffix first (numeric order), then by the full string. `R2` sorts before `R10`. |
| `lexicographic` | Sorts rack IDs as plain strings. `R10` sorts before `R2` because `"1" < "2"`. |

Any other value is rejected at validation time with a clear error message.

**Example** (project YAML):

```yaml
settings:
  ordering:
    peer_sort: lexicographic
```

## Settings: `panel.u_label_mode`

The `panel.u_label_mode` setting controls how U numbers are displayed in the Rack Panel
Occupancy UI. This affects display labels only; allocation behavior is controlled by
`settings.panel.allocation_direction`.

Supported values:

| Value | Behaviour |
|---|---|
| `ascending` (default) | Shows U labels as `U1`, `U2`, `U3`, ... from top to bottom. |
| `descending` | Shows U labels as `Umax`, `Umax-1`, ... from top to bottom (for example `U42`, `U41`, ... on a 42U rack). |

**Example** (project YAML):

```yaml
settings:
  panel:
    u_label_mode: descending
```

UI pages:
- Upload
- Trial
- Project detail
- Diff (logical + physical tabs)
