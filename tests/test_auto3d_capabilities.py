import unittest

from auto3d.capabilities import capability_catalog, recommended_capabilities


class CapabilityCatalogTests(unittest.TestCase):
    def test_catalog_contains_expected_entries(self) -> None:
        catalog = capability_catalog()
        self.assertGreaterEqual(len(catalog), 6)
        keys = {cap.key for cap in catalog}
        self.assertIn("tripo_sr_single_image", keys)
        self.assertIn("meshroom_photogrammetry", keys)
        self.assertIn("distributed_hpc_orchestration", keys)

    def test_recommendations_reflect_style_tags(self) -> None:
        capabilities = recommended_capabilities(
            style_tags=["Scottish", "Canadian", "Picaresque"],
            floors=3,
            has_basement=True,
        )
        keys = [cap.key for cap in capabilities]
        self.assertIn("tripo_sr_single_image", keys)
        self.assertIn("meshroom_photogrammetry", keys)
        self.assertIn("freecad_brep_conversion", keys)
        self.assertIn("controlnet_view_synthesis", keys)
        self.assertIn("material_diffusion_baking", keys)
        self.assertIn("distributed_hpc_orchestration", keys)
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == "__main__":
    unittest.main()
