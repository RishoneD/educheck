"""
צילום מסך וטשטוש אזורים.
"""
import os
import tempfile

import PIL.ImageGrab
from PIL import Image, ImageFilter

BLUR_RADIUS = 14


def capture() -> Image.Image:
    return PIL.ImageGrab.grab()


def blur_regions(img: Image.Image, boxes: list[tuple]) -> Image.Image:
    """
    boxes: list of (x1, y1, x2, y2) בקואורדינטות מסך.
    """
    w, h   = img.size
    result = img.copy()
    for box in boxes:
        x1, y1, x2, y2 = (int(v) for v in box)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        crop    = result.crop((x1, y1, x2, y2))
        blurred = crop.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))
        result.paste(blurred, (x1, y1))
    return result


def save_temp(img: Image.Image) -> str:
    fd, path = tempfile.mkstemp(suffix='.png', prefix='gradify_fb_')
    os.close(fd)
    img.save(path)
    return path
