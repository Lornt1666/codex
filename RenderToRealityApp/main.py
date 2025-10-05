"""RenderToRealityApp - Drag-and-drop AI render to mesh pipeline."""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from datetime import datetime

# Check for PyQt6
try:
    from PyQt6 import QtWidgets, QtGui, QtCore
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("Warning: PyQt6 not available. GUI will not work.")

# Check for OpenCV
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: opencv-python not available. Image processing disabled.")

# Check for PIL
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow not available. Image processing disabled.")

# Optional: real depth via MiDaS
try:
    import torch
    TORCH_OK = True
except Exception:
    TORCH_OK = False

from scripts import ratio_analysis, mesh_metrics, openai_hooks

APP_ROOT = Path(__file__).resolve().parent
SCRIPTS = APP_ROOT / "scripts"
OUTPUT = APP_ROOT / "output"
DEPTH = OUTPUT / "depthmaps"
MESHES = OUTPUT / "meshes"
STL = OUTPUT / "stl"
LOGS = APP_ROOT / "logs"
SUMMARIES_LOG = LOGS / "summaries.log"

for p in (DEPTH, MESHES, STL, LOGS):
    p.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = APP_ROOT / "config.json"
DEFAULT_CFG = {
    "brand": "Render-to-Reality | 1JGM∞.BE",
    "blender_path": "C:/Program Files/Blender Foundation/Blender 3.6/blender.exe",
    "midas_model": "DPT_Hybrid",
    "use_gpu_if_available": True,
    "export_format": "stl",
    "known_scale_mm": 0.0,
    "openai_enabled": False,
    "openai_model": "gpt-4o-mini",
    "openai_api_key": "",
    "summary_tone": "technical"
}


def load_cfg():
    """Load configuration from file or create default."""
    if CONFIG_FILE.exists():
        try:
            return {**DEFAULT_CFG, **json.loads(CONFIG_FILE.read_text(encoding='utf-8'))}
        except Exception:
            pass
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CFG, indent=4), encoding='utf-8')
    return DEFAULT_CFG.copy()


CFG = load_cfg()


def log(msg: str):
    """Log a message with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOGS / "run.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def open_path(path):
    """Open a file or directory in the system's default application (cross-platform)."""
    if os.name == 'nt':  # Windows
        os.startfile(str(path))
    elif sys.platform == 'darwin':  # macOS
        subprocess.call(['open', str(path)])
    else:  # Linux and other Unix-like
        subprocess.call(['xdg-open', str(path)])


# ----------------- MiDaS Depth -----------------
class MidasDepth:
    """MiDaS depth estimation with fallback."""
    
    def __init__(self):
        self.model = None
        self.transform = None
        self.device = "cuda" if (CFG["use_gpu_if_available"] and TORCH_OK and torch.cuda.is_available()) else "cpu"
        if TORCH_OK:
            self._load()

    def _load(self):
        """Load MiDaS model."""
        try:
            log(f"Loading MiDaS ({CFG['midas_model']}) …")
            self.model = torch.hub.load("intel-isl/MiDaS", CFG["midas_model"])
            transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            self.transform = transforms.dpt_transform if "DPT" in CFG["midas_model"] else transforms.small_transform
            self.model.to(self.device).eval()
            log("MiDaS loaded.")
        except Exception as e:
            log(f"MiDaS load failed → {e}")
            self.model = None

    def gen_depth(self, img_path: Path, out_path: Path) -> bool:
        """Generate depth map from image."""
        if not CV2_AVAILABLE:
            log("OpenCV not available, cannot generate depth map")
            return False
            
        if self.model is None:
            # Fallback: simple edge-inversion depth
            img = cv2.imread(str(img_path))
            if img is None:
                log(f"Failed to read image: {img_path}")
                return False
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            depth = cv2.normalize(255 - edges, None, 0, 255, cv2.NORM_MINMAX)
            cv2.imwrite(str(out_path), depth)
            log(f"Fallback depth saved → {out_path}")
            return True

        try:
            if not PIL_AVAILABLE:
                log("Pillow not available for MiDaS")
                return False
                
            pil = Image.open(str(img_path)).convert("RGB")
            inp = self.transform(pil).unsqueeze(0)
            inp = inp.to(self.device)
            with torch.no_grad():
                pred = self.model(inp)
                pred = torch.nn.functional.interpolate(
                    pred.unsqueeze(1),
                    size=pil.size[::-1],
                    mode="bicubic",
                    align_corners=False
                ).squeeze().cpu().numpy()
            mn, mx = float(np.min(pred)), float(np.max(pred))
            norm = (pred - mn) / (mx - mn + 1e-9)
            depth = (norm * 255).astype("uint8")
            cv2.imwrite(str(out_path), depth)
            log(f"Depth saved → {out_path}")
            return True
        except Exception as e:
            log(f"Depth error: {e}")
            return False


# ----------------- Blender mesh build -----------------
def build_mesh(depth_png: Path, export_dir: Path, export_fmt: str):
    """Build mesh from depth map using Blender."""
    blender = Path(CFG["blender_path"])
    if not blender.exists():
        return False, f"Blender not found at {blender}. Edit config.json."
    export_dir.mkdir(parents=True, exist_ok=True)
    out_file = export_dir / f"{depth_png.stem}.{export_fmt.lower()}"
    cmd = [
        str(blender), "-b",
        "-P", str(SCRIPTS / "depth_to_mesh.py"),
        "--", str(depth_png), str(out_file)
    ]
    log(f"Blender cmd: {' '.join(cmd)}")
    run = subprocess.run(cmd, capture_output=True, text=True)
    if run.stdout:
        log("Blender stdout:\n" + run.stdout)
    if run.returncode != 0:
        if run.stderr:
            log("Blender stderr:\n" + run.stderr)
        return False, "Blender failed."
    log(f"Mesh exported → {out_file}")
    return True, str(out_file)


# ----------------- GUI -----------------
if PYQT_AVAILABLE:
    class DropLabel(QtWidgets.QLabel):
        """Drag-and-drop label for images."""
        fileDropped = QtCore.pyqtSignal(str)
        
        def __init__(self):
            super().__init__()
            self.setAcceptDrops(True)
            self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.setText("\nDrop Render Here\n(PNG / JPG)\n")
            self.setStyleSheet("QLabel{border:4px dashed #666; color:#ddd; font-size:16px; padding:24px;}")

        def dragEnterEvent(self, e):
            if e.mimeData().hasUrls():
                e.acceptProposedAction()

        def dropEvent(self, e):
            for url in e.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.fileDropped.emit(path)
            e.acceptProposedAction()

    class App(QtWidgets.QWidget):
        """Main application window."""
        
        def __init__(self):
            super().__init__()
            self.setWindowTitle(CFG["brand"])
            self.resize(1024, 720)
            self.midas = MidasDepth()

            layout = QtWidgets.QVBoxLayout(self)

            # Top row
            top = QtWidgets.QHBoxLayout()
            layout.addLayout(top)

            self.btn_open = QtWidgets.QPushButton("Open Output Folder")
            self.btn_open.clicked.connect(lambda: open_path(OUTPUT))
            top.addWidget(self.btn_open)

            self.btn_settings = QtWidgets.QPushButton("Edit Settings")
            self.btn_settings.clicked.connect(lambda: open_path(CONFIG_FILE))
            top.addWidget(self.btn_settings)

            if CFG.get("openai_enabled") and CFG.get("openai_api_key"):
                openai_hooks.init(CFG["openai_api_key"], CFG.get("openai_model", "gpt-4o-mini"))
                self.btn_ai = QtWidgets.QPushButton("Generate Project Update")
                self.btn_ai.clicked.connect(self.ai_update)
                top.addWidget(self.btn_ai)

                self.btn_show_summary = QtWidgets.QPushButton("Show Latest Summary")
                self.btn_show_summary.clicked.connect(self.show_latest_summary)
                top.addWidget(self.btn_show_summary)

                self.btn_open_summaries = QtWidgets.QPushButton("Open Summaries Log")
                self.btn_open_summaries.clicked.connect(self.open_summaries_log)
                top.addWidget(self.btn_open_summaries)

            top.addStretch(1)

            # Middle split
            split = QtWidgets.QHBoxLayout()
            layout.addLayout(split, 1)

            self.drop = DropLabel()
            self.drop.fileDropped.connect(self.process_image)
            split.addWidget(self.drop, 2)

            right = QtWidgets.QVBoxLayout()
            split.addLayout(right, 1)

            right.addWidget(QtWidgets.QLabel("Known width (mm, optional):"))
            self.scale_edit = QtWidgets.QLineEdit(str(CFG.get("known_scale_mm", 0.0)))
            self.scale_edit.setPlaceholderText("0 = unknown / auto")
            right.addWidget(self.scale_edit)

            right.addWidget(QtWidgets.QLabel("Export format (stl / obj):"))
            self.format_edit = QtWidgets.QLineEdit(CFG.get("export_format", "stl"))
            right.addWidget(self.format_edit)

            self.btn_mesh_latest = QtWidgets.QPushButton("Mesh Latest Depth")
            self.btn_mesh_latest.clicked.connect(self.mesh_latest)
            right.addWidget(self.btn_mesh_latest)
            right.addStretch(1)

            # Logs
            self.log_view = QtWidgets.QTextEdit()
            self.log_view.setReadOnly(True)
            layout.addWidget(self.log_view, 1)

            self.status = QtWidgets.QLabel("Ready.")
            layout.addWidget(self.status)

            # Log tailer
            self._log_pos = 0
            timer = QtCore.QTimer(self)
            timer.timeout.connect(self._flush_log)
            timer.start(500)

            log("App started.")

        def _flush_log(self):
            """Flush new log entries to the GUI."""
            f = LOGS / "run.log"
            if f.exists():
                text = f.read_text(encoding='utf-8')
                if len(text) > self._log_pos:
                    self.log_view.insertPlainText(text[self._log_pos:])
                    self._log_pos = len(text)
                    self.log_view.moveCursor(QtGui.QTextCursor.MoveOperation.End)

        def process_image(self, path: str):
            """Process an image in a background thread."""
            threading.Thread(target=self._thread_process, args=(path,), daemon=True).start()

        def _thread_process(self, path: str):
            """Background thread for image processing."""
            try:
                self.status.setText("Processing…")
                img_path = Path(path)
                depth_png = DEPTH / f"{img_path.stem}_depth.png"

                # persist known scale
                try:
                    k = float(self.scale_edit.text().strip() or "0")
                except Exception:
                    k = 0.0
                CFG["known_scale_mm"] = k
                CONFIG_FILE.write_text(json.dumps(CFG, indent=4), encoding='utf-8')

                if not self.midas.gen_depth(img_path, depth_png):
                    self.status.setText("Depth failed.")
                    return

                analysis = ratio_analysis.analyze_image(str(img_path), str(depth_png), known_width_mm=k)
                (OUTPUT / f"{img_path.stem}_analysis.json").write_text(json.dumps(analysis, indent=2), encoding='utf-8')
                log("Analysis:\n" + json.dumps(analysis, indent=2))

                fmt = (self.format_edit.text().strip() or CFG["export_format"]).lower()
                ok, result = build_mesh(depth_png, STL if fmt == "stl" else MESHES, fmt)
                if not ok:
                    self.status.setText("Mesh failed.")
                    log(f"Mesh error: {result}")
                    return

                metrics = mesh_metrics.analyze_stl(result)
                log("Mesh metrics:\n" + json.dumps(metrics, indent=2))

                # Optional AI summary
                if CFG.get("openai_enabled") and CFG.get("openai_api_key"):
                    tone = CFG.get("summary_tone", "technical")
                    try:
                        summary = openai_hooks.summarize_mesh_report({"project": CFG["brand"], **metrics}, tone=tone)
                        log("AI Mesh Summary:\n" + summary)
                        with open(SUMMARIES_LOG, "a", encoding="utf-8") as sf:
                            sf.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Mesh Summary for {Path(result).name}\n{summary}\n{'-'*60}\n")
                    except Exception as e:
                        log(f"AI mesh summary error: {e}")

                self.status.setText("Done.")
            except Exception as e:
                log(f"Error: {e}")
                self.status.setText("Error.")

        def mesh_latest(self):
            """Build mesh from the latest depth map."""
            depths = sorted(DEPTH.glob("*_depth.png"), key=lambda p: p.stat().st_mtime)
            if not depths:
                QtWidgets.QMessageBox.information(self, "No depths", "Drop an image first.")
                return
            fmt = (self.format_edit.text().strip() or CFG["export_format"]).lower()
            ok, result = build_mesh(depths[-1], STL if fmt == "stl" else MESHES, fmt)
            if ok:
                log(f"Mesh built: {result}")
                QtWidgets.QMessageBox.information(self, "Mesh", f"Built: {result}")
            else:
                QtWidgets.QMessageBox.warning(self, "Mesh failed", result)

        def ai_update(self):
            """Generate an AI project update."""
            try:
                tone = CFG.get("summary_tone", "technical")
                txt = openai_hooks.gen_status(
                    CFG["brand"],
                    completed=["Depth generation", "Mesh export"],
                    upcoming=["Slicer preview"],
                    risks=["GPU memory pressure on large inputs"],
                    tone=tone
                )
                log("AI Project Update:\n" + txt)
                QtWidgets.QMessageBox.information(self, "Project Update", txt)
            except Exception as e:
                log(f"AI update error: {e}")
                QtWidgets.QMessageBox.warning(self, "AI error", str(e))

        def show_latest_summary(self):
            """Show the latest AI summary."""
            if SUMMARIES_LOG.exists():
                text = SUMMARIES_LOG.read_text(encoding='utf-8').strip()
                if not text:
                    QtWidgets.QMessageBox.information(self, "No summary", "No summaries archived yet.")
                    return
                # last block before the final separator
                parts = [blk.strip() for blk in text.split("-" * 60) if blk.strip()]
                QtWidgets.QMessageBox.information(self, "Latest AI Summary", parts[-1] if parts else "No entries.")
            else:
                QtWidgets.QMessageBox.information(self, "No summary", "No summaries.log yet.")

        def open_summaries_log(self):
            """Open the summaries log file."""
            if SUMMARIES_LOG.exists():
                open_path(SUMMARIES_LOG)
            else:
                QtWidgets.QMessageBox.information(self, "No summaries", "No summaries.log yet.")


def main():
    """Main entry point."""
    if not PYQT_AVAILABLE:
        print("Error: PyQt6 is required to run the GUI.")
        print("Install with: pip install PyQt6")
        print("For headless operation, use cli.py instead.")
        sys.exit(1)
    
    app = QtWidgets.QApplication(sys.argv)
    w = App()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
