"""Convenience wrapper around the ``python -m auto3d`` entry point."""
from __future__ import annotations

from auto3d.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
