# Changelog

## Unreleased

- Improve input schema validation with stricter dataclass-based checks.
- Add validation-focused tests for duplicate racks, unknown endpoint types, and self-loop demands.
- Align project metadata and docs with Python 3.10+ support and current validation behavior.
- Add initial Flask + SQLite scaffold for rack-to-rack patch cabling assistant.
- Implement deterministic allocation engine for MPO/LC/UTP with exports and diff.
