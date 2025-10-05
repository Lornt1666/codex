import trimesh
import os

def analyze_stl(path: str):
    """
    Analyze STL/OBJ/GLB mesh with trimesh.
    Returns dict with size (mm), volume (cm^3), triangle count.
    """
    try:
        mesh = trimesh.load(path, force='mesh')
        if mesh.is_empty:
            return {"filename": os.path.basename(path), "error": "Empty mesh"}
        bounds = mesh.bounds  # (min, max) 3D
        dims = bounds[1] - bounds[0]  # X, Y, Z
        vol_mm3 = float(mesh.volume) if mesh.volume is not None else 0.0
        tri_count = int(mesh.faces.shape[0]) if hasattr(mesh, "faces") else 0

        return {
            "filename": os.path.basename(path),
            "width_mm": float(dims[0]),
            "depth_mm": float(dims[1]),
            "height_mm": float(dims[2]),
            "volume_cm3": float(vol_mm3 / 1000.0),  # mm^3 → cm^3
            "triangles": tri_count,
            "notes": "OK",
        }
    except Exception as e:
        return {"filename": os.path.basename(path), "error": str(e)}
