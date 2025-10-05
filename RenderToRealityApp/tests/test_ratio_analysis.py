import tempfile
from pathlib import Path
from scripts import ratio_analysis
import numpy as np
from PIL import Image


def test_analyze_image_basic():
    # create a simple black image with a white rectangle to force edges
    tmp = tempfile.TemporaryDirectory()
    p = Path(tmp.name) / "test.png"
    arr = (np.zeros((200, 300, 3), dtype='uint8'))
    arr[50:150, 80:220] = 255
    Image.fromarray(arr).save(p)

    res = ratio_analysis.analyze_image(str(p), None, known_width_mm=0)
    assert res["file"] == p.name
    assert res["width_px"] == 300
    assert res["height_px"] == 200
