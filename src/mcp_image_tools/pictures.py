"""Looking at, describing, scaling, converting and writing pictures.

Nothing here knows about MCP. A picture handed out is scaled down to the
workspace's size limit unless a call asks for another.
"""

from __future__ import annotations

import base64
import binascii
import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from mcp_image_tools.errors import ToolError
from mcp_image_tools.workspace import Workspace

JPEG_QUALITY = 85
FORMATS_WITHOUT_ALPHA = ("JPEG", "BMP")
PORTABLE_MODES = ("1", "L", "LA", "P", "RGB", "RGBA")


@dataclass(frozen=True)
class Picture:
    """An encoded picture, to be handed out as a picture.

    Attributes:
        data: The encoded picture.
        image_format: Its format, for instance ``PNG``.
        width: Width in pixels.
        height: Height in pixels.
    """

    data: bytes
    image_format: str
    width: int
    height: int


@dataclass(frozen=True)
class Facts:
    """What can be said about a picture file without showing it.

    Attributes:
        path: Where it lies.
        image_format: Its format, for instance ``PNG``.
        width: Width in pixels.
        height: Height in pixels.
        mode: Colour mode, for instance ``RGB`` or ``RGBA``.
        bytes_on_disk: Size of the file.
        transparent: Whether it carries transparency.
    """

    path: str
    image_format: str
    width: int
    height: int
    mode: str
    bytes_on_disk: int
    transparent: bool

    def describe(self) -> str:
        """Say in one line what the file is."""
        return (
            f"{self.path}, {self.image_format} {self.width}x{self.height}, "
            f"{self.bytes_on_disk} bytes"
        )


def read(space: Workspace, path: str, max_edge: int = 0) -> Picture:
    """Return a picture as PNG, scaled down to fit a longest edge.

    ``max_edge`` of 0 uses the workspace's limit. The file is not changed.

    Raises:
        ToolError: The file is missing or is not a picture, or the edge is
            negative.
    """
    with _opened(space.resolve(path)) as picture:
        return _encoded(picture, "PNG", max_edge or space.max_edge)


def resize(space: Workspace, path: str, max_edge: int) -> Picture:
    """Return a picture as PNG, scaled so its longest edge is ``max_edge``.

    The file is not changed, and a smaller picture is not enlarged.

    Raises:
        ToolError: The file is missing or is not a picture, or the edge is not
            a positive size.
    """
    if max_edge <= 0:
        raise ToolError(f"an edge of {max_edge} pixels is not a size")
    with _opened(space.resolve(path)) as picture:
        return _encoded(picture, "PNG", max_edge)


def convert(
    space: Workspace, path: str, target: str, into: str = "", max_edge: int = 0
) -> Facts:
    """Write a picture in another format.

    The result goes to ``into``, or beside the original with the new format as
    suffix. Transparency is laid on white where the format cannot carry it.
    ``max_edge`` of 0 keeps the size.

    Returns:
        What was written.

    Raises:
        ToolError: The file is missing or is not a picture, the format cannot
            be written, or the result cannot be stored.
    """
    image_format = _writable_format(target)
    source = space.resolve(path)
    with _opened(source) as picture:
        converted = _encoded(picture, image_format, max_edge)
    destination = (
        space.resolve(into) if into else source.with_suffix(f".{image_format.lower()}")
    )
    return _stored(destination, converted.data)


def write(space: Workspace, path: str, data: str) -> Facts:
    """Write a picture from base64 data to a file.

    Missing directories are created. Data that is not a picture is refused
    before anything is written.

    Returns:
        What was written.

    Raises:
        ToolError: The data is not base64 or not a picture, or the file cannot
            be written.
    """
    try:
        decoded = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as err:
        raise ToolError("that is not valid base64 data") from err
    try:
        with Image.open(io.BytesIO(decoded)) as check:
            check.load()
    except (UnidentifiedImageError, OSError) as err:
        raise ToolError("that data is not a picture") from err
    return _stored(space.resolve(path), decoded)


def facts(space: Workspace, path: str) -> Facts:
    """Return what can be said about a picture file without showing it.

    Raises:
        ToolError: The file is missing or is not a picture.
    """
    target = space.resolve(path)
    with _opened(target) as picture:
        return _facts_of(target, picture)


def _opened(path: Path) -> Image.Image:
    """Open and load a picture file.

    Raises:
        ToolError: The file is missing, unreadable, or not a picture.
    """
    try:
        picture = Image.open(path)
        picture.load()
    except FileNotFoundError as err:
        raise ToolError(f"no such file: {path}") from err
    except IsADirectoryError as err:
        raise ToolError(f"this is a directory: {path}") from err
    except UnidentifiedImageError as err:
        raise ToolError(
            f"not a picture, or a format Pillow does not know: {path}"
        ) from err
    except OSError as err:
        raise ToolError(f"could not read {path}: {err}") from err
    return picture


def _writable_format(target: str) -> str:
    """Return the Pillow name of a format a picture can be written in.

    Raises:
        ToolError: The format is unknown or can only be read.
    """
    wanted = target.strip().upper()
    if wanted == "JPG":
        wanted = "JPEG"
    if wanted not in Image.registered_extensions().values():
        raise ToolError(f"unknown format: {target}")
    if wanted not in Image.SAVE:
        raise ToolError(f"{wanted} can be read but not written")
    return wanted


def _encoded(picture: Image.Image, image_format: str, max_edge: int) -> Picture:
    """Scale a picture down to ``max_edge`` if it is larger, and encode it.

    Raises:
        ToolError: The edge is negative, or encoding failed.
    """
    if max_edge < 0:
        raise ToolError(f"an edge of {max_edge} pixels is not a size")
    prepared = _portable(picture)
    longest = max(prepared.size)
    if 0 < max_edge < longest:
        factor = max_edge / longest
        size = (
            max(1, round(prepared.width * factor)),
            max(1, round(prepared.height * factor)),
        )
        prepared = prepared.resize(size, Image.Resampling.LANCZOS)

    if image_format in FORMATS_WITHOUT_ALPHA and prepared.has_transparency_data:
        backing = Image.new("RGB", prepared.size, (255, 255, 255))
        backing.paste(prepared, mask=prepared.convert("RGBA").getchannel("A"))
        prepared = backing
    if image_format == "JPEG" and prepared.mode != "RGB":
        prepared = prepared.convert("RGB")

    buffer = io.BytesIO()
    options = {"quality": JPEG_QUALITY} if image_format == "JPEG" else {}
    try:
        prepared.save(buffer, format=image_format, **options)
    except (OSError, ValueError) as err:
        raise ToolError(f"could not encode as {image_format}: {err}") from err
    return Picture(buffer.getvalue(), image_format, *prepared.size)


def _portable(picture: Image.Image) -> Image.Image:
    """Return a picture in a mode every format here can write.

    Colour spaces such as CMYK become RGB. Greyscale deeper than 8 bits is
    stretched from its darkest to its lightest value, because Pillow cuts
    everything above 255 to white.
    """
    if picture.mode in PORTABLE_MODES:
        return picture
    if picture.mode.startswith(("I", "F")):
        low, high = picture.getextrema()
        if high == low:
            return picture.convert("L")
        scale = 255 / (high - low)
        # point() takes only a linear expression of the form value * a + b.
        stretched = picture.convert("F").point(
            lambda value: value * scale + -low * scale
        )
        return stretched.convert("L")
    return picture.convert("RGBA" if picture.has_transparency_data else "RGB")


def _stored(path: Path, data: bytes) -> Facts:
    """Write encoded picture data to a file and report what was written.

    The data goes to a temporary name first and is renamed, so a failed write
    leaves no broken picture behind.

    Raises:
        ToolError: The file cannot be written.
    """
    partial = path.with_name(f".{path.name}.partial")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        partial.write_bytes(data)
        partial.replace(path)
    except OSError as err:
        with contextlib.suppress(OSError):
            partial.unlink(missing_ok=True)
        raise ToolError(f"could not write {path}: {err}") from err
    with _opened(path) as picture:
        return _facts_of(path, picture)


def _facts_of(path: Path, picture: Image.Image) -> Facts:
    """Describe an opened picture and the file it came from."""
    return Facts(
        path=str(path),
        image_format=picture.format,
        width=picture.width,
        height=picture.height,
        mode=picture.mode,
        bytes_on_disk=path.stat().st_size,
        transparent=picture.has_transparency_data,
    )
