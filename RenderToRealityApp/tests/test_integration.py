"""Integration tests for the RenderToRealityApp pipeline."""
import tempfile
from pathlib import Path
from PIL import Image
import numpy as np


def test_depth_generation_fallback():
    """Test that depth generation works with fallback (no torch/MiDaS)."""
    from main import MidasDepth
    
    # Create a test image
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        test_img = tmp_path / "test.png"
        arr = np.zeros((100, 150, 3), dtype='uint8')
        arr[20:80, 40:110] = 255  # White rectangle
        Image.fromarray(arr).save(test_img)
        
        # Generate depth map
        md = MidasDepth()
        depth_out = tmp_path / "depth.png"
        ok = md.gen_depth(test_img, depth_out)
        
        assert ok, "Depth generation should succeed"
        assert depth_out.exists(), "Depth map should be created"
        
        # Verify the depth map is a valid image
        depth_img = Image.open(depth_out)
        assert depth_img.size == (150, 100), "Depth map should have same dimensions"


def test_full_analysis_without_depth():
    """Test full image analysis without depth map."""
    from scripts import ratio_analysis
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        test_img = tmp_path / "test.png"
        arr = np.zeros((200, 300, 3), dtype='uint8')
        arr[50:150, 100:200] = 255
        Image.fromarray(arr).save(test_img)
        
        # Analyze without depth
        result = ratio_analysis.analyze_image(str(test_img), depth_path=None, known_width_mm=100.0)
        
        assert result["file"] == "test.png"
        assert result["width_px"] == 300
        assert result["height_px"] == 200
        assert result["known_width_mm"] == 100.0
        assert result["mm_per_px"] is not None
        assert result["depth_stats"] is None  # No depth map provided


def test_full_analysis_with_depth():
    """Test full image analysis with depth map."""
    from scripts import ratio_analysis
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        test_img = tmp_path / "test.png"
        depth_img = tmp_path / "depth.png"
        
        # Create test image and depth map
        arr = np.zeros((200, 300, 3), dtype='uint8')
        arr[50:150, 100:200] = 255
        Image.fromarray(arr).save(test_img)
        
        depth_arr = np.random.randint(50, 200, (200, 300), dtype='uint8')
        Image.fromarray(depth_arr).save(depth_img)
        
        # Analyze with depth
        result = ratio_analysis.analyze_image(str(test_img), depth_path=str(depth_img), known_width_mm=0.0)
        
        assert result["file"] == "test.png"
        assert result["depth_stats"] is not None
        assert "min" in result["depth_stats"]
        assert "max" in result["depth_stats"]
        assert "mean" in result["depth_stats"]
        assert "coverage_pct" in result["depth_stats"]
