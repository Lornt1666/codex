"""Run the Auto3D regression suite from the scripts folder."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from auto3d.app import Auto3DApplication

DEFAULT_WORKSPACE = Path("Auto3D-Render-to-STL")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run compileall and the targeted Auto3D unittest modules",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help="Workspace directory (default: Auto3D-Render-to-STL)",
    )
    parser.add_argument(
        "--skip-compile",
        action="store_true",
        help="Skip the compileall sanity check",
    )
    parser.add_argument(
        "--module",
        action="append",
        dest="modules",
        help="Specific unittest module to run (repeat for multiple modules)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    app = Auto3DApplication(workspace=args.workspace)
    app.run_tests(run_compileall=not args.skip_compile, modules=args.modules)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
