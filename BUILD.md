# Local build notes

This tree was written on disk without cloning a git remote and without
pushing. Copy or push it later.

## Intended command (matches the README)

```bash
cd /workspace/vibelock
python -m pip install -e ".[dev]"
pytest -q
```

On this machine the system Python is PEP 668-externally-managed, so a
venv was used instead of installing into `/usr`:

```bash
python3 -m venv /workspace/vibelock/.venv
/workspace/vibelock/.venv/bin/pip install -U pip setuptools wheel
/workspace/vibelock/.venv/bin/pip install -e "/workspace/vibelock[dev]"
/workspace/vibelock/.venv/bin/pytest -q
```

## What ran (2026-08-28)

- Python 3.13.5
- numpy 2.5.2, scipy 1.18.1, pytest 9.1.1
- `pytest -q` → **31 passed**, no warnings
- `vibelock version` → `vibelock 0.1.0`
- `python examples/synthetic_pair.py` → dual-channel score on a synthetic
  pair, reason codes none

`.venv/` is gitignored. Tests do not require hardware.
