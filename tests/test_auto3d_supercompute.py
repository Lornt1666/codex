"""Tests for the Auto3D supercomputing blueprint helpers."""
from __future__ import annotations

import unittest

from auto3d.supercompute import (
    SUPERCOMPUTE_REQUIRED_CAPABILITIES,
    evaluate_supercompute,
    supercompute_blueprint,
)


class SupercomputeBlueprintTests(unittest.TestCase):
    def test_blueprint_contains_expected_layers(self) -> None:
        blueprint = supercompute_blueprint(protocol="1JGM∞.BE")
        self.assertEqual(blueprint.protocol, "1JGM∞.BE")
        self.assertGreaterEqual(len(blueprint.layers), 4)
        layer_keys = {layer.key for layer in blueprint.layers}
        self.assertIn("ingestion", layer_keys)
        self.assertIn("orchestration", layer_keys)

    def test_evaluate_reports_missing_capabilities(self) -> None:
        readiness = evaluate_supercompute(available_capabilities=[], protocol="1JGM∞.BE")
        self.assertEqual(readiness.blueprint.protocol, "1JGM∞.BE")
        self.assertEqual(tuple(readiness.available_capabilities), ())
        self.assertEqual(readiness.missing_capabilities, SUPERCOMPUTE_REQUIRED_CAPABILITIES)
        self.assertGreater(len(readiness.recommended_actions), 0)

    def test_evaluate_handles_full_stack(self) -> None:
        readiness = evaluate_supercompute(
            available_capabilities=SUPERCOMPUTE_REQUIRED_CAPABILITIES,
            protocol="1JGM∞.BE",
        )
        self.assertEqual(tuple(readiness.missing_capabilities), ())
        self.assertEqual(
            readiness.recommended_actions,
            ("All required capabilities are present. Scale monitoring and resilience next.",),
        )


if __name__ == "__main__":
    unittest.main()
