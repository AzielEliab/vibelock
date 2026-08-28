"""Allow ``python -m vibelock`` to invoke the CLI."""

from vibelock.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
