"""Wrapper around :mod:`auto3d.run` for backwards compatibility."""
from __future__ import annotations

from auto3d.run import main


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    raise SystemExit(main())
