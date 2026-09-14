"""What the catalogue hands a server.

No server is involved: the catalogue is plain data, which is the point of
keeping it free of any server library.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from drawing import encoded, make_picture
from mcp_image_tools import Picture, ToolError, Workspace
from mcp_image_tools.server.registry import Catalogue, catalogue
from mcp_image_tools.workspace import DEFAULT_MAX_EDGE

EXPECTED = {"read", "facts", "resize", "convert", "write"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def tools(space: Workspace) -> Catalogue:
    """Return the catalogue bound to a fresh workspace."""
    return catalogue(space)


def test_the_whole_set_is_in_the_catalogue(tools: Catalogue) -> None:
    assert set(tools) == EXPECTED


def test_every_description_has_english_german_and_search_words(
    tools: Catalogue,
) -> None:
    incomplete = []
    for name, tool in tools.items():
        paragraphs = [part.strip() for part in tool.__doc__.split("\n\n")]
        if len(paragraphs) < 3 or not paragraphs[-1].startswith("Stichworte:"):
            incomplete.append(name)

    assert not incomplete


def test_the_reading_description_names_the_limit(tools: Catalogue) -> None:
    assert f"{DEFAULT_MAX_EDGE} pixels" in tools["read"].__doc__
    assert f"{DEFAULT_MAX_EDGE} Pixel" in tools["read"].__doc__


@pytest.mark.usefixtures("picture")
def test_reading_hands_back_a_picture_not_a_path(tools: Catalogue) -> None:
    shown = tools["read"]("a.png")

    assert isinstance(shown, Picture)
    assert shown.data.startswith(PNG_SIGNATURE)


@pytest.mark.usefixtures("picture")
def test_the_facts_come_back_as_a_mapping(tools: Catalogue) -> None:
    described = tools["facts"]("a.png")

    assert described["image_format"] == "PNG"
    assert (described["width"], described["height"]) == (40, 20)


def test_resizing_hands_back_a_picture(tools: Catalogue, tmp_path: Path) -> None:
    make_picture(tmp_path / "big.png", size=(800, 400))

    shown = tools["resize"]("big.png", 200)

    assert isinstance(shown, Picture)
    assert (shown.width, shown.height) == (200, 100)


@pytest.mark.usefixtures("picture")
def test_converting_answers_with_what_was_written(
    tools: Catalogue, tmp_path: Path
) -> None:
    answer = tools["convert"]("a.png", "JPEG")

    assert answer.startswith(f"wrote {tmp_path / 'a.jpeg'}, JPEG 40x20")


def test_writing_answers_with_what_was_written(
    tools: Catalogue, tmp_path: Path
) -> None:
    answer = tools["write"]("new.png", base64.b64encode(encoded()).decode())

    assert answer.startswith(f"wrote {tmp_path / 'new.png'}, PNG 8x8")


def test_a_refusal_reaches_the_caller(tools: Catalogue) -> None:
    with pytest.raises(ToolError, match="no such file"):
        tools["read"]("nowhere.png")
