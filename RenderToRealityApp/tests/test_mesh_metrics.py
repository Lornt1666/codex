import tempfile
from pathlib import Path
from scripts import mesh_metrics
import trimesh


def test_analyze_stl_box():
    box = trimesh.creation.box(extents=(10.0, 20.0, 5.0))
    tmp = tempfile.TemporaryDirectory()
    out = Path(tmp.name) / "box.stl"
    box.export(out)

    res = mesh_metrics.analyze_stl(str(out))
    assert res["filename"] == out.name
    assert "width_mm" in res
    assert res["triangles"] > 0
