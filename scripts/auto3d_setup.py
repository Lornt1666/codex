"""Wrapper around :mod:`auto3d.setup` for backwards compatibility."""
from __future__ import annotations

from auto3d.setup import main


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    raise SystemExit(main())
