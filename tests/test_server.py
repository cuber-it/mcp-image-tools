"""The server: its arguments, the workspace it builds, and what it publishes."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp.server.mcpserver import exceptions

from mcp_image_tools import Workspace
from mcp_image_tools.server import app
from mcp_image_tools.workspace import DEFAULT_MAX_EDGE

SWITCHED_ON = {
    "MCP_OAUTH_ENABLED": "true",
    "MCP_OAUTH_SERVER_URL": "https://issuer.example/",
    "MCP_PUBLIC_URL": "https://mcp.example/",
}


def published(tmp_path: Path) -> dict[str, object]:
    """Return the tools a server on a fresh workspace publishes, by name."""
    tools = asyncio.run(app.build(Workspace(working_dir=tmp_path)).list_tools())
    return {tool.name: tool for tool in tools}


def test_stdio_is_the_default() -> None:
    assert app.parse([]).transport == "stdio"


def test_the_legacy_sse_transport_is_not_offered() -> None:
    with pytest.raises(SystemExit):
        app.parse(["--transport", "sse"])


def test_the_http_arguments_are_read() -> None:
    args = app.parse(
        ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "12205"]
    )

    assert (args.transport, args.host, args.port) == (
        "streamable-http",
        "0.0.0.0",
        12205,
    )


def test_host_and_port_default_to_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")
    monkeypatch.setenv("MCP_PORT", "12250")

    args = app.parse([])

    assert (args.host, args.port) == ("0.0.0.0", 12250)


def test_an_unusable_port_in_the_environment_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("MCP_PORT", "abc")

    with pytest.raises(SystemExit) as refused:
        app.parse([])

    assert refused.value.code == app.REFUSED
    assert "invalid int value" in capsys.readouterr().err


def test_the_path_defaults_to_mcp_and_can_be_moved() -> None:
    assert app.parse([]).path == "/mcp"
    assert app.parse(["--path", "/images"]).path == "/images"


def test_the_workspace_carries_the_arguments(tmp_path: Path) -> None:
    args = app.parse(["--working-dir", str(tmp_path), "--max-edge", "640"])

    assert app.workspace_from_args(args) == Workspace(
        working_dir=tmp_path, max_edge=640
    )


def test_the_limit_defaults_to_the_library_default(tmp_path: Path) -> None:
    space = app.workspace_from_args(app.parse(["--working-dir", str(tmp_path)]))

    assert space.max_edge == DEFAULT_MAX_EDGE


def test_the_network_without_authentication_is_refused(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("MCP_OAUTH_ENABLED", raising=False)

    code = app.main(["--transport", "streamable-http", "--host", "0.0.0.0"])

    assert code == app.REFUSED
    assert "without authentication" in capsys.readouterr().err


def test_an_unknown_auth_method_is_refused_before_starting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for name, value in {**SWITCHED_ON, "MCP_AUTH_METHOD": "carrier-pigeon"}.items():
        monkeypatch.setenv(name, value)

    assert app.main(["--transport", "streamable-http"]) == app.REFUSED
    assert "no such auth method" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("argument", "message"),
    [("--working-dir", "not a directory"), ("--max-edge", "positive")],
)
def test_an_unusable_workspace_is_refused_before_starting(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], argument: str, message: str
) -> None:
    value = str(tmp_path / "nowhere") if argument == "--working-dir" else "0"

    code = app.main(["--working-dir", str(tmp_path), argument, value])

    assert code == app.REFUSED
    assert message in capsys.readouterr().err


def test_the_server_publishes_the_image_tools(tmp_path: Path) -> None:
    assert set(published(tmp_path)) == {"read", "facts", "resize", "convert", "write"}


def test_every_published_tool_carries_its_description(tmp_path: Path) -> None:
    assert [
        name for name, tool in published(tmp_path).items() if not tool.description
    ] == []


def test_the_input_schema_follows_the_tool_signature(tmp_path: Path) -> None:
    schema = published(tmp_path)["convert"].input_schema

    assert set(schema["properties"]) == {"path", "target", "into", "max_edge"}
    assert sorted(schema["required"]) == ["path", "target"]


def test_picture_tools_announce_no_structured_output(tmp_path: Path) -> None:
    tools = published(tmp_path)

    assert tools["read"].output_schema is None
    assert tools["resize"].output_schema is None
    assert tools["facts"].output_schema["type"] == "object"


def test_the_server_carries_its_instructions(tmp_path: Path) -> None:
    assert app.build(Workspace(working_dir=tmp_path)).instructions == app.INSTRUCTIONS


def test_a_refusal_keeps_its_reason(tmp_path: Path) -> None:
    """The SDK blanks a crash but carries its own ToolError through."""
    built = app.build(Workspace(working_dir=tmp_path))

    with pytest.raises(exceptions.ToolError) as refused:
        asyncio.run(built.call_tool("read", {"path": "nowhere.png"}))

    assert not isinstance(refused.value, exceptions.UnexpectedToolError)
    assert "no such file" in str(refused.value)
