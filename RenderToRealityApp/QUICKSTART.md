# RenderToRealityApp Quick Start

## 5-Minute Setup

### 1. Install Python Dependencies

```bash
cd RenderToRealityApp
pip install -r requirements.txt
```

**Note:** You can skip PyQt6 if you only need headless mode:
```bash
pip install opencv-python numpy Pillow trimesh
```

### 2. Configure Blender Path

```bash
cp config.json.example config.json
```

Edit `config.json` and set your Blender path:

**Windows:**
```json
{
    "blender_path": "C:/Program Files/Blender Foundation/Blender 3.6/blender.exe"
}
```

**macOS:**
```json
{
    "blender_path": "/Applications/Blender.app/Contents/MacOS/Blender"
}
```

**Linux:**
```json
{
    "blender_path": "/usr/bin/blender"
}
```

### 3. Test the Installation

#### Headless Mode (No GUI)

```bash
# Create a test image
python -c "from PIL import Image; import numpy as np; arr = np.zeros((200, 300, 3), dtype='uint8'); arr[50:150, 100:200] = 255; Image.fromarray(arr).save('test.png')"

# Run the pipeline (without Blender, just depth + analysis)
python -c "from main import MidasDepth; from pathlib import Path; md = MidasDepth(); md.gen_depth(Path('test.png'), Path('test_depth.png'))"

# Check the result
ls -l test_depth.png

# Clean up
rm test.png test_depth.png
```

#### GUI Mode

```bash
python main.py
```

Then drag and drop an image file into the window.

## What Works Without Optional Dependencies

| Feature | Required Packages | Optional Packages |
|---------|------------------|-------------------|
| Image Analysis | opencv-python, numpy | - |
| Depth Map (Fallback) | opencv-python, numpy | torch, torchvision (for MiDaS) |
| Mesh Analysis | trimesh | - |
| GUI | PyQt6 | - |
| OpenAI Summaries | openai | - |
| Mesh Generation | **Blender** (external) | - |

## Common Issues

### "PyQt6 not available"
- **Solution**: Install PyQt6 with `pip install PyQt6` or use headless mode with `cli.py`

### "Blender not found"
- **Solution**: Edit `config.json` and set the correct path to your Blender executable
- **Find Blender path**: 
  - Linux/macOS: `which blender`
  - Windows: Usually in `C:\Program Files\Blender Foundation\Blender 3.x\`

### "torch not available"
- **Solution**: The app uses a fallback edge-based depth map. For better results, install PyTorch from https://pytorch.org/
- The fallback mode works fine for most use cases

## Next Steps

1. **Read the full README**: See [README.md](README.md) for complete documentation
2. **Run tests**: `pytest tests/` to verify everything works
3. **Try the CLI**: `python cli.py --input yourimage.png --export-format stl`
4. **Enable OpenAI**: Edit `config.json` to add your API key for AI summaries

## Architecture Overview

```
┌─────────────┐
│  Image.png  │
└──────┬──────┘
       │
       v
┌──────────────────┐      ┌──────────────┐
│  Depth Map Gen   │─────>│  depth.png   │
│  (MiDaS/Fallback)│      └──────┬───────┘
└──────────────────┘             │
                                 │
       ┌─────────────────────────┴─────────────┐
       │                                       │
       v                                       v
┌─────────────┐                      ┌─────────────────┐
│  Analysis   │                      │  Blender Script │
│  (Ratios,   │                      │  (Depth -> Mesh)│
│   Stats)    │                      └────────┬────────┘
└──────┬──────┘                               │
       │                                      v
       │                              ┌──────────────┐
       │                              │  output.stl  │
       │                              └──────┬───────┘
       │                                     │
       v                                     v
┌──────────────────┐              ┌─────────────────┐
│  analysis.json   │              │  Mesh Metrics   │
└──────────────────┘              │  (Size, Volume) │
                                  └─────────────────┘
```

## Philosophy

This app is designed to work with **minimal dependencies** and **graceful degradation**:
- No PyQt6? Use the CLI
- No torch? Use edge-based fallback
- No OpenAI? Skip the summaries
- No Blender? Skip mesh generation (or configure it later)

Start simple, add complexity as needed.
