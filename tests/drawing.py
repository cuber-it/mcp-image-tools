"""Pictures the tests write to disk or encode in memory."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

COLOURS = {"RGBA": (255, 0, 0, 128), "P": 1}


def make_picture(
    path: Path, size: tuple[int, int] = (40, 20), mode: str = "RGB"
) -> Path:
    """Write a picture of a given size and mode, and return its path."""
    Image.new(mode, size, COLOURS.get(mode, (255, 0, 0))).save(path)
    return path


def encoded(size: tuple[int, int] = (8, 8), image_format: str = "PNG") -> bytes:
    """Return a picture encoded in memory."""
    buffer = io.BytesIO()
    Image.new("RGB", size, (0, 128, 255)).save(buffer, format=image_format)
    return buffer.getvalue()
