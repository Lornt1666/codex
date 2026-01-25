# Solution Summary: Missing Modules Found ✅

## The Problem

The RenderToRealityApp project code shown in the problem statement has **missing Python import statements** in `scripts/ratio_analysis.py`.

---

## The Answer: Missing Modules

### 🔴 Missing Import Statements

The file `scripts/ratio_analysis.py` is missing these four import statements:

```python
import cv2
import numpy as np
import math
from pathlib import Path
```

### 🔴 Missing Third-Party Packages

These packages need to be installed via pip:

| Package | Purpose | Install Command |
|---------|---------|----------------|
| PyQt6 | GUI framework | `pip install PyQt6` |
| opencv-python | Computer vision (cv2) | `pip install opencv-python` |
| numpy | Numerical computing | `pip install numpy` |
| Pillow | Image processing (PIL) | `pip install Pillow` |
| trimesh | 3D mesh processing | `pip install trimesh` |
| openai | OpenAI API client | `pip install openai` |
| torch | PyTorch (optional) | `pip install torch` |

---

## The Fix

### Option 1: Fix the Code File

**Add these lines at the top of `scripts/ratio_analysis.py`:**

```python
import cv2
import numpy as np
import math
from pathlib import Path

def analyze_image(render_path, depth_path=None, known_width_mm=0.0):
    # ... rest of the code
```

### Option 2: Install Missing Packages

**Run this command:**

```bash
pip install -r requirements.txt
```

**Or install individually:**

```bash
pip install PyQt6 opencv-python numpy Pillow trimesh openai torch
```

---

## Verification

### Step 1: Test Imports
```bash
python3 -c "import cv2, numpy as np, math; from pathlib import Path; print('✅ Imports work!')"
```

### Step 2: Run Module Checker
```bash
python3 docs/analysis/check_missing_modules.py
```

Expected output:
```
✅ All required modules are available!
```

---

## Why This Matters

### Without the imports, Python will crash with errors:

❌ `NameError: name 'cv2' is not defined`  
❌ `NameError: name 'np' is not defined`  
❌ `NameError: name 'math' is not defined`  
❌ `NameError: name 'Path' is not defined`

### With the imports added:

✅ Code will execute successfully  
✅ OpenCV functions (cv2) will work  
✅ NumPy operations (np) will work  
✅ Math functions will work  
✅ Path handling will work  

---

## Complete Fixed Code

```python
import cv2
import numpy as np
import math
from pathlib import Path

def analyze_image(render_path, depth_path=None, known_width_mm=0.0):
    img = cv2.imread(render_path)
    if img is None:
        return {"error": "image not found", "file": Path(render_path).name}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    aspect = (w / h) if h else None

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
        hist, bins = np.histogram(angles, bins=36)
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
```

---

## Summary Table

| File | Status | Missing Imports | Action Required |
|------|--------|----------------|-----------------|
| **scripts/ratio_analysis.py** | ❌ INCOMPLETE | cv2, numpy, math, Path | ✅ Add imports |
| main.py | ✅ COMPLETE | None | No action |
| scripts/depth_to_mesh.py | ✅ COMPLETE | None | No action |
| scripts/mesh_metrics.py | ✅ COMPLETE | None | No action |
| scripts/openai_hooks.py | ✅ COMPLETE | None | No action |

---

## Quick Reference

### Missing Modules List:
1. `cv2` - from opencv-python package
2. `numpy` (as np) - from numpy package
3. `math` - standard library
4. `Path` - from pathlib (standard library)

### Installation Command:
```bash
pip install opencv-python numpy
```

### Import Statements to Add:
```python
import cv2
import numpy as np
import math
from pathlib import Path
```

---

## Conclusion

✅ **Problem Identified:** Missing import statements in `scripts/ratio_analysis.py`  
✅ **Solution Provided:** Add 4 import lines at the top of the file  
✅ **Packages Required:** opencv-python, numpy (and others from requirements.txt)  
✅ **Verification:** Run `check_missing_modules.py` to confirm  

**The missing modules have been found and documented!** 🎉
