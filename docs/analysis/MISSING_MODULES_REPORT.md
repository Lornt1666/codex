# Missing Modules Report - RenderToRealityApp

## Executive Summary

This report identifies **missing Python modules** in the RenderToRealityApp project. There are two types of issues:

1. **Missing import statements** in source code files
2. **Missing third-party packages** that need to be installed

---

## 1. Missing Import Statements in Code Files

### Problem: `scripts/ratio_analysis.py`

The code fragment shown in the problem statement is **missing ALL import statements** at the beginning of the file. The code uses several modules but doesn't import them.

#### Modules Used But Not Imported:
- `cv2` - OpenCV for image processing
- `numpy` (as `np`) - Numerical operations
- `math` - Mathematical functions
- `pathlib.Path` - File path handling

#### Solution - Add These Imports:

```python
import cv2
import numpy as np
import math
from pathlib import Path
```

#### Complete Fixed Code:

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

## 2. Missing Third-Party Packages

### Problem: Required Packages Not Installed

The following third-party Python packages are required but not currently installed in the environment:

#### Required Packages (from requirements.txt):
1. ❌ **PyQt6** - GUI framework for the main application
2. ❌ **opencv-python** - Provides `cv2` module for computer vision
3. ❌ **numpy** - Numerical computing library
4. ❌ **Pillow** - Image processing library (provides `PIL`)
5. ❌ **trimesh** - 3D mesh processing
6. ❌ **openai** - OpenAI API client (optional feature)
7. ❌ **torch** - PyTorch for MiDaS depth estimation (optional)

#### Solution - Install Required Packages:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install PyQt6 opencv-python numpy Pillow trimesh openai torch
```

---

## 3. Module Usage by File

### Summary Table:

| File | Missing Imports | External Packages Used |
|------|----------------|----------------------|
| **scripts/ratio_analysis.py** | ✅ **YES - ALL MISSING** | cv2, numpy, math, pathlib |
| main.py | ✅ Complete | PyQt6, cv2, numpy, PIL, torch |
| scripts/depth_to_mesh.py | ✅ Complete | bpy (Blender) |
| scripts/mesh_metrics.py | ✅ Complete | trimesh |
| scripts/openai_hooks.py | ✅ Complete | openai |

---

## 4. Detailed Module Dependencies

### Standard Library (Built-in Python Modules):
These are always available and don't need installation:
- ✅ `os` - Operating system interfaces
- ✅ `sys` - System-specific parameters
- ✅ `json` - JSON encoding/decoding
- ✅ `threading` - Thread-based parallelism
- ✅ `subprocess` - Subprocess management
- ✅ `math` - Mathematical functions
- ✅ `pathlib` - Object-oriented filesystem paths
- ✅ `datetime` - Date and time handling

### Third-Party Packages (Need Installation):
These must be installed via pip:
- ❌ `PyQt6` → `pip install PyQt6`
- ❌ `cv2` → `pip install opencv-python`
- ❌ `numpy` → `pip install numpy`
- ❌ `PIL` → `pip install Pillow`
- ❌ `trimesh` → `pip install trimesh`
- ❌ `openai` → `pip install openai`
- ❌ `torch` → `pip install torch` (optional, for better depth maps)

### Special Requirements:
- **Blender** - The `bpy` module is only available when running scripts inside Blender. The `blender_path` in config.json must point to a valid Blender installation.

---

## 5. Quick Fix Guide

### Step 1: Fix Missing Imports in ratio_analysis.py

Add these lines at the top of `scripts/ratio_analysis.py`:

```python
import cv2
import numpy as np
import math
from pathlib import Path
```

### Step 2: Install Required Packages

```bash
# Install all required packages
pip install PyQt6 opencv-python numpy Pillow trimesh openai

# Optional: Install PyTorch for better depth maps
# Visit https://pytorch.org/ for platform-specific installation
pip install torch
```

### Step 3: Verify Installation

Run the module checker script:

```bash
python check_missing_modules.py
```

Expected output when all modules are installed:
```
✅ All required modules are available!
```

---

## 6. Root Cause Analysis

### Why Are Imports Missing?

The code fragment in the problem statement appears to be an **excerpt** from the middle of a file, showing only the function implementation without the import statements that should be at the top of the file.

**This is likely due to:**
1. Copy-paste error - imports were left out when copying code
2. Incomplete code example - showing only the relevant function logic
3. Code refactoring - imports were accidentally removed

### Impact:

Without the import statements:
- ❌ Python will raise `NameError: name 'cv2' is not defined`
- ❌ Python will raise `NameError: name 'np' is not defined`
- ❌ Python will raise `NameError: name 'math' is not defined`
- ❌ Python will raise `NameError: name 'Path' is not defined`

---

## 7. Verification Commands

After fixing the imports and installing packages, verify the setup:

```bash
# Check if all imports work
python3 -c "import cv2, numpy as np, math; from pathlib import Path; print('✅ All imports successful')"

# Check if PyQt6 is available
python3 -c "from PyQt6 import QtWidgets; print('✅ PyQt6 available')"

# Check if other modules are available
python3 -c "import trimesh, openai; from PIL import Image; print('✅ All third-party modules available')"

# Run the full module checker
python3 check_missing_modules.py
```

---

## Conclusion

**The missing modules are:**

1. **Import statements** missing from `scripts/ratio_analysis.py`:
   - `import cv2`
   - `import numpy as np`
   - `import math`
   - `from pathlib import Path`

2. **Third-party packages** not installed (need `pip install`):
   - PyQt6
   - opencv-python
   - numpy
   - Pillow
   - trimesh
   - openai (optional)
   - torch (optional)

**Fix**: Add the import statements to the file and run `pip install -r requirements.txt` to install all required packages.
