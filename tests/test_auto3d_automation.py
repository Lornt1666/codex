from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auto3d.automation import PlaywrightScriptConfig, automation_guidelines, render_playwright_script, write_playwright_script
from auto3d.regulations import building_code_catalog, filter_building_codes


class PlaywrightScriptTests(unittest.TestCase):
    def test_render_script_includes_selectors(self) -> None:
        config = PlaywrightScriptConfig(
            url="https://example.com/upload",
            upload_path=Path("outputs/assembled.stl"),
            start_selectors=("button#start",),
            extra_clicks=("button#confirm",),
            submit_selector="button#submit",
            wait_time_ms=2500,
            headless=True,
            notes=("Use staging credentials",),
        )
        script = render_playwright_script(config)
        self.assertIn("button#start", script)
        self.assertIn("button#confirm", script)
        self.assertIn("button#submit", script)
        self.assertIn("page.wait_for_timeout(2500)", script)
        self.assertIn("headless=True", script)
        self.assertIn("# NOTE: Use staging credentials", script)

    def test_write_script_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upload.py"
            config = PlaywrightScriptConfig(
                url="https://example.com/upload",
                upload_path=Path("outputs/assembled.stl"),
            )
            result = write_playwright_script(path, config)
            self.assertTrue(result.exists())
            contents = result.read_text(encoding="utf-8")
            self.assertIn("https://example.com/upload", contents)
            self.assertIn("UPLOAD_SELECTOR", contents)

    def test_guidelines_not_empty(self) -> None:
        tips = automation_guidelines()
        self.assertGreaterEqual(len(tips), 3)
        for tip in tips:
            self.assertTrue(tip)


class BuildingCodeCatalogTests(unittest.TestCase):
    def test_catalog_contains_alberta_reference(self) -> None:
        catalog = building_code_catalog()
        alberta = [entry for entry in catalog if entry.region == "alberta"]
        self.assertTrue(alberta)

    def test_filtering_by_region_and_scale(self) -> None:
        filtered = filter_building_codes(regions=["alberta"], scales=["residential"])
        self.assertTrue(filtered)
        for entry in filtered:
            self.assertEqual(entry.region, "alberta")
            self.assertTrue(any(scale.lower() == "residential" for scale in entry.scale_applicability))

    def test_keyword_filtering(self) -> None:
        energy = filter_building_codes(keywords=["energy"])
        self.assertTrue(any("Energy" in entry.name or "Energy" in entry.description for entry in energy))


if __name__ == "__main__":  # pragma: no cover - test entrypoint
    unittest.main()
