"""Tests for the static mission-control site generator."""
from __future__ import annotations

import unittest
import zipfile
from pathlib import Path

from auto3d.app import Auto3DApplication
from auto3d.site import start_site_server


class Auto3DSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(self._tmp_dir())

    def _tmp_dir(self) -> str:
        import tempfile

        return tempfile.mkdtemp(prefix="auto3d-site-test-")

    def tearDown(self) -> None:
        import shutil

        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_build_site_creates_assets_and_bundle(self) -> None:
        workspace = self.tmp / "workspace"
        app = Auto3DApplication(workspace=workspace)

        output_dir = self.tmp / "site"
        outputs = app.build_site(
            output=output_dir,
            protocol="1JGM∞.BE",
            include_bundle=True,
            force=True,
        )

        index = outputs["index"]
        self.assertTrue(index.exists())
        html = index.read_text(encoding="utf-8")
        self.assertIn("Auto3D Mission Control", html)
        self.assertIn("Protocol 1JGM∞.BE", html)
        self.assertIn("downloads/auto3d-application.zip", html)
        self.assertIn("Supercomputing Visuals", html)
        self.assertIn("Automation Playbook", html)
        self.assertIn("Regulation Atlas", html)
        self.assertIn("Supercomputing Blueprint", html)
        self.assertIn("Mission Control", html)
        self.assertIn("Printability Gate", html)

        self.assertTrue(outputs["styles"].exists())
        self.assertTrue(outputs["script"].exists())

        bundle = outputs["bundle"]
        self.assertTrue(zipfile.is_zipfile(bundle))
        with zipfile.ZipFile(bundle) as archive:
            names = set(archive.namelist())
            self.assertIn("auto3d/app.py", names)
            self.assertIn("scripts/auto3d_prompt_to_stl.py", names)
            self.assertIn("scripts/auto3d_test.py", names)
            self.assertIn("docs/auto3d-pipeline.md", names)

    def test_build_site_requires_force_when_dir_exists(self) -> None:
        workspace = self.tmp / "workspace"
        app = Auto3DApplication(workspace=workspace)

        output_dir = self.tmp / "existing"
        output_dir.mkdir(parents=True)

        with self.assertRaises(FileExistsError):
            app.build_site(output=output_dir, include_bundle=False)

        outputs = app.build_site(output=output_dir, include_bundle=False, force=True)
        self.assertNotIn("bundle", outputs)
        self.assertTrue((output_dir / "index.html").exists())

    def test_preview_server_serves_generated_site(self) -> None:
        workspace = self.tmp / "workspace"
        app = Auto3DApplication(workspace=workspace)

        output_dir = self.tmp / "site"
        app.build_site(output=output_dir, include_bundle=False, force=True)

        server = start_site_server(output_dir, host="127.0.0.1", port=0)
        try:
            import time
            import urllib.request

            # Give the server a moment to start accepting connections
            for _ in range(10):
                if server.is_alive():
                    time.sleep(0.05)
                else:
                    break

            with urllib.request.urlopen(server.url, timeout=5) as response:
                body = response.read().decode("utf-8")
                self.assertIn("Auto3D Mission Control", body)
                self.assertIn("Protocol 1JGM∞.BE", body)
                self.assertIn("Automation Playbook", body)
                self.assertIn("Supercomputing Blueprint", body)
                self.assertIn("Printability Gate", body)
        finally:
            server.stop()

