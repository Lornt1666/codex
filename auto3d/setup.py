"""Create the Auto3D-Render-to-STL workspace with helper scripts."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

README_CONTENT = '''# Auto3D-Render-to-STL (Windows-friendly)

This repo gives you a **practical pipeline** to go from **ChatGPT-rendered house images** → **auto 3D mesh** → **floor-by-floor STL** for 3D printing.

> You control the STL quality and the floor split heights. It’s designed to be dead-simple, modular, and recoverable if any step fails.

---

## TL;DR (Quick Start)
1. Put your best **single hero image** of the house in: `input_images/hero.png` (PNG or JPG).
2. Install Python 3.10+ on Windows, then in **PowerShell**:
   ```powershell
   cd "<path-to-project>"
   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1
   pip install -U pip wheel
   pip install trimesh shapely numpy pyyaml
   ```
3. Generate a base mesh from the hero image using TripoSR (fast single-image-to-3D, MIT-licensed). Install TripoSR (follow their README): <https://github.com/VAST-AI-Research/TripoSR>

   Example command (after TripoSR is installed):
   ```powershell
   # Adjust the path to your TripoSR entrypoint if needed
   python path\\to\\tripoSR\\demo.py --input "input_images/hero.png" --output "working/house_mesh.obj"
   ```
4. If you have multiple views (front/back/left/right/top/iso), you’ll get better results using a multi-view method like COLMAP+OpenMVS or Meshroom (AliceVision). See **Multi-View Option** below.
5. Edit `configs/floors.yaml` and set your floor split heights (in the mesh’s Z-units; we’ll help you scale in Blender later if needed).
6. Run the slicer to output one STL per floor:
   ```powershell
   python scripts\\2_slice_mesh_to_floors.py --mesh "working/house_mesh.obj" --config "configs/floors.yaml" --outdir "outputs"
   ```
7. Your STLs will be in `outputs/` — one per floor, plus an assembled STL if you want a single-piece print.

---

## What’s inside
```
Auto3D-Render-to-STL/
├── input_images/           # drop your ChatGPT renders here
├── working/                # intermediate meshes + temp files (OBJ/GLB/etc.)
├── outputs/                # final STL files per floor
├── scripts/
│   ├── 1_notes_triposr.md
│   ├── 2_slice_mesh_to_floors.py
│   ├── 3_blender_floor_exploder.py
│   ├── auto_cleanup.py
│   └── run_pipeline.bat
└── configs/
    └── floors.yaml
```

---

## Multi-View Option (better geometry)

If you can generate 6+ consistent views of the house (front/back/left/right/top, plus a couple of angled isometrics), you can use:

- Meshroom (AliceVision) GUI (easy) — <https://alicevision.org/#meshroom>
- COLMAP + OpenMVS (scriptable).

These will produce a textured mesh with more accurate walls. Export as OBJ/PLY/GLB into `working/house_mesh.obj`.

Tip: If your ChatGPT renders aren’t consistent, tell the image model to keep identical proportions and window/door placements across views. Naming the house and re-using that name in every prompt also helps consistency.

---

## Floor Slicing 101

We split the mesh into floors by Z heights. You define breakpoints in `configs/floors.yaml`.

Example:

```yaml
units_hint: "meters"     # or "cm" or "arbitrary"
floor_breaks_z:          # Z-heights (same units as your mesh)
  - 0.0                  # ground level
  - 3.0                  # top of floor 1
  - 6.2                  # top of floor 2 (etc.)
close_holes: true
weld_threshold: 0.0005
export_assembled: true
```

The slicer will:

1. Separate faces whose vertices lie within each `[z_min, z_max]` band.
2. Attempt to close open cross-sections (caps) so every floor is watertight for STL.
3. Export `floor_01.stl`, `floor_02.stl`, … and optional `assembled.stl`.

If your mesh comes in tiny or huge, don’t sweat it. After slicing, use Blender to scale the STL to your printer’s target (e.g., 1:100).

---

## Optional: Blender Exploded View

Use `3_blender_floor_exploder.py` to:

- Import your sliced floors.
- Auto “explode” them apart vertically for inspection.
- Export a GLB or FBX for sharing.

Run from Blender:

```powershell
"C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe" --background --python scripts\\3_blender_floor_exploder.py -- --indir "outputs" --explode 0.2 --export "outputs\\house_exploded.glb"
```

---

## CAD-ish Output

Need crisper edges/walls? After you’ve got a decent base mesh:

- In Blender: use Remesh (Voxel/Quadriflow) + Edge Crease + Solidify to regularize walls.
- Or push the mesh through a mesh-to-CAD tool (Moi3D, Rhino + QuadRemesh, FreeCAD’s Surface → Solid workflows).

---

## Troubleshooting

- **Messy interiors / hollow floors?** Increase `close_holes: true` and try `weld_threshold` up to `0.002`.
- **Floors bleed into each other?** Adjust `floor_breaks_z` or try a small gap between ranges (e.g., `3.0` becomes `2.99` in the config).
- **Gaps at slice caps?** The slicer auto-caps, but complex roofs might need manual patching in Blender (Grid Fill).
- **Scale off by 10× or 100×?** Common. Just scale in Blender after slicing.
- **Need fully automated multi-view?** Use Meshroom’s CLI or COLMAP scripting; swap in the resulting mesh path in step 5.

---

## License

All scripts here are MIT. You’re responsible for third-party tool licenses (TripoSR, Blender, etc.).
'''

FLOORS_YAML = '''units_hint: "meters"

# Define Z heights for floor splits (same units as your mesh; these are examples)
floor_breaks_z:
  - 0.0
  - 3.0
  - 6.0
  - 9.0
close_holes: true
weld_threshold: 0.0005
export_assembled: true
'''

TRIPOSR_NOTES = '''# Getting a Base Mesh via TripoSR (Single-Image 3D)

TripoSR turns one image into a rough 3D mesh fast (Windows-friendly).

## Install

Follow the official README: <https://github.com/VAST-AI-Research/TripoSR>

You need Python + PyTorch with CUDA for best performance.

## Run

Assuming your hero image is at `input_images/hero.png`:

```powershell
# From your TripoSR repo directory (adjust paths as needed)
python demo.py --input "PATH\\TO\\Auto3D-Render-to-STL\\input_images\\hero.png" --output "PATH\\TO\\Auto3D-Render-to-STL\\working\\house_mesh.obj"
```

This produces `working/house_mesh.obj`, which you can slice into floors with our `2_slice_mesh_to_floors.py` script.
'''

SLICE_SCRIPT = '''#!/usr/bin/env python3
"""
Slice a mesh into floor-by-floor STL files using Z height ranges.

Usage:
    python 2_slice_mesh_to_floors.py --mesh working/house_mesh.obj --config configs/floors.yaml --outdir outputs

Dependencies:
    pip install trimesh shapely numpy pyyaml
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import trimesh
import yaml


FaceMask = np.ndarray


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _select_faces_by_band(mesh: trimesh.Trimesh, zmin: float, zmax: float, eps: float = 1e-6) -> FaceMask:
    v_z = mesh.vertices[:, 2]
    mask = np.ones(len(mesh.faces), dtype=bool)
    for idx, face in enumerate(mesh.faces):
        ztri = v_z[face]
        if not (ztri.min() >= zmin - eps and ztri.max() <= zmax + eps):
            mask[idx] = False
    return mask


def slice_by_zbands(
    mesh: trimesh.Trimesh,
    z_breaks: Sequence[float],
    *,
    close_holes: bool = True,
    weld_threshold: float = 0.0005,
) -> List[Tuple[int, Optional[trimesh.Trimesh]]]:
    """Return a list of (floor_index, submesh) pairs for each z band."""
    values = list(z_breaks)
    if len(values) < 2:
        msg = "Need at least two z break values"
        raise ValueError(msg)

    mesh = mesh.copy()
    if weld_threshold and weld_threshold > 0:
        mesh.merge_vertices(weld_threshold)

    floors: List[Tuple[int, Optional[trimesh.Trimesh]]] = []
    for index in range(len(values) - 1):
        zmin, zmax = values[index], values[index + 1]
        face_mask = _select_faces_by_band(mesh, zmin, zmax)
        if not face_mask.any():
            floors.append((index + 1, None))
            continue

        submesh = mesh.submesh([np.where(face_mask)[0]], append=True, repair=True)
        if isinstance(submesh, list):
            submesh = submesh[0]

        if submesh is None or submesh.faces.size == 0:
            floors.append((index + 1, None))
            continue

        if close_holes:
            try:
                submesh = submesh.copy()
                submesh.remove_unreferenced_vertices()
                submesh.fill_holes()
                submesh.process(validate=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] Floor {index + 1}: fill_holes failed: {exc}")

        floors.append((index + 1, submesh))

    return floors


def export_stls(floors: Iterable[Tuple[int, Optional[trimesh.Trimesh]]], outdir: str) -> list[str]:
    os.makedirs(outdir, exist_ok=True)
    exported: list[str] = []
    for idx, submesh in floors:
        if submesh is None or submesh.faces.size == 0:
            print(f"[info] Floor {idx}: empty (no faces in this band). Skipping.")
            continue
        path = os.path.join(outdir, f"floor_{idx:02d}.stl")
        submesh.export(path)
        print(f"[ok] Wrote {path}")
        exported.append(path)
    return exported


def export_assembled(floors: Iterable[Tuple[int, Optional[trimesh.Trimesh]]], outpath: str) -> Optional[str]:
    parts = [sub for _, sub in floors if sub is not None and sub.faces.size > 0]
    if not parts:
        print("[info] No parts to assemble.")
        return None
    scene = trimesh.util.concatenate(parts)
    scene.export(outpath)
    print(f"[ok] Wrote {outpath}")
    return outpath


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", required=True, help="Path to OBJ/PLY/GLB/FBX etc.")
    parser.add_argument("--config", required=True, help="YAML with floor_breaks_z etc.")
    parser.add_argument("--outdir", default="outputs")
    args = parser.parse_args()

    config = load_config(args.config)
    z_breaks = config.get("floor_breaks_z")
    if not z_breaks or len(z_breaks) < 2:
        print("ERROR: configs/floors.yaml must define at least two values under floor_breaks_z.")
        sys.exit(2)

    close_holes = bool(config.get("close_holes", True))
    weld_threshold = float(config.get("weld_threshold", 0.0005))
    export_assembled_flag = bool(config.get("export_assembled", True))

    print(f"[load] {args.mesh}")
    mesh = trimesh.load(args.mesh, force="mesh")
    if mesh is None or mesh.faces.size == 0:
        print("ERROR: Could not load a valid mesh from:", args.mesh)
        sys.exit(2)

    print(f"[slice] z breaks: {z_breaks}")
    floors = slice_by_zbands(
        mesh,
        z_breaks,
        close_holes=close_holes,
        weld_threshold=weld_threshold,
    )
    export_stls(floors, args.outdir)

    if export_assembled_flag:
        export_assembled(floors, os.path.join(args.outdir, "assembled.stl"))

    print("[done] Floor slicing complete.")


if __name__ == "__main__":
    main()
'''

BLENDER_EXPLODER = '''#!/usr/bin/env python3
"""Blender 4.x: Explode stacked floor STLs and export GLB."""

import argparse
import os
import sys
from pathlib import Path

import bpy


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", default="outputs")
    parser.add_argument("--explode", type=float, default=0.2)
    parser.add_argument("--export", default="outputs/house_exploded.glb")
    return parser.parse_args(argv)


def import_stls(indir: Path) -> list[object]:
    stls = sorted(
        file for file in indir.iterdir() if file.suffix.lower() == ".stl" and file.name.lower().startswith("floor_")
    )
    imported = []
    for path in stls:
        bpy.ops.import_mesh.stl(filepath=str(path))
        obj = bpy.context.selected_objects[0]
        obj.name = path.stem
        imported.append(obj)
    return imported


def explode(objs: list[object], dz: float) -> None:
    height = 0.0
    for obj in objs:
        obj.location.z = height
        height += dz


def main(argv: list[str]) -> None:
    args = parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.world.use_nodes = True

    indir = Path(args.indir)
    if not indir.exists():
        print(f"No such directory: {indir}")
        return

    objects = import_stls(indir)
    if not objects:
        print(f"No floor_*.stl files found in {indir}")
        return

    explode(objects, args.explode)
    export_path = Path(args.export)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(export_path), export_apply=True)
    print(f"Exported {export_path}")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
'''

RUN_PIPELINE_BAT = r"""@echo off
REM === Auto3D Render → 3D Mesh → Floor STLs ===
setlocal enabledelayedexpansion

REM Adjust Python and Blender paths if needed
set VENV_DIR=.venv
set PYTHON=.%VENV_DIR%\Scripts\python.exe

if not exist %VENV_DIR% (
    py -3 -m venv %VENV_DIR%
)
call .%VENV_DIR%\Scripts\activate

pip install -U pip wheel
pip install trimesh shapely numpy pyyaml

echo.
echo [1/3] Expecting mesh at working\house_mesh.obj (generate via TripoSR or Meshroom)
if not exist working\house_mesh.obj (
    echo MESH NOT FOUND. Please run TripoSR or Meshroom to create working\house_mesh.obj
    echo See scripts\1_notes_triposr.md
    goto :eof
)

echo.
echo [2/3] Slicing floors per configs\floors.yaml
%PYTHON% scripts\2_slice_mesh_to_floors.py --mesh "working\house_mesh.obj" --config "configs\floors.yaml" --outdir "outputs"

echo.
echo [3/3] Optional: Exploded view via Blender (edit paths in this .bat if you want)
echo Done.
"""

AUTO_CLEANUP = '''# ------------------------------------------------------------
# Auto Cleanup for TripoSR meshes
# Use inside Blender 4.x
# ------------------------------------------------------------
import bpy
import bmesh

# --------- CONFIG ---------
FLOOR_Z_SNAPS = [0.0, 3.0, 6.0]   # example floor break planes in mesh units
SOLID_THICKNESS = 0.8             # mm or mesh-units
MERGE_DISTANCE = 0.001            # weld threshold
# --------------------------

def select_object(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def merge_by_distance(obj, dist):
    select_object(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=dist)
    bpy.ops.object.mode_set(mode='OBJECT')

def fill_holes(obj):
    select_object(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.object.mode_set(mode='OBJECT')

def flatten_to_planes(obj, planes):
    select_object(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    for z in planes:
        for vert in bm.verts:
            if abs(vert.co.z - z) < 0.05:
                vert.co.z = z
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')

def add_solidify(obj, thickness):
    select_object(obj)
    modifier = obj.modifiers.new(name="SolidifyWalls", type='SOLIDIFY')
    modifier.thickness = thickness
    bpy.ops.object.modifier_apply(modifier=modifier.name)

def main():
    obj = bpy.context.active_object
    if obj is None or obj.type != 'MESH':
        print("Select a mesh object first.")
        return

    print("Starting cleanup for", obj.name)
    merge_by_distance(obj, MERGE_DISTANCE)
    fill_holes(obj)
    flatten_to_planes(obj, FLOOR_Z_SNAPS)
    add_solidify(obj, SOLID_THICKNESS)

    bpy.ops.mesh.print3d_check_all()
    print("Cleanup complete. Save or export your mesh.")

if __name__ == '__main__':
    main()
'''


@dataclass
class FileSpec:
    relative_path: Path
    content: str
    executable: bool = False


FILES: Dict[str, FileSpec] = {
    "README.md": FileSpec(Path("README.md"), README_CONTENT),
    "configs/floors.yaml": FileSpec(Path("configs/floors.yaml"), FLOORS_YAML),
    "scripts/1_notes_triposr.md": FileSpec(Path("scripts/1_notes_triposr.md"), TRIPOSR_NOTES),
    "scripts/2_slice_mesh_to_floors.py": FileSpec(Path("scripts/2_slice_mesh_to_floors.py"), SLICE_SCRIPT, True),
    "scripts/3_blender_floor_exploder.py": FileSpec(Path("scripts/3_blender_floor_exploder.py"), BLENDER_EXPLODER, True),
    "scripts/run_pipeline.bat": FileSpec(Path("scripts/run_pipeline.bat"), RUN_PIPELINE_BAT),
    "scripts/auto_cleanup.py": FileSpec(Path("scripts/auto_cleanup.py"), AUTO_CLEANUP),
}


SUBDIRS = [
    Path("input_images"),
    Path("working"),
    Path("outputs"),
    Path("scripts"),
    Path("configs"),
]


def write_file(base: Path, spec: FileSpec, *, force: bool) -> bool:
    path = base / spec.relative_path
    if path.exists() and not force:
        print(f"[skip] {path} already exists (use --force to overwrite)")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(spec.content, encoding="utf-8")
    if spec.executable:
        path.chmod(path.stat().st_mode | 0o111)
    print(f"[write] {path}")
    return True


def ensure_structure(base: Path) -> None:
    for directory in SUBDIRS:
        target = base / directory
        target.mkdir(parents=True, exist_ok=True)
        print(f"[dir] {target}")


def create_project(base: Path, *, force: bool) -> None:
    ensure_structure(base)
    for spec in FILES.values():
        write_file(base, spec, force=force)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the Auto3D-Render-to-STL workspace")
    parser.add_argument(
        "directory",
        nargs="?",
        default="Auto3D-Render-to-STL",
        help="Target directory for the workspace (default: Auto3D-Render-to-STL)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files if they already exist",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base = Path(args.directory).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    print(f"[base] {base}")
    create_project(base, force=args.force)
    print("[done] Auto3D workspace ready.")


if __name__ == "__main__":
    main()
