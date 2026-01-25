"""Image and depth analysis module."""
import cv2
import numpy as np
import math
from pathlib import Path


def analyze_image(render_path, depth_path=None, known_width_mm=0.0):
    """Analyze an image for aspect ratio, edges, orientation, and depth statistics."""
    img = cv2.imread(render_path)
    if img is None:
        return {"error": "image not found", "file": Path(render_path).name}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    aspect = (w / h) if h else None

    # Edge/line analysis
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=90, minLineLength=40, maxLineGap=12)

    angles = []
    if lines is not None:
        for l in lines:
            x1, y1, x2, y2 = l[0]
            ang = math.degrees(math.atan2((y2 - y1), (x2 - x1)))
            angles.append(ang)

    dominant_angle = None
    if angles:
        hist, bins = np.histogram(angles, bins=36)  # 5-degree bins
        i = int(np.argmax(hist))
        dominant_angle = float((bins[i] + bins[i+1]) / 2.0)

    orientation = "unknown"
    if dominant_angle is not None:
        a = ((dominant_angle + 180) % 180) - 90
        if abs(a) < 15:
            orientation = "mostly-horizontal"
        elif abs(a) > 75:
            orientation = "mostly-vertical"
        else:
            orientation = "angled"

    depth_stats = None
    if depth_path:
        d = cv2.imread(depth_path, cv2.IMREAD_UNCHANGED)
        if d is not None:
            if len(d.shape) == 3:
                d = cv2.cvtColor(d, cv2.COLOR_BGR2GRAY)
            nz = d[d > 0]
            if nz.size > 0:
                depth_stats = {
                    "min": int(nz.min()),
                    "max": int(nz.max()),
                    "mean": float(nz.mean()),
                    "coverage_pct": float(nz.size) / float(d.size) * 100.0
                }

    # Optional physical estimate if user supplies known width
    mm_per_px = None
    est_width_mm, est_height_mm = None, None
    if known_width_mm and w > 0:
        mm_per_px = known_width_mm / float(w)
        est_width_mm = float(known_width_mm)
        est_height_mm = float(h) * mm_per_px

    return {
        "file": Path(render_path).name,
        "width_px": int(w),
        "height_px": int(h),
        "aspect_ratio": float(aspect) if aspect else None,
        "dominant_angle_deg": float(dominant_angle) if dominant_angle is not None else None,
        "orientation_guess": orientation,
        "lines_detected": int(len(angles)),
        "depth_stats": depth_stats,
        "known_width_mm": float(known_width_mm),
        "mm_per_px": float(mm_per_px) if mm_per_px else None,
        "est_width_mm": float(est_width_mm) if est_width_mm else None,
        "est_height_mm": float(est_height_mm) if est_height_mm else None
    }
