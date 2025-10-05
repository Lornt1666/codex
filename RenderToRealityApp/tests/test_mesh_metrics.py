from scripts import mesh_metrics
import trimesh
import tempfile

def test_analyze_stl():
    # Create a simple cube mesh
    mesh = trimesh.creation.box(extents=(10, 20, 30))
    with tempfile.NamedTemporaryFile(suffix=".stl") as f:
        mesh.export(f.name)
        result = mesh_metrics.analyze_stl(f.name)
        assert result["width_mm"] == pytest.approx(10)
        assert result["depth_mm"] == pytest.approx(20)
        assert result["height_mm"] == pytest.approx(30)
        assert result["triangles"] > 0
