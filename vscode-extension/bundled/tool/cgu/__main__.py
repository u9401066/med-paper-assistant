"""`python -m cgu ...` runs the same command line as the `cgu` script."""

from __future__ import annotations

from cgu.interfaces.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
