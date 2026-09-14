"""Behaviour of the picture tools, without any MCP in sight."""

from __future__ import annotations

import base64
import io
import os
import warnings
from pathlib import Path

import pytest
from PIL import Image

from drawing import encoded, make_picture
from mcp_image_tools import ToolError, Workspace, pictures
from mcp_image_tools.workspace import DEFAULT_MAX_EDGE

MODES = ["1", "L", "LA", "P", "RGB", "RGBA", "CMYK", "I;16", "I", "F"]
FORMATS = ["PNG", "JPEG", "WEBP", "GIF", "BMP"]


def opened(data: bytes) -> Image.Image:
    """Return the picture encoded in some bytes."""
    return Image.open(io.BytesIO(data))


@pytest.mark.usefixtures("picture")
def test_reading_returns_the_picture_as_png(space: Workspace) -> None:
    shown = pictures.read(space, "a.png")

    assert (shown.image_format, shown.width, shown.height) == ("PNG", 40, 20)
    assert opened(shown.data).format == "PNG"
    assert opened(shown.data).size == (40, 20)


@pytest.mark.usefixtures("large_picture")
def test_a_large_picture_is_scaled_to_the_limit(space: Workspace) -> None:
    shown = pictures.read(space, "big.png")

    assert (shown.width, shown.height) == (DEFAULT_MAX_EDGE, DEFAULT_MAX_EDGE // 2)
    assert opened(shown.data).size == (DEFAULT_MAX_EDGE, DEFAULT_MAX_EDGE // 2)


@pytest.mark.usefixtures("large_picture")
def test_the_workspace_limit_applies(tmp_path: Path) -> None:
    shown = pictures.read(Workspace(working_dir=tmp_path, max_edge=300), "big.png")

    assert (shown.width, shown.height) == (300, 150)


@pytest.mark.usefixtures("large_picture")
def test_a_call_can_raise_the_limit(space: Workspace) -> None:
    assert pictures.read(space, "big.png", max_edge=2000).width == 2000


@pytest.mark.usefixtures("picture")
def test_a_small_picture_is_not_enlarged(space: Workspace) -> None:
    assert pictures.read(space, "a.png", max_edge=1000).width == 40


@pytest.mark.usefixtures("picture")
def test_a_negative_limit_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError, match="not a size"):
        pictures.read(space, "a.png", max_edge=-1)


def test_an_absolute_path_is_read_as_given(picture: Path) -> None:
    elsewhere = Workspace(working_dir=Path("/"))

    assert pictures.read(elsewhere, str(picture)).width == 40


def test_reading_a_missing_file_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError, match="no such file"):
        pictures.read(space, "nowhere.png")


def test_reading_a_directory_is_refused(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "adir").mkdir()

    with pytest.raises(ToolError, match="directory"):
        pictures.read(space, "adir")


def test_something_that_is_no_picture_is_refused(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "broken.png").write_bytes(b"this is not a picture")

    with pytest.raises(ToolError, match="not a picture"):
        pictures.read(space, "broken.png")


def test_a_truncated_picture_is_refused(space: Workspace, tmp_path: Path) -> None:
    (tmp_path / "half.png").write_bytes(encoded()[:20])

    with pytest.raises(ToolError):
        pictures.read(space, "half.png")


def test_transparency_survives_reading(space: Workspace, tmp_path: Path) -> None:
    make_picture(tmp_path / "clear.png", mode="RGBA")

    assert opened(pictures.read(space, "clear.png").data).mode == "RGBA"


@pytest.mark.usefixtures("large_picture")
def test_resizing_keeps_the_ratio(space: Workspace) -> None:
    shown = pictures.resize(space, "big.png", 300)

    assert (shown.width, shown.height) == (300, 150)


@pytest.mark.usefixtures("picture")
def test_resizing_does_not_enlarge(space: Workspace) -> None:
    assert pictures.resize(space, "a.png", 500).width == 40


@pytest.mark.usefixtures("picture")
@pytest.mark.parametrize("edge", [0, -5])
def test_resizing_to_no_size_is_refused(space: Workspace, edge: int) -> None:
    with pytest.raises(ToolError, match="not a size"):
        pictures.resize(space, "a.png", edge)


@pytest.mark.parametrize(
    ("target", "suffix"),
    [
        ("JPEG", "jpeg"),
        ("jpg", "jpeg"),
        ("WEBP", "webp"),
        ("BMP", "bmp"),
        ("GIF", "gif"),
        ("png", "png"),
    ],
)
def test_converting_writes_beside_the_original(
    space: Workspace, tmp_path: Path, target: str, suffix: str
) -> None:
    make_picture(tmp_path / "source.tiff")

    written = pictures.convert(space, "source.tiff", target)

    stored = tmp_path / f"source.{suffix}"
    assert Path(written.path) == stored
    assert opened(stored.read_bytes()).format == written.image_format


@pytest.mark.parametrize("mode", MODES)
def test_every_colour_mode_can_be_read(
    space: Workspace, tmp_path: Path, mode: str
) -> None:
    make_picture(tmp_path / "source.tiff", mode=mode)

    assert opened(pictures.read(space, "source.tiff").data).format == "PNG"


def test_deep_greyscale_keeps_its_shades(space: Workspace, tmp_path: Path) -> None:
    deep = Image.new("I;16", (3, 1))
    for column, value in enumerate((0, 30000, 60000)):
        deep.putpixel((column, 0), value)
    deep.save(tmp_path / "deep.png")

    shown = opened(pictures.read(space, "deep.png").data)

    darkest, middle, lightest = (shown.getpixel((column, 0)) for column in range(3))
    assert (darkest, lightest) == (0, 255)
    assert 120 < middle < 135


def test_cmyk_keeps_its_colour(space: Workspace, tmp_path: Path) -> None:
    make_picture(tmp_path / "print.jpeg", mode="CMYK")

    red, green, blue = opened(pictures.read(space, "print.jpeg").data).getpixel((5, 5))

    assert red > 200
    assert green < 50
    assert blue < 50


@pytest.mark.parametrize("target", FORMATS)
@pytest.mark.parametrize("mode", MODES)
def test_every_colour_mode_can_be_converted(
    space: Workspace, tmp_path: Path, mode: str, target: str
) -> None:
    make_picture(tmp_path / "source.tiff", mode=mode)

    written = pictures.convert(space, "source.tiff", target)

    assert opened(Path(written.path).read_bytes()).format == target


def test_a_refused_picture_leaves_no_file_open(
    space: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "half.png").write_bytes(encoded()[:20])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ResourceWarning)
        with pytest.raises(ToolError):
            pictures.read(space, "half.png")

    assert [str(w.message) for w in caught if w.category is ResourceWarning] == []


@pytest.mark.usefixtures("picture")
def test_converting_writes_where_told(space: Workspace, tmp_path: Path) -> None:
    written = pictures.convert(space, "a.png", "WEBP", "out/copy.webp")

    assert written.image_format == "WEBP"
    assert (tmp_path / "out/copy.webp").is_file()


@pytest.mark.usefixtures("picture")
def test_converting_to_an_unknown_format_is_refused(space: Workspace) -> None:
    with pytest.raises(ToolError, match="unknown format"):
        pictures.convert(space, "a.png", "NOTAFORMAT")


@pytest.mark.usefixtures("picture")
def test_converting_to_a_format_that_can_only_be_read_is_refused(
    space: Workspace, tmp_path: Path
) -> None:
    with pytest.raises(ToolError, match="can be read but not written"):
        pictures.convert(space, "a.png", "PSD")

    assert not (tmp_path / "a.psd").exists()


def test_transparency_is_laid_on_white_for_jpeg(
    space: Workspace, tmp_path: Path
) -> None:
    make_picture(tmp_path / "clear.png", mode="RGBA")

    pictures.convert(space, "clear.png", "JPEG")

    converted = Image.open(tmp_path / "clear.jpeg")
    red, green, blue = converted.getpixel((5, 5))
    assert converted.mode == "RGB"
    assert red > 200
    assert green > 100
    assert blue > 100


@pytest.mark.usefixtures("large_picture")
def test_converting_can_scale_at_the_same_time(space: Workspace) -> None:
    written = pictures.convert(space, "big.png", "JPEG", max_edge=200)

    assert (written.width, written.height) == (200, 100)


def test_writing_stores_the_picture_and_reports_it(
    space: Workspace, tmp_path: Path
) -> None:
    data = base64.b64encode(encoded()).decode()

    written = pictures.write(space, "deep/new.png", data)

    assert (tmp_path / "deep/new.png").is_file()
    assert (written.image_format, written.width, written.height) == ("PNG", 8, 8)
    assert written.bytes_on_disk == (tmp_path / "deep/new.png").stat().st_size


def test_writing_refuses_what_is_no_base64(space: Workspace, tmp_path: Path) -> None:
    with pytest.raises(ToolError, match="base64"):
        pictures.write(space, "new.png", "!!! not base64 !!!")

    assert not (tmp_path / "new.png").exists()


def test_writing_refuses_base64_that_is_no_picture(
    space: Workspace, tmp_path: Path
) -> None:
    with pytest.raises(ToolError, match="not a picture"):
        pictures.write(space, "new.png", base64.b64encode(b"nope").decode())

    assert not (tmp_path / "new.png").exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes into read-only directories")
def test_a_failed_write_leaves_nothing_behind(space: Workspace, tmp_path: Path) -> None:
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        with pytest.raises(ToolError, match="could not write"):
            pictures.write(
                space, "locked/new.png", base64.b64encode(encoded()).decode()
            )
        left = list(locked.iterdir())
    finally:
        locked.chmod(0o700)

    assert not left


def test_the_facts_describe_the_picture(space: Workspace, picture: Path) -> None:
    described = pictures.facts(space, "a.png")

    assert described.image_format == "PNG"
    assert (described.width, described.height) == (40, 20)
    assert described.mode == "RGB"
    assert described.transparent is False
    assert described.bytes_on_disk == picture.stat().st_size


def test_the_facts_notice_transparency(space: Workspace, tmp_path: Path) -> None:
    make_picture(tmp_path / "clear.png", mode="RGBA")

    assert pictures.facts(space, "clear.png").transparent is True


def test_a_palette_picture_without_transparency_is_not_transparent(
    space: Workspace, tmp_path: Path
) -> None:
    make_picture(tmp_path / "palette.png", mode="P")

    assert pictures.facts(space, "palette.png").transparent is False


def test_facts_of_a_missing_file_are_refused(space: Workspace) -> None:
    with pytest.raises(ToolError, match="no such file"):
        pictures.facts(space, "nowhere.png")


def test_the_one_line_description_names_file_format_and_size(
    space: Workspace, picture: Path
) -> None:
    line = pictures.facts(space, "a.png").describe()

    assert line == f"{picture}, PNG 40x20, {picture.stat().st_size} bytes"
