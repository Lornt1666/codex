# RenderToRealityApp

Drag-and-drop AI render to mesh pipeline with depth estimation, analysis, and OpenAI integration.

## Features

- **Depth Map Generation**: Converts 2D renders to depth maps using MiDaS (with fallback)
- **Mesh Export**: Generates 3D meshes (STL/OBJ) via Blender
- **Image Analysis**: Analyzes aspect ratios, edges, orientation, and depth statistics
- **Mesh Metrics**: Computes dimensions, volume, and triangle count
- **OpenAI Integration**: Optional AI-powered summaries and status updates
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

### Prerequisites

1. **Python 3.9+**
2. **Blender 3.6+** (download from [blender.org](https://www.blender.org/))

### Setup

```bash
# Clone or extract the project
cd RenderToRealityApp

# Install dependencies
pip install -r requirements.txt

# (Optional) Install PyTorch for better depth maps
# Visit https://pytorch.org/ and install for your platform
# Example for CPU-only:
pip install torch torchvision

# Copy and edit config
cp config.json.example config.json
# Edit config.json to set your Blender path and other settings
```

### Configuration

Edit `config.json`:

```json
{
    "brand": "Your Project Name",
    "blender_path": "/path/to/blender",  // Update this!
    "midas_model": "DPT_Hybrid",
    "use_gpu_if_available": true,
    "export_format": "stl",
    "openai_enabled": false,
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini"
}
```

**Platform-specific Blender paths:**
- Windows: `C:/Program Files/Blender Foundation/Blender 3.6/blender.exe`
- macOS: `/Applications/Blender.app/Contents/MacOS/Blender`
- Linux: `/usr/bin/blender` or `blender` if in PATH

## Usage

### GUI Mode

```bash
python main.py
```

Drag and drop PNG/JPG images into the window. The app will:
1. Generate a depth map
2. Analyze the image
3. Build a 3D mesh
4. Export to STL or OBJ

### Headless CLI Mode

```bash
python cli.py --input image.png --export-format stl --known-width-mm 100
```

Options:
- `--input`: Input image path (required)
- `--known-width-mm`: Known width in millimeters (optional, default: 0)
- `--export-format`: Export format, `stl` or `obj` (default: `stl`)

### OpenAI Integration

To enable AI-powered summaries:

1. Get an API key from [OpenAI](https://platform.openai.com/)
2. Edit `config.json`:
   ```json
   {
       "openai_enabled": true,
       "openai_api_key": "sk-...",
       "openai_model": "gpt-4o-mini"
   }
   ```
3. Use the "Generate Project Update" and summary buttons in the GUI

## Project Structure

```
RenderToRealityApp/
├── main.py                 # GUI application
├── cli.py                  # Headless CLI
├── scripts/
│   ├── ratio_analysis.py   # Image analysis
│   ├── mesh_metrics.py     # Mesh analysis
│   ├── openai_hooks.py     # OpenAI integration
│   └── depth_to_mesh.py    # Blender script
├── tests/                  # Unit tests
├── requirements.txt        # Dependencies
├── config.json.example     # Example config
└── README.md              # This file
```

## Testing

```bash
# Install pytest
pip install pytest

# Run tests
pytest tests/
```

## Output

Generated files are saved to:
- `output/depthmaps/` - Depth map images
- `output/meshes/` - OBJ meshes
- `output/stl/` - STL meshes
- `output/*.json` - Analysis results
- `logs/` - Application logs
- `logs/summaries.log` - AI summaries (if enabled)

## Troubleshooting

### "Blender not found"
- Check that `blender_path` in `config.json` points to the correct Blender executable
- On Linux/macOS, try the full path: `which blender`

### "PyQt6 not available"
- Install PyQt6: `pip install PyQt6`
- Or use headless mode: `python cli.py --input image.png`

### "torch not available"
- The app will use a fallback edge-based depth map
- For better results, install PyTorch from https://pytorch.org/

### "openai package not available"
- Install OpenAI package: `pip install openai`
- Or disable in config: `"openai_enabled": false`

## Dependencies

- **opencv-python**: Image processing
- **numpy**: Numerical operations
- **Pillow**: Image loading
- **trimesh**: Mesh analysis
- **PyQt6**: GUI (optional for headless)
- **openai**: AI integration (optional)
- **torch**: Deep learning depth maps (optional)

## License

See the repository LICENSE file.

## Credits

- MiDaS depth estimation: Intel ISL
- Blender: Blender Foundation
- OpenAI API: OpenAI
