import sys
import argparse
from pathlib import Path
from scripts import ratio_analysis, mesh_metrics
import json

def main():
    parser = argparse.ArgumentParser(description="Render-to-Reality CLI: depth/mesh pipeline")
    parser.add_argument("image", help="Input PNG/JPG image")
    parser.add_argument("--depth", help="Output depthmap path", default=None)
    parser.add_argument("--analysis", help="Output analysis JSON path", default=None)
    parser.add_argument("--mesh", help="Output mesh path (STL/OBJ)", default=None)
    parser.add_argument("--known-width-mm", type=float, default=0.0, help="Known width in mm (optional)")
    args = parser.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"Image not found: {img_path}")
        sys.exit(1)

    # Depth fallback: edge-based
    import cv2
    img = cv2.imread(str(img_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    depth = cv2.normalize(255 - edges, None, 0, 255, cv2.NORM_MINMAX)
    depth_path = Path(args.depth) if args.depth else img_path.with_name(f"{img_path.stem}_depth.png")
    cv2.imwrite(str(depth_path), depth)
    print(f"Depth saved: {depth_path}")

    # Analysis
    analysis = ratio_analysis.analyze_image(str(img_path), str(depth_path), known_width_mm=args.known_width_mm)
    analysis_path = Path(args.analysis) if args.analysis else img_path.with_name(f"{img_path.stem}_analysis.json")
    analysis_path.write_text(json.dumps(analysis, indent=2), encoding='utf-8')
    print(f"Analysis saved: {analysis_path}")

    # Mesh (optional, only if --mesh given)
    if args.mesh:
        # This requires Blender and depth_to_mesh.py
        print("Mesh export via Blender not supported in CLI (requires Blender subprocess). Run via GUI or add Blender call.")

    # Mesh metrics (optional, only if mesh given)
    # if args.mesh:
    #     metrics = mesh_metrics.analyze_stl(args.mesh)
    #     print("Mesh metrics:", metrics)

if __name__ == "__main__":
    main()
