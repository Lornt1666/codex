"""Application-level orchestration helpers for Auto3D."""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from auto3d.capabilities import (
    AICapability,
    capability_catalog,
    recommended_capabilities,
)
from auto3d.automation import (
    PlaywrightScriptConfig,
    automation_guidelines as _automation_guidelines,
    write_playwright_script,
)
from auto3d.supercompute import (
    SupercomputeReadiness,
    evaluate_supercompute,
)
from auto3d.regulations import (
    BuildingCodeReference,
    building_code_catalog as _building_code_catalog,
    filter_building_codes,
)
from auto3d.site import render_site
from auto3d.prompt import (
    DEFAULT_MODEL_SCALE,
    DEFAULT_PROTOCOL,
    ModelDimensions,
    PromptConfig,
    convert_to_model_dims,
    copy_hero as copy_prompt_hero,
    ensure_workspace,
    estimate_geometry,
    extract_prompt_config,
    generate_assembled_stl,
    generate_catalog,
    generate_floor_stls,
    generate_roof_stl,
    default_catalog_variants,
    write_report,
)
from auto3d.printability import (
    PrintabilityResult,
    evaluate_printability,
    write_printability_report,
)
from auto3d.run import run_pipeline as run_pipeline_command
from auto3d.setup import create_project
from auto3d.wizard import (
    CONFIG_DEFAULT_PATH,
    RunnerState,
    gather_state,
    load_state,
    run_with_state,
    save_state,
)


DEFAULT_TEST_MODULES: tuple[str, ...] = (
    "tests.test_auto3d_prompt_to_stl",
    "tests.test_auto3d_capabilities",
    "tests.test_auto3d_site",
    "tests.test_auto3d_cli",
    "tests.test_auto3d_automation",
    "tests.test_auto3d_supercompute",
    "tests.test_auto3d_printability",
)


COMPILE_TARGETS: tuple[str, ...] = (
    "auto3d",
    "auto3d/prompt.py",
    "auto3d/run.py",
    "auto3d/wizard.py",
    "auto3d/setup.py",
    "auto3d/script_cli.py",
    "auto3d/tester.py",
    "scripts/auto3d_prompt_to_stl.py",
    "scripts/auto3d_run.py",
    "scripts/auto3d_do_it_for_me.py",
    "scripts/auto3d_setup.py",
    "scripts/auto3d_cli.py",
    "scripts/auto3d_test.py",
)


CommandExecutor = Callable[[Sequence[str], Path], None]


@dataclass
class SupercomputeApplicationSummary:
    """Aggregate view of the supercomputing blueprint readiness."""

    readiness: SupercomputeReadiness
    available_capabilities: tuple[AICapability, ...]
    missing_capabilities: tuple[AICapability, ...]
    unknown_capabilities: tuple[str, ...]


@dataclass
class Auto3DApplication:
    """High-level façade that coordinates the Auto3D helpers."""

    workspace: Path = Path("Auto3D-Render-to-STL")

    # ------------------------------------------------------------------
    # Workspace scaffolding
    def create_workspace(self, *, force: bool = False) -> None:
        """Ensure that the scaffolded workspace exists."""

        base = self.workspace.expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        create_project(base, force=force)

    # ------------------------------------------------------------------
    # Pipeline execution (TripoSR → slicer)
    def run_pipeline(
        self,
        *,
        hero: Path | None = None,
        hero_name: str = "hero",
        triposr_command: str | None = None,
        triposr_cwd: Path | None = None,
        skip_triposr: bool = False,
        skip_slicer: bool = False,
        slicer_config: Path | None = None,
        python: Path | None = None,
        force: bool = False,
    ) -> None:
        """Invoke the existing turnkey pipeline with minimal ceremony."""

        run_pipeline_command(
            workspace=self.workspace,
            force=force,
            hero=hero,
            hero_name=hero_name,
            triposr_command=triposr_command,
            triposr_cwd=triposr_cwd,
            skip_triposr=skip_triposr,
            skip_slicer=skip_slicer,
            slicer_config=slicer_config,
            python=python,
        )

    # ------------------------------------------------------------------
    # Prompt-driven STL generation
    def prompt_to_stl(
        self,
        prompt: str,
        *,
        hero: Path | None = None,
        model_scale: float = DEFAULT_MODEL_SCALE,
        include_roof: bool = True,
        force: bool = False,
        protocol: str = DEFAULT_PROTOCOL,
    ) -> dict[str, Path]:
        """Produce STL files and a report directly from a descriptive prompt."""

        workspace = self.workspace.expanduser().resolve()
        ensure_workspace(workspace, force=force)
        copy_prompt_hero(hero, workspace)

        config = extract_prompt_config(prompt)
        geometry = estimate_geometry(config)
        model_dims = convert_to_model_dims(geometry, scale=model_scale)

        outputs: dict[str, Path] = {}
        for path in generate_floor_stls(workspace, geometry, model_dims):
            outputs[path.name] = path
        if include_roof:
            roof = generate_roof_stl(workspace, geometry, model_dims)
            outputs[roof.name] = roof
        assembled = generate_assembled_stl(
            workspace,
            geometry,
            model_dims,
            include_roof=include_roof,
        )
        outputs[assembled.name] = assembled

        stl_paths = [path for path in outputs.values() if path.suffix.lower() == ".stl"]
        printability = evaluate_printability(stl_paths)
        printability_report = write_printability_report(workspace / "outputs", printability)
        outputs[printability_report.name] = printability_report

        report = write_report(
            workspace,
            prompt=prompt,
            config=config,
            geometry=geometry,
            model=model_dims,
            protocol=protocol,
            scale=model_scale,
            printability=printability,
        )
        outputs[report.name] = report
        if not printability.success:
            errors = [issue.message for issue in printability.issues if issue.level == "error"]
            raise RuntimeError(
                "Printability gate failed:\n" + "\n".join(f"- {message}" for message in errors)
            )
        return outputs

    def prompt_catalog(
        self,
        prompt: str,
        *,
        hero: Path | None = None,
        model_scale: float = DEFAULT_MODEL_SCALE,
        include_roof: bool = True,
        force: bool = False,
        protocol: str = DEFAULT_PROTOCOL,
        limit: int | None = None,
    ) -> dict[str, list[Path]]:
        """Generate a catalog of variant STL stacks from a single descriptive prompt."""

        config = extract_prompt_config(prompt)
        base_geometry = estimate_geometry(config)
        variants = default_catalog_variants(config, base_geometry)
        if limit is not None:
            variants = variants[:limit]

        return generate_catalog(
            self.workspace,
            prompt,
            model_scale=model_scale,
            include_roof=include_roof,
            protocol=protocol,
            force=force,
            hero=hero,
            variants=variants,
        )

    # ------------------------------------------------------------------
    # Printability evaluation
    def assess_printability(
        self,
        stl_paths: Sequence[Path] | None = None,
        *,
        report_dir: Path | None = None,
        write_report: bool = True,
        report_name: str = "printability.md",
    ) -> tuple[PrintabilityResult, Path | None]:
        """Evaluate existing STL files and optionally write a printability report."""

        workspace = self.workspace.expanduser().resolve()

        resolved_paths: list[Path] = []
        if stl_paths:
            for raw_path in stl_paths:
                candidate = raw_path.expanduser()
                if not candidate.is_absolute():
                    candidate = (workspace / candidate).resolve()
                else:
                    candidate = candidate.resolve()
                if not candidate.exists():
                    raise FileNotFoundError(f"STL not found: {candidate}")
                resolved_paths.append(candidate)
        else:
            outputs_dir = workspace / "outputs"
            resolved_paths = sorted(
                path for path in outputs_dir.glob("*.stl") if path.is_file()
            )
            if not resolved_paths:
                raise FileNotFoundError(
                    "No STL files found in outputs/. Provide --stl to specify files explicitly."
                )

        result = evaluate_printability(resolved_paths)
        report_path: Path | None = None
        if write_report:
            destination = report_dir.expanduser() if report_dir else workspace / "outputs"
            if not destination.is_absolute():
                destination = (workspace / destination).resolve()
            report_path = write_printability_report(destination, result, name=report_name)

        return result, report_path

    # ------------------------------------------------------------------
    # Supercomputing blueprint readiness
    def supercompute_blueprint(
        self,
        *,
        available_capabilities: Sequence[str] | None = None,
        protocol: str = DEFAULT_PROTOCOL,
    ) -> SupercomputeApplicationSummary:
        """Return readiness information for the artificial supercomputing blueprint."""

        readiness = evaluate_supercompute(
            available_capabilities=available_capabilities or (),
            protocol=protocol,
        )
        catalog = {cap.key: cap for cap in capability_catalog()}

        available_objs = tuple(
            catalog[key]
            for key in readiness.available_capabilities
            if key in catalog
        )
        missing_objs = tuple(
            catalog[key]
            for key in readiness.missing_capabilities
            if key in catalog
        )
        unknown = tuple(
            key for key in readiness.available_capabilities if key not in catalog
        )

        return SupercomputeApplicationSummary(
            readiness=readiness,
            available_capabilities=available_objs,
            missing_capabilities=missing_objs,
            unknown_capabilities=unknown,
        )

    # ------------------------------------------------------------------
    # Static site generation
    def build_site(
        self,
        *,
        output: Path | None = None,
        include_bundle: bool = True,
        protocol: str = DEFAULT_PROTOCOL,
        force: bool = False,
    ) -> dict[str, Path]:
        """Generate a static marketing site that surfaces the Auto3D workflow."""

        site_dir = (output or (self.workspace / "site")).expanduser().resolve()
        summary = self.supercompute_blueprint(protocol=protocol)
        return render_site(
            site_dir,
            capabilities=capability_catalog(),
            supercompute_readiness=summary.readiness,
            supercompute_available=summary.available_capabilities,
            supercompute_missing=summary.missing_capabilities,
            protocol=protocol,
            force=force,
            include_bundle=include_bundle,
        )

    # ------------------------------------------------------------------
    # Playwright automation helpers
    def create_playwright_script(
        self,
        *,
        url: str,
        output: Path | None = None,
        upload_path: Path | None = None,
        upload_selector: str = "input[type=file]",
        start_selectors: Sequence[str] | None = None,
        extra_clicks: Sequence[str] | None = None,
        submit_selector: str | None = None,
        wait_for_network_idle: bool = True,
        wait_time_ms: int = 5000,
        headless: bool = False,
        notes: Sequence[str] | None = None,
    ) -> Path:
        """Generate a Playwright automation script for STL uploads."""

        workspace = self.workspace.expanduser().resolve()
        target = (output or (workspace / "automation" / "auto3d_playwright_upload.py")).expanduser().resolve()

        upload = (upload_path or (workspace / "outputs" / "assembled.stl")).expanduser().resolve()
        config = PlaywrightScriptConfig(
            url=url,
            upload_path=upload,
            upload_selector=upload_selector,
            start_selectors=tuple(start_selectors or ()),
            extra_clicks=tuple(extra_clicks or ()),
            submit_selector=submit_selector,
            wait_for_network_idle=wait_for_network_idle,
            wait_time_ms=wait_time_ms,
            headless=headless,
            notes=tuple(notes or ()),
        )
        return write_playwright_script(target, config)

    @staticmethod
    def automation_guidelines() -> Sequence[str]:
        """Return guidance for operating generated automation scripts."""

        return list(_automation_guidelines())

    # ------------------------------------------------------------------
    # Building code references
    def building_codes(
        self,
        *,
        regions: Sequence[str] | None = None,
        keywords: Sequence[str] | None = None,
        scales: Sequence[str] | None = None,
    ) -> list[BuildingCodeReference]:
        """Return building code references filtered by region/scale/keywords."""

        return filter_building_codes(regions=regions, keywords=keywords, scales=scales)

    @staticmethod
    def building_code_catalog() -> list[BuildingCodeReference]:
        """Return the full building code catalog."""

        return list(_building_code_catalog())

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Wizard automation
    def run_wizard(
        self,
        *,
        config_path: Path | None = None,
        auto: bool = False,
        reset: bool = False,
        remember: bool = True,
    ) -> RunnerState:
        """Run the interactive wizard (or its unattended variant)."""

        store = (config_path or CONFIG_DEFAULT_PATH).expanduser()
        existing = None if reset else load_state(store)

        if auto:
            if not existing:
                raise RuntimeError("No stored defaults available; run interactively first.")
            state = existing
        else:
            state = gather_state(existing)

        run_with_state(state)

        if not auto and remember:
            save_state(store, state)
        return state

    # ------------------------------------------------------------------
    # Convenience helpers for external tooling
    @staticmethod
    def describe_prompt(prompt: str) -> tuple[PromptConfig, ModelDimensions]:
        """Return the parsed config and scaled dimensions for inspection."""

        config = extract_prompt_config(prompt)
        geometry = estimate_geometry(config)
        model_dims = convert_to_model_dims(geometry, scale=DEFAULT_MODEL_SCALE)
        return config, model_dims

    @staticmethod
    def list_outputs(paths: Iterable[Path]) -> Sequence[str]:  # pragma: no cover - trivial
        return [str(path) for path in paths]

    # ------------------------------------------------------------------
    # AI capability catalog helpers
    def ai_capabilities(
        self,
        *,
        style_tags: Sequence[str] | None = None,
        floors_above: int | None = None,
        has_basement: bool | None = None,
        include_catalog_overview: bool = True,
    ) -> list[AICapability]:
        """Return recommended AI capabilities (or the full catalog)."""

        if style_tags is None and floors_above is None and has_basement is None:
            return capability_catalog()

        return recommended_capabilities(
            style_tags=style_tags or [],
            floors=floors_above,
            has_basement=has_basement,
            include_catalog_overview=include_catalog_overview,
        )

    # ------------------------------------------------------------------
    # Quality gates
    def run_tests(
        self,
        *,
        run_compileall: bool = True,
        modules: Sequence[str] | None = None,
        executor: CommandExecutor | None = None,
    ) -> list[tuple[str, ...]]:
        """Execute the Auto3D regression suite (compileall + unittest)."""

        project_root = Path(__file__).resolve().parent.parent
        commands: list[list[str]] = []

        if run_compileall:
            commands.append(
                [
                    sys.executable,
                    "-m",
                    "compileall",
                    *COMPILE_TARGETS,
                ]
            )

        test_modules = list(modules or DEFAULT_TEST_MODULES)
        if test_modules:
            commands.append([sys.executable, "-m", "unittest", *test_modules])

        exec_command = executor or self._default_executor
        executed: list[tuple[str, ...]] = []
        for command in commands:
            exec_command(command, project_root)
            executed.append(tuple(command))
        return executed

    @staticmethod
    def _default_executor(command: Sequence[str], cwd: Path) -> None:
        """Run a subprocess command, raising if it fails."""

        subprocess.run(command, cwd=cwd, check=True)
