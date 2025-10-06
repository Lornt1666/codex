"""Wrapper around :mod:`auto3d.prompt` for backwards compatibility."""
from __future__ import annotations

from auto3d.prompt import main


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    raise SystemExit(main())
