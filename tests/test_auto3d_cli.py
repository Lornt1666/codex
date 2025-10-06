"""Tests for the Auto3D CLI helpers that wire quality gates."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Sequence
from types import SimpleNamespace
from unittest import mock

from auto3d.app import Auto3DApplication
from auto3d import cli
from auto3d.app import COMPILE_TARGETS


class Auto3DTestRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name) / "workspace"

    def test_run_tests_builds_expected_commands(self) -> None:
        app = Auto3DApplication(workspace=self.workspace)
        executed: list[tuple[tuple[str, ...], Path]] = []

        def executor(command: Sequence[str], cwd: Path) -> None:
            executed.append((tuple(command), cwd))

        commands = app.run_tests(executor=executor)
        self.assertEqual(len(commands), 2)
        compile_cmd, test_cmd = commands

        self.assertEqual(compile_cmd[0], sys.executable)
        self.assertEqual(compile_cmd[1:3], ("-m", "compileall"))
        self.assertEqual(tuple(compile_cmd[3:]), COMPILE_TARGETS)

        self.assertEqual(test_cmd[0], sys.executable)
        self.assertEqual(test_cmd[1:3], ("-m", "unittest"))
        self.assertGreaterEqual(len(test_cmd[3:]), 1)
        for module in test_cmd[3:]:
            self.assertTrue(module.startswith("tests."))

        self.assertEqual(len(executed), 2)
        project_root = Path(__file__).resolve().parent.parent
        for _, cwd in executed:
            self.assertTrue(project_root.samefile(cwd))

    def test_run_tests_supports_custom_modules(self) -> None:
        app = Auto3DApplication(workspace=self.workspace)
        executed: list[tuple[tuple[str, ...], Path]] = []

        def executor(command: Sequence[str], cwd: Path) -> None:
            executed.append((tuple(command), cwd))

        commands = app.run_tests(
            run_compileall=False,
            modules=["tests.only_me"],
            executor=executor,
        )

        self.assertEqual(len(commands), 1)
        self.assertEqual(len(executed), 1)
        command, cwd = executed[0]
        self.assertEqual(commands[0], command)
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(command[1:3], ("-m", "unittest"))
        self.assertEqual(command[3:], ("tests.only_me",))
        project_root = Path(__file__).resolve().parent.parent
        self.assertTrue(project_root.samefile(cwd))


class Auto3DCLITestCommand(unittest.TestCase):
    def test_cli_test_command_invokes_application(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "Auto3D-Render-to-STL"
            with mock.patch("auto3d.cli.Auto3DApplication") as mock_app:
                instance = mock_app.return_value
                instance.run_tests.return_value = [("cmd",)]

                exit_code = cli.main(
                    [
                        "--workspace",
                        str(workspace),
                        "test",
                        "--skip-compile",
                        "--module",
                        "tests.custom",
                    ]
                )

                self.assertEqual(exit_code, 0)
                instance.run_tests.assert_called_once_with(
                    run_compileall=False,
                    modules=["tests.custom"],
                )

    def test_cli_automation_command_invokes_application(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "Auto3D-Render-to-STL"
            with mock.patch("auto3d.cli.Auto3DApplication") as mock_app:
                instance = mock_app.return_value
                instance.create_playwright_script.return_value = Path("script.py")
                instance.automation_guidelines.return_value = ["Install Playwright", "Use staging"]

                exit_code = cli.main(
                    [
                        "--workspace",
                        str(workspace),
                        "automation",
                        "--url",
                        "https://example.com/upload",
                        "--upload-path",
                        "outputs/assembled.stl",
                        "--start",
                        "button#start",
                        "--click",
                        "button#confirm",
                        "--submit",
                        "button#submit",
                        "--wait-ms",
                        "1234",
                        "--headless",
                        "--note",
                        "watch staging",
                    ]
                )

                self.assertEqual(exit_code, 0)
                instance.create_playwright_script.assert_called_once_with(
                    url="https://example.com/upload",
                    output=None,
                    upload_path=Path("outputs/assembled.stl"),
                    upload_selector="input[type=file]",
                    start_selectors=["button#start"],
                    extra_clicks=["button#confirm"],
                    submit_selector="button#submit",
                    wait_for_network_idle=True,
                    wait_time_ms=1234,
                    headless=True,
                    notes=["watch staging"],
                )
                instance.automation_guidelines.assert_called_once_with()

    def test_cli_regulations_command_invokes_application(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "Auto3D-Render-to-STL"
            with mock.patch("auto3d.cli.Auto3DApplication") as mock_app:
                entry = SimpleNamespace(
                    name="Alberta Building Code 2019",
                    jurisdiction="Province of Alberta",
                    region="alberta",
                    url="https://example.com",
                    scale_applicability=("residential",),
                    notes=("Primary housing code",),
                    to_dict=lambda: {
                        "name": "Alberta Building Code 2019",
                        "jurisdiction": "Province of Alberta",
                        "region": "alberta",
                        "url": "https://example.com",
                        "scale_applicability": ("residential",),
                        "notes": ("Primary housing code",),
                    },
                )
                instance = mock_app.return_value
                instance.building_codes.return_value = [entry]

                exit_code = cli.main(
                    [
                        "--workspace",
                        str(workspace),
                        "regulations",
                        "--region",
                        "alberta",
                        "--scale",
                        "residential",
                        "--keyword",
                        "energy",
                    ]
                )

                self.assertEqual(exit_code, 0)
                instance.building_codes.assert_called_once_with(
                    regions=["alberta"],
                    keywords=["energy"],
                    scales=["residential"],
                )

    def test_cli_printability_command_invokes_application(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "Auto3D-Render-to-STL"
            with mock.patch("auto3d.cli.Auto3DApplication") as mock_app, mock.patch(
                "auto3d.cli.render_printability_markdown", return_value="summary"
            ):
                instance = mock_app.return_value
                result = SimpleNamespace(success=True)
                instance.assess_printability.return_value = (
                    result,
                    Path("outputs/printability.md"),
                )

                exit_code = cli.main(
                    [
                        "--workspace",
                        str(workspace),
                        "printability",
                        "--stl",
                        "outputs/floor_01.stl",
                        "--report-dir",
                        "reports",
                        "--report-name",
                        "gate.md",
                    ]
                )

                self.assertEqual(exit_code, 0)
                instance.assess_printability.assert_called_once_with(
                    stl_paths=[Path("outputs/floor_01.stl")],
                    report_dir=Path("reports"),
                    write_report=True,
                    report_name="gate.md",
                )

    def test_cli_printability_command_nonzero_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "Auto3D-Render-to-STL"
            with mock.patch("auto3d.cli.Auto3DApplication") as mock_app, mock.patch(
                "auto3d.cli.render_printability_markdown", return_value=""
            ):
                instance = mock_app.return_value
                result = SimpleNamespace(success=False)
                instance.assess_printability.return_value = (result, None)

                with self.assertRaises(SystemExit) as exc:
                    cli.main([
                        "--workspace",
                        str(workspace),
                        "printability",
                    ])

                self.assertEqual(exc.exception.code, 1)
                instance.assess_printability.assert_called_once_with(
                    stl_paths=None,
                    report_dir=None,
                    write_report=True,
                    report_name="printability.md",
                )

    def test_cli_supercompute_command_invokes_application(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "Auto3D-Render-to-STL"
            with mock.patch("auto3d.cli.Auto3DApplication") as mock_app:
                from auto3d.capabilities import capability_catalog
                from auto3d.supercompute import evaluate_supercompute

                readiness = evaluate_supercompute(
                    available_capabilities=list(
                        cap.key for cap in capability_catalog()
                        if cap.key in {
                            "tripo_sr_single_image",
                            "controlnet_view_synthesis",
                            "meshroom_photogrammetry",
                            "nerfstudio_gaussian",
                            "geonodes_parametric",
                            "freecad_brep_conversion",
                            "meshfix_print_prep",
                            "material_diffusion_baking",
                            "distributed_hpc_orchestration",
                        }
                    ),
                    protocol="1JGM∞.BE",
                )
                catalog = {cap.key: cap for cap in capability_catalog()}
                available = tuple(catalog[key] for key in readiness.available_capabilities if key in catalog)

                instance = mock_app.return_value
                instance.supercompute_blueprint.return_value = SimpleNamespace(
                    readiness=readiness,
                    available_capabilities=available,
                    missing_capabilities=tuple(),
                )

                exit_code = cli.main(
                    [
                        "--workspace",
                        str(workspace),
                        "supercompute",
                        "--capability",
                        "tripo_sr_single_image",
                        "--capability",
                        "distributed_hpc_orchestration",
                    ]
                )

                self.assertEqual(exit_code, 0)
                instance.supercompute_blueprint.assert_called_once_with(
                    available_capabilities=[
                        "tripo_sr_single_image",
                        "distributed_hpc_orchestration",
                    ],
                    protocol="1JGM∞.BE",
                )
