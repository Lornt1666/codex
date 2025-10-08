"""Command-line interface entrypoints for the Auto3D package."""
from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from typing import Sequence

from .app import Auto3DApplication
from .commands import Command, command_registry
from .printability import render_printability_markdown


def _register_defaults() -> None:
    if "setup" in command_registry:
        return

    command_registry.register(
        Command(
            name="setup",
            help="Create the Auto3D workspace structure",
            configure=lambda parser: parser.add_argument("--force", action="store_true", help="Overwrite existing files"),
            handler=lambda app, args: app.create_workspace(force=args.force),
        )
    )

    def configure_pipeline(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--hero", type=Path, help="Hero render to place into input_images/")
        parser.add_argument("--hero-name", default="hero", help="Basename for the hero render inside the workspace")
        parser.add_argument(
            "--triposr-command",
            help="Command template for TripoSR (use {input} and {output} placeholders)",
        )
        parser.add_argument("--triposr-cwd", type=Path, help="Working directory when running TripoSR")
        parser.add_argument("--skip-triposr", action="store_true", help="Skip running TripoSR")
        parser.add_argument("--skip-slicer", action="store_true", help="Skip running the slicer")
        parser.add_argument("--slicer-config", type=Path, help="Custom floors.yaml path")
        parser.add_argument("--python", type=Path, help="Python interpreter for running scripts")
        parser.add_argument("--force", action="store_true", help="Overwrite template files if needed")

    def handle_pipeline(app: Auto3DApplication, args: argparse.Namespace) -> None:
        app.run_pipeline(
            hero=args.hero,
            hero_name=args.hero_name,
            triposr_command=args.triposr_command,
            triposr_cwd=args.triposr_cwd,
            skip_triposr=args.skip_triposr,
            skip_slicer=args.skip_slicer,
            slicer_config=args.slicer_config,
            python=args.python,
            force=args.force,
        )

    command_registry.register(
        Command(
            name="pipeline",
            help="Execute the TripoSR → slicer pipeline",
            configure=configure_pipeline,
            handler=handle_pipeline,
        )
    )

    def configure_prompt(parser: argparse.ArgumentParser) -> None:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--prompt", help="Inline descriptive prompt")
        group.add_argument("--prompt-file", type=Path, help="File containing the descriptive prompt")
        parser.add_argument("--hero", type=Path, help="Hero render to copy for reference")
        parser.add_argument("--model-scale", type=float, default=100.0, help="Scale denominator (real:model)")
        parser.add_argument("--no-roof", action="store_true", help="Skip generating a roof STL")
        parser.add_argument("--protocol", default="1JGM∞.BE", help="Protocol identifier for the report")
        parser.add_argument("--force", action="store_true", help="Overwrite existing scaffolded files")

    def handle_prompt(app: Auto3DApplication, args: argparse.Namespace) -> None:
        if args.prompt:
            prompt_text = args.prompt
        else:
            prompt_path = args.prompt_file.expanduser()
            if not prompt_path.exists():
                raise SystemExit(f"Prompt file not found: {prompt_path}")
            prompt_text = prompt_path.read_text(encoding="utf-8")
        outputs = app.prompt_to_stl(
            prompt_text,
            hero=args.hero,
            model_scale=args.model_scale,
            include_roof=not args.no_roof,
            force=args.force,
            protocol=args.protocol,
        )
        for name, path in sorted(outputs.items()):
            print(f"[output] {name}: {path}")

    command_registry.register(
        Command(
            name="prompt",
            help="Generate STL assets directly from a descriptive prompt",
            configure=configure_prompt,
            handler=handle_prompt,
        )
    )

    def configure_catalog(parser: argparse.ArgumentParser) -> None:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--prompt", help="Inline descriptive prompt")
        group.add_argument("--prompt-file", type=Path, help="File containing the descriptive prompt")
        parser.add_argument("--hero", type=Path, help="Hero render to copy for reference")
        parser.add_argument("--model-scale", type=float, default=100.0, help="Scale denominator (real:model)")
        parser.add_argument("--no-roof", action="store_true", help="Skip generating roofs in the catalog")
        parser.add_argument("--protocol", default="1JGM∞.BE", help="Protocol identifier for the reports")
        parser.add_argument("--limit", type=int, help="Limit the number of catalog variants")
        parser.add_argument("--force", action="store_true", help="Overwrite existing scaffolded files")

    def handle_catalog(app: Auto3DApplication, args: argparse.Namespace) -> None:
        if args.prompt:
            prompt_text = args.prompt
        else:
            prompt_path = args.prompt_file.expanduser()
            if not prompt_path.exists():
                raise SystemExit(f"Prompt file not found: {prompt_path}")
            prompt_text = prompt_path.read_text(encoding="utf-8")

        outputs = app.prompt_catalog(
            prompt_text,
            hero=args.hero,
            model_scale=args.model_scale,
            include_roof=not args.no_roof,
            force=args.force,
            protocol=args.protocol,
            limit=args.limit,
        )
        for key, paths in sorted(outputs.items()):
            print(f"[variant] {key}")
            for path in sorted(paths):
                print(f"  - {path}")

    command_registry.register(
        Command(
            name="catalog",
            help="Generate a catalog of STL variants from a descriptive prompt",
            configure=configure_catalog,
            handler=handle_catalog,
        )
    )

    def configure_printability(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--stl",
            action="append",
            dest="stls",
            type=Path,
            help="STL file to evaluate (repeat to check multiple)",
        )
        parser.add_argument(
            "--report-dir",
            type=Path,
            help="Directory for the Markdown report (default: workspace/outputs)",
        )
        parser.add_argument(
            "--report-name",
            default="printability.md",
            help="Filename for the generated report",
        )
        parser.add_argument(
            "--no-report",
            action="store_true",
            help="Skip writing the Markdown report and only print the summary",
        )

    def handle_printability(app: Auto3DApplication, args: argparse.Namespace) -> None:
        try:
            result, report_path = app.assess_printability(
                stl_paths=args.stls,
                report_dir=args.report_dir,
                write_report=not args.no_report,
                report_name=args.report_name,
            )
        except FileNotFoundError as exc:
            raise SystemExit(str(exc)) from exc

        summary = render_printability_markdown(result, include_header=False).strip()
        if summary:
            print(summary)
        if report_path is not None:
            print(f"[printability] report: {report_path}")
        if not result.success:
            raise SystemExit(1)

    command_registry.register(
        Command(
            name="printability",
            help="Evaluate STL files against the printability gate",
            configure=configure_printability,
            handler=handle_printability,
        )
    )

    def configure_capabilities(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--style",
            action="append",
            dest="styles",
            help="Style tag to bias the recommendations (repeat for multiple tags)",
        )
        parser.add_argument("--floors", type=int, help="Number of floors above grade")
        parser.add_argument("--basement", action="store_true", help="Indicate a basement programme")
        parser.add_argument(
            "--catalog",
            action="store_true",
            help="Show the entire capability catalog instead of tailored suggestions",
        )
        parser.add_argument(
            "--format",
            choices=["table", "json"],
            default="table",
            help="Output format (default: table)",
        )
        parser.add_argument("--limit", type=int, help="Limit the number of capabilities shown")

    def handle_capabilities(app: Auto3DApplication, args: argparse.Namespace) -> None:
        if args.catalog or (args.floors is None and not args.styles and not args.basement):
            capabilities = app.ai_capabilities()
        else:
            capabilities = app.ai_capabilities(
                style_tags=args.styles or [],
                floors_above=args.floors,
                has_basement=args.basement,
            )
        if args.limit is not None:
            capabilities = capabilities[: args.limit]

        if args.format == "json":
            import json

            print(json.dumps([cap.to_dict() for cap in capabilities], indent=2))
            return

        for cap in capabilities:
            print(f"- {cap.label} [{cap.category}] ({cap.key})")
            print(f"  Description: {cap.description}")
            if cap.inputs:
                print(f"  Inputs: {', '.join(cap.inputs)}")
            if cap.outputs:
                print(f"  Outputs: {', '.join(cap.outputs)}")
            if cap.providers:
                print(f"  Providers: {', '.join(cap.providers)}")
            readiness = "Offline-ready" if cap.offline_ready else "Cloud or GPU required"
            print(f"  Availability: {readiness}")
            for note in cap.notes:
                print(f"  - {note}")

    command_registry.register(
        Command(
            name="capabilities",
            help="List AI capabilities relevant to the Auto3D pipeline",
            configure=configure_capabilities,
            handler=handle_capabilities,
        )
    )

    def configure_supercompute(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--capability",
            action="append",
            dest="capabilities",
            help="Capability key to mark as already integrated (repeat for multiple)",
        )
        parser.add_argument(
            "--protocol",
            default="1JGM∞.BE",
            help="Protocol identifier for the blueprint (default: 1JGM∞.BE)",
        )
        parser.add_argument(
            "--format",
            choices=["table", "json"],
            default="table",
            help="Output format for the readiness report",
        )

    def handle_supercompute(app: Auto3DApplication, args: argparse.Namespace) -> None:
        summary = app.supercompute_blueprint(
            available_capabilities=args.capabilities or [],
            protocol=args.protocol,
        )
        readiness = summary.readiness

        if args.format == "json":
            import json

            payload = {
                "readiness": readiness.to_dict(),
                "available_capabilities": [
                    {"key": cap.key, "label": cap.label} for cap in summary.available_capabilities
                ],
                "missing_capabilities": [
                    {"key": cap.key, "label": cap.label} for cap in summary.missing_capabilities
                ],
                "protocol": readiness.blueprint.protocol,
            }
            print(json.dumps(payload, indent=2))
            return

        print(f"Protocol: {readiness.blueprint.protocol}")
        print(f"Mission: {readiness.blueprint.mission}")
        print("\nLayers:")
        for layer in readiness.blueprint.layers:
            print(f"- {layer.label}: {layer.objective}")
            print(f"  AI stack: {', '.join(layer.ai_capabilities)}")
            print(f"  Infrastructure: {', '.join(layer.infrastructure)}")
            print(f"  Deliverables: {', '.join(layer.deliverables)}")

        if summary.available_capabilities:
            print("\nAvailable capabilities:")
            for cap in summary.available_capabilities:
                print(f"- {cap.label} ({cap.key})")
        else:
            print("\nAvailable capabilities: none declared yet.")

        if summary.missing_capabilities:
            print("\nMissing capabilities:")
            for cap in summary.missing_capabilities:
                print(f"- {cap.label} ({cap.key})")
        else:
            print("\nMissing capabilities: all requirements satisfied.")

        print("\nRecommended actions:")
        for action in readiness.recommended_actions:
            print(f"- {action}")

        print("\nNotes:")
        for note in readiness.notes:
            print(f"- {note}")

    command_registry.register(
        Command(
            name="supercompute",
            help="Summarise the artificial supercomputing blueprint and readiness",
            configure=configure_supercompute,
            handler=handle_supercompute,
        )
    )

    def configure_test(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--module",
            action="append",
            dest="modules",
            help="Specific unittest module to run (repeat for multiple modules)",
        )
        parser.add_argument(
            "--skip-compile",
            action="store_true",
            help="Skip the compileall sanity check",
        )

    def handle_test(app: Auto3DApplication, args: argparse.Namespace) -> None:
        results = app.run_tests(run_compileall=not args.skip_compile, modules=args.modules)
        for command in results:
            quoted = " ".join(shlex.quote(part) for part in command)
            print(f"[test] {quoted}")

    command_registry.register(
        Command(
            name="test",
            help="Run the Auto3D regression checks (compileall + targeted unittests)",
            configure=configure_test,
            handler=handle_test,
        )
    )

    def configure_web(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--output", type=Path, help="Directory where the static site will be written")
        parser.add_argument("--protocol", default="1JGM∞.BE", help="Protocol identifier to showcase")
        parser.add_argument("--no-bundle", action="store_true", help="Skip bundling the Auto3D download archive")
        parser.add_argument("--force", action="store_true", help="Overwrite the output directory if it exists")
        parser.add_argument("--serve", action="store_true", help="Start a preview server after generating the site")
        parser.add_argument("--host", default="127.0.0.1", help="Host interface for the preview server")
        parser.add_argument("--port", type=int, default=8000, help="Port for the preview server (use 0 for random)")
        parser.add_argument("--open-browser", action="store_true", help="Open the default browser when serving")

    def handle_web(app: Auto3DApplication, args: argparse.Namespace) -> None:
        outputs = app.build_site(
            output=args.output,
            include_bundle=not args.no_bundle,
            protocol=args.protocol,
            force=args.force,
        )
        for name, path in sorted(outputs.items()):
            print(f"[site] {name}: {path}")

        if args.serve:
            import webbrowser

            from .site import start_site_server

            site_root = outputs["index"].parent
            server = start_site_server(site_root, host=args.host, port=args.port)
            print(f"[serve] Serving {site_root} at {server.url}")
            print("[serve] Press Ctrl+C to stop the preview server.")
            if args.open_browser:
                webbrowser.open(server.url)
            try:
                while server.is_alive():
                    server.join(timeout=0.5)
            except KeyboardInterrupt:
                print("\n[serve] Shutting down preview server…")
            finally:
                server.stop()

    command_registry.register(
        Command(
            name="web",
            help="Generate the Auto3D marketing site and optional download bundle",
            configure=configure_web,
            handler=handle_web,
        )
    )

    def configure_automation(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--url", required=True, help="Target webpage for the upload workflow")
        parser.add_argument("--upload-path", type=Path, help="STL file to upload (defaults to outputs/assembled.stl)")
        parser.add_argument("--output", type=Path, help="Where to write the generated Playwright script")
        parser.add_argument("--upload-selector", default="input[type=file]", help="CSS selector for the upload input")
        parser.add_argument("--start", action="append", dest="starts", help="Selector to click before uploading (repeat)")
        parser.add_argument("--click", action="append", dest="clicks", help="Extra selectors to click after setting files")
        parser.add_argument("--submit", help="Selector to click after uploading")
        parser.add_argument("--wait-ms", type=int, default=5000, help="Extra wait time (ms) after the upload flow")
        parser.add_argument("--headless", action="store_true", help="Launch Chromium in headless mode")
        parser.add_argument("--no-network-idle", action="store_true", help="Skip waiting for network idle")
        parser.add_argument("--note", action="append", dest="notes", help="Inline note to embed in the generated script")

    def handle_automation(app: Auto3DApplication, args: argparse.Namespace) -> None:
        script_path = app.create_playwright_script(
            url=args.url,
            output=args.output,
            upload_path=args.upload_path,
            upload_selector=args.upload_selector,
            start_selectors=args.starts,
            extra_clicks=args.clicks,
            submit_selector=args.submit,
            wait_for_network_idle=not args.no_network_idle,
            wait_time_ms=args.wait_ms,
            headless=args.headless,
            notes=args.notes,
        )
        print(f"[automation] script: {script_path}")
        for tip in app.automation_guidelines():
            print(f"[tip] {tip}")

    command_registry.register(
        Command(
            name="automation",
            help="Generate a Playwright STL upload automation script",
            configure=configure_automation,
            handler=handle_automation,
        )
    )

    def configure_regulations(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--region", action="append", dest="regions", help="Filter by region (e.g., alberta, canada)")
        parser.add_argument("--scale", action="append", dest="scales", help="Filter by scale (toy, residential, commercial)")
        parser.add_argument("--keyword", action="append", dest="keywords", help="Keyword filter (e.g., energy, infill)")
        parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
        parser.add_argument("--limit", type=int, help="Limit number of entries")

    def handle_regulations(app: Auto3DApplication, args: argparse.Namespace) -> None:
        entries = app.building_codes(regions=args.regions, keywords=args.keywords, scales=args.scales)
        if args.limit is not None:
            entries = entries[: args.limit]
        if args.format == "json":
            import json

            print(json.dumps([entry.to_dict() for entry in entries], indent=2))
            return
        for entry in entries:
            print(f"- {entry.name} ({entry.jurisdiction}) [{entry.region}]")
            print(f"  URL: {entry.url}")
            print(f"  Applies to: {', '.join(entry.scale_applicability)}")
            for note in entry.notes:
                print(f"  - {note}")

    command_registry.register(
        Command(
            name="regulations",
            help="List regional building code references",
            configure=configure_regulations,
            handler=handle_regulations,
        )
    )

    def configure_wizard(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--config", type=Path, help="Location to store wizard defaults")
        parser.add_argument("--auto", action="store_true", help="Run using stored defaults without prompting")
        parser.add_argument("--reset", action="store_true", help="Ignore any stored defaults when prompting")
        parser.add_argument("--no-remember", action="store_true", help="Do not persist new defaults after completion")

    def handle_wizard(app: Auto3DApplication, args: argparse.Namespace) -> None:
        remember = not args.no_remember
        try:
            state = app.run_wizard(
                config_path=args.config,
                auto=args.auto,
                reset=args.reset,
                remember=remember,
            )
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        print("[wizard] Completed pipeline run for workspace:", state.workspace)

    command_registry.register(
        Command(
            name="wizard",
            help="Use the interactive wizard or its unattended variant",
            configure=configure_wizard,
            handler=handle_wizard,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    _register_defaults()
    parser = argparse.ArgumentParser(prog="auto3d", description="High-level Auto3D pipeline controls")
    parser.add_argument("--workspace", type=Path, default=Path("Auto3D-Render-to-STL"), help="Workspace directory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in command_registry.values():
        sub = subparsers.add_parser(command.name, help=command.help)
        command.configure(sub)
        sub.set_defaults(_command=command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    app = Auto3DApplication(workspace=args.workspace)
    command: Command = args._command
    command.handler(app, args)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
