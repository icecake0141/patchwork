# Architecture Overview

- `app.py`: Flask routes and persistence wiring.
- `models.py`: YAML validation using dataclass-based checks.
- `services/allocator.py`: deterministic allocation engine.
- `services/render_svg.py`: simple SVG text renderers.
- `services/export.py`: result JSON and session CSV exporters.
- `db.py`: SQLite schema bootstrap.
