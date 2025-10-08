"""Turnkey runner that orchestrates the Auto3D Render-to-STL pipeline."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from auto3d.printability import evaluate_printability, write_printability_report
from auto3d.setup import create_project


DEFAULT_WORKSPACE = Path("Auto3D-Render-to-STL")
HERO_NAME = "hero"
DEFAULT_MESH = Path("working/house_mesh.obj")
DEFAULT_CONFIG = Path("configs/floors.yaml")
DEFAULT_OUTPUTS = Path("outputs")


class CommandError(RuntimeError):
    """Raised when a subprocess exits with a non-zero status."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the Auto3D workspace, copy your hero image, optionally run "
            "TripoSR, and slice floors in a single command."
        )
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=DEFAULT_WORKSPACE,
        help="Target directory for the Auto3D workspace (default: Auto3D-Render-to-STL)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite scaffolded files if they already exist",
    )
    parser.add_argument(
        "--hero",
        type=Path,
        help="Path to the hero render to copy into input_images/",
    )
    parser.add_argument(
        "--hero-name",
        default=HERO_NAME,
        help="Base filename (without extension) for the copied hero render (default: hero)",
    )
    parser.add_argument(
        "--triposr-command",
        help=(
            "Optional command template that generates the mesh. Use {input} and {output} "
            "placeholders for the hero image and output mesh paths."
        ),
    )
    parser.add_argument(
        "--triposr-cwd",
        type=Path,
        help="Optional working directory when running the TripoSR command",
    )
    parser.add_argument(
        "--skip-triposr",
        action="store_true",
        help="Skip running the TripoSR command even if provided",
    )
    parser.add_argument(
        "--skip-slicer",
        action="store_true",
        help="Skip running the floor slicer",
    )
    parser.add_argument(
        "--slicer-config",
        type=Path,
        help="Custom floors.yaml path. Defaults to the scaffolded configs/floors.yaml",
    )
    parser.add_argument(
        "--python",
        type=Path,
        default=Path(sys.executable),
        help="Python interpreter to use when running slicer scripts (default: current interpreter)",
    )
    return parser.parse_args()


def scaffold_workspace(base: Path, *, force: bool) -> None:
    base = base.expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    print(f"[workspace] {base}")
    create_project(base, force=force)


def copy_hero(source: Path, target_dir: Path, hero_name: str) -> Path:
    if not source.exists():
        msg = f"Hero image not found: {source}"
        raise FileNotFoundError(msg)
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / f"{hero_name}{source.suffix.lower()}"
    shutil.copy2(source, destination)
    print(f"[hero] Copied {source} -> {destination}")
    return destination


def find_existing_hero(directory: Path, hero_name: str) -> Path | None:
    for extension in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
        candidate = directory / f"{hero_name}{extension}"
        if candidate.exists():
            return candidate
    return None


def run_command(command: Sequence[str], *, cwd: Path | None = None) -> None:
    display = " ".join(command)
    print(f"[cmd] {display}")
    try:
        subprocess.run(command, cwd=cwd, check=True)
    except subprocess.CalledProcessError as exc:  # noqa: BLE001
        raise CommandError(f"Command failed with exit code {exc.returncode}: {display}") from exc


def maybe_run_triposr(
    *,
    command_template: str | None,
    cwd: Path | None,
    hero_path: Path,
    mesh_path: Path,
    skip: bool,
) -> None:
    if skip:
        print("[triposr] Skipped (per flag)")
        return
    if not command_template:
        print("[triposr] No command provided; skipping mesh generation")
        return
    if not hero_path.exists():
        print(f"[triposr] Hero image missing ({hero_path}); skipping mesh generation")
        return

    formatted = command_template.format(input=str(hero_path), output=str(mesh_path))
    command = split_shell(formatted)
    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(command, cwd=cwd)


def split_shell(value: str) -> list[str]:
    import shlex

    return shlex.split(value)


def ensure_mesh_exists(mesh_path: Path) -> bool:
    if mesh_path.exists():
        print(f"[mesh] Found {mesh_path}")
        return True
    print(f"[mesh] Missing {mesh_path}")
    return False


def run_slicer(
    *,
    workspace: Path,
    python: Path,
    mesh: Path,
    config: Path,
    outdir: Path,
) -> None:
    slicer = workspace / "scripts" / "2_slice_mesh_to_floors.py"
    if not slicer.exists():
        msg = f"Slicer script missing: {slicer}"
        raise FileNotFoundError(msg)

    command: list[str] = [
        str(python),
        str(slicer),
        "--mesh",
        str(mesh),
        "--config",
        str(config),
        "--outdir",
        str(outdir),
    ]
    outdir.mkdir(parents=True, exist_ok=True)
    run_command(command)


def run_pipeline(
    *,
    workspace: Path,
    force: bool = False,
    hero: Path | None = None,
    hero_name: str = HERO_NAME,
    triposr_command: str | None = None,
    triposr_cwd: Path | None = None,
    skip_triposr: bool = False,
    skip_slicer: bool = False,
    slicer_config: Path | None = None,
    python: Path | None = None,
) -> None:
    """Execute the Auto3D pipeline programmatically."""

    resolved_workspace = workspace.expanduser()
    scaffold_workspace(resolved_workspace, force=force)

    hero_directory = resolved_workspace / "input_images"
    if hero:
        hero_path = copy_hero(hero.expanduser(), hero_directory, hero_name)
    else:
        existing = find_existing_hero(hero_directory, hero_name)
        if existing:
            hero_path = existing
            print(f"[hero] Using existing {hero_path}")
        else:
            hero_path = hero_directory / f"{hero_name}.png"
            print("[hero] No image provided; place your render in input_images/ manually")

    mesh_path = resolved_workspace / DEFAULT_MESH
    maybe_run_triposr(
        command_template=triposr_command,
        cwd=triposr_cwd.expanduser() if triposr_cwd else None,
        hero_path=hero_path,
        mesh_path=mesh_path,
        skip=skip_triposr,
    )

    if skip_slicer:
        print("[slicer] Skipped (per flag)")
        return

    if not ensure_mesh_exists(mesh_path):
        print("[slicer] Mesh missing; skipping floor slicing")
        return

    if slicer_config:
        config_path = slicer_config.expanduser()
    else:
        config_path = resolved_workspace / DEFAULT_CONFIG
    if not config_path.exists():
        msg = f"Slicer config not found: {config_path}"
        raise FileNotFoundError(msg)

    outputs = resolved_workspace / DEFAULT_OUTPUTS
    run_slicer(
        workspace=resolved_workspace,
        python=(python or Path(sys.executable)).expanduser(),
        mesh=mesh_path,
        config=config_path,
        outdir=outputs,
    )
    stl_paths = sorted(outputs.glob("*.stl"))
    if stl_paths:
        printability = evaluate_printability(stl_paths)
        write_printability_report(outputs, printability)
        if not printability.success:
            errors = [issue.message for issue in printability.issues if issue.level == "error"]
            raise RuntimeError(
                "Printability gate failed:\n" + "\n".join(f"- {message}" for message in errors)
            )
    else:
        print("[printability] No STL files produced; skipping gate.")
    print("[done] Floor slicing complete. STLs are in the outputs/ folder.")


def main() -> None:
    args = parse_args()

    run_pipeline(
        workspace=args.workspace,
        force=args.force,
        hero=args.hero,
        hero_name=args.hero_name,
        triposr_command=args.triposr_command,
        triposr_cwd=args.triposr_cwd,
        skip_triposr=args.skip_triposr,
        skip_slicer=args.skip_slicer,
        slicer_config=args.slicer_config,
        python=args.python,
    )


if __name__ == "__main__":
    main()
