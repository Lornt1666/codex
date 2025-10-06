"""Entry point for ``python -m auto3d``."""
from __future__ import annotations

from .cli import main


if __name__ == "__main__":  # pragma: no cover - module CLI
    raise SystemExit(main())
