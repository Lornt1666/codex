import pytest
from scripts import ratio_analysis
from pathlib import Path
import numpy as np
import cv2

def test_analyze_image(tmp_path):
    # Create a simple test image
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    cv2.rectangle(img, (10, 10), (190, 90), (255, 255, 255), -1)
    img_path = tmp_path / "test.png"
    cv2.imwrite(str(img_path), img)
    # Run analysis
    result = ratio_analysis.analyze_image(str(img_path))
    assert result["width_px"] == 200
    assert result["height_px"] == 100
    assert result["lines_detected"] >= 0
