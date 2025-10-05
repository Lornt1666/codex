"""Headless CLI runner for RenderToRealityApp pipeline.

Usage:
  python cli.py --input image.png --export-format stl
"""
import argparse
from pathlib import Path
import json
from datetime import datetime
from scripts import ratio_analysis, mesh_metrics
from main import MidasDepth, build_mesh, APP_ROOT, DEPTH, STL, MESHES, CFG


def run_pipeline(input_path: Path, known_width_mm: float, export_format: str):
    depth_out = DEPTH / f"{input_path.stem}_depth.png"
    md = MidasDepth()
    ok = md.gen_depth(input_path, depth_out)
    if not ok:
        return False, "depth failed"

    analysis = ratio_analysis.analyze_image(str(input_path), str(depth_out), known_width_mm)
    out_analysis = APP_ROOT / f"output/{input_path.stem}_analysis.json"
    out_analysis.write_text(json.dumps(analysis, indent=2), encoding='utf-8')

    fmt = export_format.lower()
    ok, res = build_mesh(depth_out, STL if fmt == "stl" else MESHES, fmt)
    if not ok:
        return False, res

    metrics = mesh_metrics.analyze_stl(res)
    return True, {"mesh": res, "metrics": metrics}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="input image path")
    p.add_argument("--known-width-mm", type=float, default=0.0)
    p.add_argument("--export-format", default="stl")
    args = p.parse_args()

    inp = Path(args.input)
    ok, out = run_pipeline(inp, args.known_width_mm, args.export_format)
    if not ok:
        print("Pipeline failed:", out)
        raise SystemExit(2)
    print("Pipeline succeeded:", out)


if __name__ == "__main__":
    main()
