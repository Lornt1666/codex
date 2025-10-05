# Render-to-Reality

Windows desktop pipeline: drag-and-drop AI renders → depth map (MiDaS) → analysis → mesh → STL.
Optional GPT hooks for project updates + mesh summaries (archived).

Features
- Drag & drop PNG/JPG
- Depth (MiDaS via torch.hub; edge-based fallback)
- Ratio & orientation analysis (OpenCV)
- Mesh + STL via Blender
- Logs + archived AI summaries (`logs/summaries.log`)
- Optional OpenAI hooks (off by default)

Setup (Windows)
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
# (Optional) install torch per https://pytorch.org/ for better depth maps
python main.py
```

Packaging
```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "scripts;scripts" main.py
```

Notes
- Edit `config.json` to point to Blender on your machine.
