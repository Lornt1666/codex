import tempfile
import unittest
from pathlib import Path

from auto3d.app import Auto3DApplication
from auto3d.printability import (
    PrintabilityResult,
    evaluate_printability,
    render_printability_markdown,
    write_printability_report,
)


class PrintabilityEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name)

    def test_detects_zero_thickness(self) -> None:
        stl = self.workspace / "flat.stl"
        stl.write_text(
            "\n".join(
                [
                    "solid flat",
                    "  facet normal 0 0 1",
                    "    outer loop",
                    "      vertex 0 0 0",
                    "      vertex 1 0 0",
                    "      vertex 0 1 0",
                    "    endloop",
                    "  endfacet",
                    "endsolid flat",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = evaluate_printability([stl], min_thickness_mm=0.1)
        self.assertIsInstance(result, PrintabilityResult)
        self.assertFalse(result.success)
        self.assertTrue(any("zero thickness" in issue.message for issue in result.issues))

    def test_writes_markdown_summary(self) -> None:
        stl = self.workspace / "box.stl"
        stl.write_text(
            "\n".join(
                [
                    "solid box",
                    "  facet normal 0 0 1",
                    "    outer loop",
                    "      vertex 0 0 0",
                    "      vertex 1 0 0",
                    "      vertex 0 1 0",
                    "    endloop",
                    "  endfacet",
                    "  facet normal 0 0 -1",
                    "    outer loop",
                    "      vertex 0 0 1",
                    "      vertex 0 1 1",
                    "      vertex 1 0 1",
                    "    endloop",
                    "  endfacet",
                    "endsolid box",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        result = evaluate_printability([stl], min_thickness_mm=0.0)
        self.assertTrue(result.success)
        markdown = render_printability_markdown(result)
        self.assertIn("Printability Gate", markdown)
        self.assertIn("Status", markdown)
        report_path = write_printability_report(self.workspace, result)
        self.assertTrue(report_path.exists())
        self.assertIn("Recommendations", report_path.read_text(encoding="utf-8"))

    def test_application_assess_printability_defaults_to_workspace_outputs(self) -> None:
        workspace = self.workspace / "Auto3D-Render-to-STL"
        outputs = workspace / "outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        stl = outputs / "floor_01.stl"
        stl.write_text(
            "\n".join(
                [
                    "solid floor",
                    "  facet normal 0 0 1",
                    "    outer loop",
                    "      vertex 0 0 0",
                    "      vertex 1 0 0",
                    "      vertex 0 1 0",
                    "    endloop",
                    "  endfacet",
                    "  facet normal 0 0 -1",
                    "    outer loop",
                    "      vertex 0 0 1",
                    "      vertex 0 1 1",
                    "      vertex 1 0 1",
                    "    endloop",
                    "  endfacet",
                    "endsolid floor",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        app = Auto3DApplication(workspace=workspace)
        result, report_path = app.assess_printability()
        self.assertTrue(result.success)
        self.assertIsNotNone(report_path)
        self.assertTrue(report_path.exists())
        self.assertTrue(report_path.parent.samefile(outputs))

    def test_application_assess_printability_resolves_relative_paths(self) -> None:
        workspace = self.workspace / "Auto3D-Render-to-STL"
        outputs = workspace / "outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        stl = outputs / "roof.stl"
        stl.write_text(
            "\n".join(
                [
                    "solid roof",
                    "  facet normal 0 0 1",
                    "    outer loop",
                    "      vertex 0 0 0",
                    "      vertex 2 0 0",
                    "      vertex 0 2 0",
                    "    endloop",
                    "  endfacet",
                    "  facet normal 0 0 -1",
                    "    outer loop",
                    "      vertex 0 0 1",
                    "      vertex 0 2 1",
                    "      vertex 2 0 1",
                    "    endloop",
                    "  endfacet",
                    "endsolid roof",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        app = Auto3DApplication(workspace=workspace)
        result, report_path = app.assess_printability(
            stl_paths=[Path("outputs/roof.stl")],
            report_dir=Path("reports"),
            report_name="roof.md",
        )

        self.assertTrue(result.success)
        self.assertIsNotNone(report_path)
        self.assertTrue(report_path.exists())
        self.assertEqual(report_path.name, "roof.md")
        self.assertTrue(report_path.parent.samefile(workspace / "reports"))


if __name__ == "__main__":
    unittest.main()
