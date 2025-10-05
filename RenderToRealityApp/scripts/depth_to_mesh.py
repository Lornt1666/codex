import bpy
import sys
from pathlib import Path

argv = sys.argv
argv = argv[argv.index("--") + 1 :] if "--" in argv else []
if len(argv) < 2:
    print("Usage: blender -b -P depth_to_mesh.py -- <depth.png> <out.stl|out.obj>")
    sys.exit(1)

depth_png = Path(argv[0]).resolve()
out_path = Path(argv[1]).resolve()

# Reset scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Load depth image
img = bpy.data.images.load(str(depth_png))
w, h = img.size
xs = max(64, min(512, w // 4))
ys = max(64, min(512, h // 4))

# Create grid plane
bpy.ops.mesh.primitive_grid_add(x_subdivisions=xs, y_subdivisions=ys, size=1)
plane = bpy.context.active_object
plane.name = "DepthPlane"

# Create texture from image
tex = bpy.data.textures.new("DepthTex", type='IMAGE')
tex.image = img

# Displace
mod = plane.modifiers.new(name="Displace", type='DISPLACE')
mod.texture = tex
mod.strength = 0.6  # tune displacement strength per your scale

# Smooth & apply
bpy.ops.object.shade_smooth()
bpy.context.view_layer.update()
bpy.ops.object.modifier_apply(modifier=mod.name)

# Export
ext = out_path.suffix.lower()
if ext == ".stl":
    bpy.ops.export_mesh.stl(filepath=str(out_path))
else:
    bpy.ops.export_scene.obj(filepath=str(out_path), use_selection=True)

print("Exported:", out_path)
