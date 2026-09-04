"""Allow ``python -m mialock``."""

from mialock.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
