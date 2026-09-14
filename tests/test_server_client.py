"""The server as a client sees it, in process.

A client built on the server object speaks to it directly — no port, no
subprocess — and negotiates the current protocol revision while doing it. That
makes this the place to pin what a caller actually receives: above all that a
picture arrives as an image content block.
"""

from __future__ import annotations

import asyncio
import base64
import io
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mcp import Client
from PIL import Image

from drawing import encoded, make_picture
from mcp_image_tools import Workspace
from mcp_image_tools.server import app

CURRENT_REVISION = "2026-07-28"


def served(space: Workspace, work: Callable[[Any], Awaitable[Any]]) -> Any:
    """Run one piece of client work against a server on this workspace."""
    built = app.build(space)

    async def talk() -> Any:
        async with Client(built) as client:
            return await work(client)

    return asyncio.run(talk())


def called(space: Workspace, name: str, arguments: dict[str, Any]) -> Any:
    """Call one tool through a client and return its answer."""

    async def work(client: Any) -> Any:
        return await client.call_tool(name, arguments)

    return served(space, work)


def picture_in(answer: Any) -> Image.Image:
    """Return the picture carried by the single image block of an answer."""
    [block] = answer.content
    assert (block.type, block.mime_type) == ("image", "image/png")
    return Image.open(io.BytesIO(base64.b64decode(block.data)))


def test_the_current_revision_is_spoken(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return client.protocol_version

    assert served(Workspace(working_dir=tmp_path), work) == CURRENT_REVISION


def test_the_server_names_itself(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return client.server_info

    info = served(Workspace(working_dir=tmp_path), work)

    assert info.name == "mcp-image-tools"
    assert info.version


def test_the_tools_are_offered_with_descriptions(tmp_path: Path) -> None:
    async def work(client: Any) -> Any:
        return await client.list_tools()

    listed = served(Workspace(working_dir=tmp_path), work).tools

    assert {tool.name for tool in listed} == {
        "read",
        "facts",
        "resize",
        "convert",
        "write",
    }
    assert [tool.name for tool in listed if not tool.description] == []


def test_reading_arrives_as_an_image_scaled_to_the_limit(tmp_path: Path) -> None:
    make_picture(tmp_path / "big.png", size=(3000, 1500))

    answer = called(Workspace(working_dir=tmp_path), "read", {"path": "big.png"})

    assert not answer.is_error
    assert picture_in(answer).size == (1024, 512)


def test_the_server_limit_and_the_call_limit_apply(tmp_path: Path) -> None:
    make_picture(tmp_path / "big.png", size=(3000, 1500))
    space = Workspace(working_dir=tmp_path, max_edge=300)

    by_server = called(space, "read", {"path": "big.png"})
    by_call = called(space, "read", {"path": "big.png", "max_edge": 600})

    assert picture_in(by_server).size == (300, 150)
    assert picture_in(by_call).size == (600, 300)


def test_resizing_arrives_as_an_image(tmp_path: Path) -> None:
    make_picture(tmp_path / "big.png", size=(800, 400))

    answer = called(
        Workspace(working_dir=tmp_path), "resize", {"path": "big.png", "max_edge": 200}
    )

    assert picture_in(answer).size == (200, 100)


def test_the_facts_arrive_as_structured_content(tmp_path: Path) -> None:
    make_picture(tmp_path / "a.png")

    answer = called(Workspace(working_dir=tmp_path), "facts", {"path": "a.png"})

    assert not answer.is_error
    assert answer.structured_content["image_format"] == "PNG"
    assert (
        answer.structured_content["width"],
        answer.structured_content["height"],
    ) == (
        40,
        20,
    )


def test_writing_reaches_the_disk(tmp_path: Path) -> None:
    data = base64.b64encode(encoded()).decode()

    answer = called(
        Workspace(working_dir=tmp_path), "write", {"path": "new.png", "data": data}
    )

    assert not answer.is_error
    assert Image.open(tmp_path / "new.png").size == (8, 8)


def test_converting_reaches_the_disk(tmp_path: Path) -> None:
    make_picture(tmp_path / "a.png")

    answer = called(
        Workspace(working_dir=tmp_path), "convert", {"path": "a.png", "target": "JPEG"}
    )

    assert not answer.is_error
    assert Image.open(tmp_path / "a.jpeg").format == "JPEG"


def test_a_refusal_arrives_with_its_reason(tmp_path: Path) -> None:
    answer = called(Workspace(working_dir=tmp_path), "read", {"path": "nowhere.png"})

    assert answer.is_error
    assert "no such file" in answer.content[0].text
