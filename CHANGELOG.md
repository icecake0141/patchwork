# Changelog

## Unreleased

- Improve input schema validation with stricter dataclass-based checks.
- Add validation-focused tests for duplicate racks, unknown endpoint types, and self-loop demands.
- Align project metadata and docs with Python 3.10+ support and current validation behavior.
- Add `.github/pull_request_template.md` to prevent placeholder PR bodies and enforce review checklist.
- Add Apache-2.0 + LLM attribution headers to HTML templates.
- Add initial Flask + SQLite scaffold for rack-to-rack patch cabling assistant.
- Implement deterministic allocation engine for MPO/LC/UTP with exports and diff.
