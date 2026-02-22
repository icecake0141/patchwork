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

UI pages:
- Upload
- Trial
- Project detail
- Diff (logical + physical tabs)
