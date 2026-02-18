# Overview

This implementation follows the v0 design spec for rack-to-rack cabling allocation:

- Supported media: MMF/SMF LC duplex, MPO12, UTP RJ45.
- Slot category priority: MPO E2E → LC MMF → LC SMF → UTP.
- Mixed-in-U allocation is enabled by contiguous slot reservation.
- Deterministic IDs use SHA-256 canonical strings.
- Saved revisions persist generated `panel/module/cable/session` rows in SQLite.

UI pages:
- Upload
- Trial
- Project detail
- Diff (logical + physical tabs)
