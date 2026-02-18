# Architecture Overview

- `app.py`: Flask routes and persistence wiring.
- `models.py`: input schema and validation.
- `services/allocator.py`: deterministic allocation engine.
- `services/render_svg.py`: SVG renderers for topology/rack/pair views.
- `services/export.py`: `result.json` and session CSV exports.
- `db.py`: SQLite schema bootstrap.
