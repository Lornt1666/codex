"""Lightweight integration tests for the prompt-driven stack.

These checks intentionally exercise the Auto3D modules as a closed system so we
can guarantee the scaffolding, prompt parser, geometry estimators, and STL
writers stay in sync.  They do **not** attempt to drive external renderers or
photogrammetry pipelines—the goal is simply to confirm the Python toolkit can
stand alone when converting a descriptive brief into printable shells.
"""

import tempfile
import unittest
from pathlib import Path

from auto3d.app import Auto3DApplication
from auto3d import prompt


USER_PROMPT = (
    "Coordinate a feature of rendering a house design, the usual 2 floors and basement "
    "but id like the outside to be light brown wooden edges with dark oak interior siding "
    "with charcoal stone with a feature of siding on the lower half etching the framework "
    "of the garage. Piercing in a fundamental portrayal of picaresque. But jaggedly poetic "
    "id like a Scottish/Irish/Dutch Scandinavian style with the textures and tones please "
    "with a feature of portrayal of a Canadian/American home please. 4 bedroom 2 bath "
    "unfinished basement (Just the furnace room and laundry room in the basement)."
)


class PromptExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.workspace = Path(self._tmp.name) / "Auto3D-Render-to-STL"

    def test_extracts_prompt_requirements(self) -> None:
        config = prompt.extract_prompt_config(USER_PROMPT)

        self.assertEqual(config.bedrooms, 4)
        self.assertAlmostEqual(config.bathrooms, 2.0)
        self.assertEqual(config.floors_above, 2)
        self.assertTrue(config.has_basement)
        self.assertIsNone(config.declared_square_feet)

        for tag in [
            "scottish",
            "irish",
            "dutch",
            "scandinavian",
            "canadian",
            "american",
            "picaresque",
            "poetic",
        ]:
            self.assertIn(tag, config.style_tags)

        geometry = prompt.estimate_geometry(config)
        self.assertAlmostEqual(geometry.main_width_ft, 34.8487, places=3)
        self.assertAlmostEqual(geometry.main_depth_ft, 23.6738, places=3)
        self.assertAlmostEqual(geometry.total_depth_ft, 36.6943, places=3)
        self.assertIsNotNone(geometry.garage)
        self.assertIsNotNone(geometry.porch)
        self.assertEqual(len(geometry.floors), 3)
        self.assertEqual([spec.label for spec in geometry.floors], [
            "Unfinished Basement",
            "Main Floor",
            "Upper Floor 1",
        ])
        self.assertEqual([spec.level for spec in geometry.floors], list(range(3)))
        self.assertEqual(geometry.wings, [])
        self.assertEqual(geometry.towers, [])
        self.assertGreaterEqual(len(geometry.notes), 2)

        model = prompt.convert_to_model_dims(geometry, scale=prompt.DEFAULT_MODEL_SCALE)
        self.assertAlmostEqual(model.width_mm, 106.22, delta=0.1)
        self.assertAlmostEqual(model.depth_mm, 111.84, delta=0.1)
        self.assertEqual(len(model.floor_heights_mm), 3)
        self.assertTrue(all(height > 0 for height in model.floor_heights_mm))
        self.assertGreater(model.roof_height_mm, 0.0)

    def test_generates_outputs(self) -> None:
        prompt.ensure_workspace(self.workspace, force=True)
        config = prompt.extract_prompt_config(USER_PROMPT)
        geometry = prompt.estimate_geometry(config)
        model = prompt.convert_to_model_dims(geometry, scale=prompt.DEFAULT_MODEL_SCALE)

        floors = prompt.generate_floor_stls(self.workspace, geometry, model)
        self.assertEqual([path.name for path in floors], [
            "floor_00_basement.stl",
            "floor_01_main.stl",
            "floor_02_upper1.stl",
        ])
        for path in floors:
            self.assertTrue(path.exists())
            first_line = path.read_text(encoding="utf-8").splitlines()[0]
            self.assertTrue(first_line.startswith("solid"))

        roof = prompt.generate_roof_stl(self.workspace, geometry, model)
        self.assertTrue(roof.exists())

        assembled = prompt.generate_assembled_stl(self.workspace, geometry, model, include_roof=True)
        self.assertTrue(assembled.exists())

        printability = prompt.evaluate_printability(floors + [roof, assembled])
        self.assertTrue(printability.success)
        printability_report = prompt.write_printability_report(
            self.workspace / "outputs", printability
        )
        self.assertTrue(printability_report.exists())
        print_text = printability_report.read_text(encoding="utf-8")
        self.assertIn("Printability Gate", print_text)
        self.assertIn("Status", print_text)

        report = prompt.write_report(
            self.workspace,
            prompt=USER_PROMPT,
            config=config,
            geometry=geometry,
            model=model,
            protocol=prompt.DEFAULT_PROTOCOL,
            scale=prompt.DEFAULT_MODEL_SCALE,
            printability=printability,
        )
        self.assertTrue(report.exists())
        report_text = report.read_text(encoding="utf-8")
        self.assertIn("Auto3D Prompt-to-STL Summary", report_text)
        self.assertIn("Protocol:", report_text)
        self.assertIn("cm |", report_text)
        self.assertIn("Generated Massing Features", report_text)
        self.assertIn("Central dormer", report_text)
        self.assertIn("Recommended AI Capability Stack", report_text)
        self.assertIn("TripoSR single-image reconstruction", report_text)
        self.assertIn("Printability Gate", report_text)
        self.assertIn("PASS", report_text)

    def test_application_prompt_to_stl(self) -> None:
        app_workspace = Path(self._tmp.name) / "AppWorkspace"
        app = Auto3DApplication(workspace=app_workspace)
        outputs = app.prompt_to_stl(
            USER_PROMPT,
            hero=None,
            include_roof=True,
            force=True,
            protocol="1JGM∞.BE",
        )

        expected = {
            "floor_00_basement.stl",
            "floor_01_main.stl",
            "floor_02_upper1.stl",
            "roof.stl",
            "assembled.stl",
            "printability.md",
            "auto3d_prompt_report.md",
        }
        self.assertTrue(expected.issubset(set(outputs)))
        for name, path in outputs.items():
            with self.subTest(name=name):
                self.assertTrue(path.exists())
                self.assertTrue(path.is_file())
        self.assertTrue(outputs["printability.md"].read_text(encoding="utf-8").startswith("## Printability Gate"))

    def test_application_prompt_catalog(self) -> None:
        app_workspace = Path(self._tmp.name) / "CatalogWorkspace"
        app = Auto3DApplication(workspace=app_workspace)
        outputs = app.prompt_catalog(
            USER_PROMPT,
            hero=None,
            include_roof=True,
            force=True,
            protocol="1JGM∞.BE",
            limit=2,
        )

        self.assertIn("standard", outputs)
        standard_assets = outputs["standard"]
        self.assertTrue(any(path.name == "floor_00_basement.stl" for path in standard_assets))
        self.assertTrue(any(path.name == "report.md" for path in standard_assets))
        self.assertTrue(any(path.name == "printability.md" for path in standard_assets))

        index_assets = outputs.get("index")
        self.assertIsNotNone(index_assets)
        self.assertGreater(len(index_assets), 0)
        index_path = index_assets[0]
        self.assertTrue(index_path.exists())
        index_text = index_path.read_text(encoding="utf-8")
        self.assertIn("Prompt Catalog", index_text)
        self.assertIn("standard", index_text)

    def test_buttress_variant_enriched_geometry(self) -> None:
        prompt_text = (
            USER_PROMPT
            + " Vandited flying buttresses and legendary engineering arches cascade around the home."
        )
        config = prompt.extract_prompt_config(prompt_text)
        self.assertIn("buttress", config.style_tags)
        self.assertIn("legendary", config.style_tags)

        base_geometry = prompt.estimate_geometry(config)
        variants = prompt.default_catalog_variants(config, base_geometry)
        buttress_variant = next(variant for variant in variants if variant.key == "buttress")
        enhanced = buttress_variant.adjust(config, base_geometry)

        self.assertGreater(len(enhanced.buttresses), 0)
        self.assertTrue(any(spec.flying for spec in enhanced.buttresses))
        self.assertTrue(
            any(spec.bridge_length_ft > 0 for spec in enhanced.buttresses if spec.flying)
        )
        self.assertTrue(any("buttress" in note.lower() for note in enhanced.notes))


if __name__ == "__main__":
    unittest.main()
