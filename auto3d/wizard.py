"""Interactive "do it for me" wrapper for the Auto3D pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auto3d.run import DEFAULT_OUTPUTS, DEFAULT_WORKSPACE, HERO_NAME, run_pipeline

CONFIG_DEFAULT_PATH = Path.home() / ".auto3d_do_it_for_me.json"


@dataclass
class RunnerState:
    workspace: Path = DEFAULT_WORKSPACE
    hero: Path | None = None
    hero_name: str = HERO_NAME
    triposr_command: str | None = None
    triposr_cwd: Path | None = None
    skip_triposr: bool = False
    skip_slicer: bool = False
    slicer_config: Path | None = None
    python: Path | None = None
    force: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunnerState":
        def _maybe_path(value: str | None) -> Path | None:
            return Path(value) if value else None

        return cls(
            workspace=Path(data.get("workspace", DEFAULT_WORKSPACE)),
            hero=_maybe_path(data.get("hero")),
            hero_name=data.get("hero_name", HERO_NAME),
            triposr_command=data.get("triposr_command"),
            triposr_cwd=_maybe_path(data.get("triposr_cwd")),
            skip_triposr=bool(data.get("skip_triposr", False)),
            skip_slicer=bool(data.get("skip_slicer", False)),
            slicer_config=_maybe_path(data.get("slicer_config")),
            python=_maybe_path(data.get("python")),
            force=bool(data.get("force", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        def _serialize(path: Path | None) -> str | None:
            return str(path) if path else None

        return {
            "workspace": str(self.workspace),
            "hero": _serialize(self.hero),
            "hero_name": self.hero_name,
            "triposr_command": self.triposr_command,
            "triposr_cwd": _serialize(self.triposr_cwd),
            "skip_triposr": self.skip_triposr,
            "skip_slicer": self.skip_slicer,
            "slicer_config": _serialize(self.slicer_config),
            "python": _serialize(self.python),
            "force": self.force,
        }


def load_state(path: Path) -> RunnerState | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:  # noqa: BLE001
        print(f"[config] Ignoring invalid config at {path}: {exc}")
        return None
    return RunnerState.from_dict(data)


def save_state(path: Path, state: RunnerState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state.to_dict(), handle, indent=2)
    print(f"[config] Saved defaults to {path}")


def yes_no(prompt: str, *, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{suffix}]: ").strip().lower()
        if not response:
            return default
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Please answer yes or no (y/n).")


def prompt_path(prompt: str, default: Path | None) -> Path | None:
    suffix = f" [{default}]" if default else ""
    response = input(f"{prompt}{suffix}: ").strip()
    if not response:
        return default
    expanded = Path(response).expanduser()
    return expanded


def prompt_text(prompt: str, default: str | None) -> str | None:
    suffix = f" [{default}]" if default else ""
    response = input(f"{prompt}{suffix}: ").strip()
    if not response:
        return default
    return response


def gather_state(existing: RunnerState | None) -> RunnerState:
    state = existing or RunnerState()

    print('\n=== Auto3D "Do it for me" wizard ===')
    print("Press Enter to accept the value in brackets.")

    workspace = prompt_path("Where should we create or reuse the workspace?", state.workspace)
    hero = prompt_path("Hero image path (leave blank to skip)", state.hero)
    hero_name = prompt_text("Save the hero image as (base filename)", state.hero_name)
    triposr_command = prompt_text(
        "TripoSR command template (use {input}/{output}, leave blank to skip)",
        state.triposr_command,
    )
    triposr_cwd = prompt_path("Working directory for TripoSR (optional)", state.triposr_cwd)

    skip_triposr = not yes_no(
        "Run TripoSR now? (answer No if you only want setup)",
        default=not state.skip_triposr,
    )
    skip_slicer = not yes_no("Run the floor slicer after mesh generation?", default=not state.skip_slicer)

    slicer_config = prompt_path(
        "Custom floors.yaml (blank uses the workspace default)",
        state.slicer_config,
    )
    python = prompt_path(
        "Python interpreter for the slicer (blank uses the current one)",
        state.python,
    )

    force = yes_no(
        "Overwrite template files if they already exist?",
        default=state.force,
    )

    return RunnerState(
        workspace=workspace or state.workspace,
        hero=hero,
        hero_name=hero_name or HERO_NAME,
        triposr_command=triposr_command,
        triposr_cwd=triposr_cwd,
        skip_triposr=skip_triposr,
        skip_slicer=skip_slicer,
        slicer_config=slicer_config,
        python=python,
        force=force,
    )


def run_with_state(state: RunnerState) -> None:
    print("\n[plan] Workspace:", state.workspace)
    if state.hero:
        print("[plan] Hero image:", state.hero)
    else:
        print("[plan] Hero image: use existing file in input_images/")
    if state.triposr_command:
        print("[plan] TripoSR command:", state.triposr_command)
    else:
        print("[plan] TripoSR command: skipped")
    print("[plan] Floor slicing:", "enabled" if not state.skip_slicer else "skipped")
    print("[plan] Outputs folder:", state.workspace / DEFAULT_OUTPUTS)

    run_pipeline(
        workspace=state.workspace,
        force=state.force,
        hero=state.hero,
        hero_name=state.hero_name,
        triposr_command=state.triposr_command,
        triposr_cwd=state.triposr_cwd,
        skip_triposr=state.skip_triposr,
        skip_slicer=state.skip_slicer,
        slicer_config=state.slicer_config,
        python=state.python,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Guide users through the Auto3D pipeline with interactive prompts and optional saved defaults."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_DEFAULT_PATH,
        help=f"Path to the JSON file storing defaults (default: {CONFIG_DEFAULT_PATH})",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run without prompts using the saved defaults.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Ignore any saved defaults and prompt for everything.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = args.config.expanduser()

    existing = None if args.reset else load_state(config_path)
    if args.auto:
        if not existing:
            raise SystemExit("No saved defaults found. Run without --auto first.")
        state = existing
    else:
        state = gather_state(existing)

    run_with_state(state)

    if not args.auto and yes_no("Remember these answers for next time?", default=True):
        save_state(config_path, state)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:  # noqa: PIE786
        sys.exit("\nAborted by user.")
