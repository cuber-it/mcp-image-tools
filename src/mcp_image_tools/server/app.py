"""The server: the image tools over stdio or HTTP, through the MCP SDK.

This is the only module that imports the SDK. It takes the catalogue from
:mod:`mcp_image_tools.server.registry` and the authentication from
:mod:`mcp_image_tools.server.auth` and hands both to the SDK, so a change in
the SDK is felt here and nowhere else.
"""

from __future__ import annotations

import argparse
import functools
import inspect
import os
import sys
from pathlib import Path
from typing import Any, get_type_hints

from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError as AnticipatedError

from mcp_image_tools import __version__
from mcp_image_tools.errors import ToolError
from mcp_image_tools.pictures import Picture
from mcp_image_tools.server.auth import (
    AuthConfig,
    ConfigurationError,
    TokenCheck,
    auth_from_environment,
    guard_exposure,
)
from mcp_image_tools.server.registry import Tool, catalogue
from mcp_image_tools.workspace import DEFAULT_MAX_EDGE, Workspace, workspace_from

INSTRUCTIONS = (
    "Image tools: look at a picture, describe it, scale it, convert it and "
    "write one. A picture comes back as an image, scaled so its longest edge "
    "fits the server's limit unless a call asks for another.\n\n"
    "Bildwerkzeuge: ein Bild ansehen, beschreiben, skalieren, umwandeln und "
    "schreiben. Ein Bild kommt als Bild zurück, so verkleinert, dass seine "
    "längste Kante in die Grenze des Servers passt, sofern ein Aufruf keine "
    "andere verlangt."
)
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
REFUSED = 2


def _published(tool: Tool) -> Tool:
    """Wrap a tool for the SDK: refusals keep their reason, pictures become images.

    The SDK tells a deliberate refusal from a crash by the exception class:
    its own ``ToolError`` reaches the caller carrying its message, while
    anything else is a crash and the caller is told no more than "Error
    executing tool <name>". The tools raise our own ``ToolError``, which would
    land in that second case. Only those are translated; any other exception
    stays a crash.

    A :class:`Picture` is answered as the SDK's ``Image``, which reaches the
    client as an image content block. The SDK builds the output schema from
    the return annotation, so that annotation becomes ``Image`` as well; left
    as ``Picture``, every call fails the SDK's validation.
    """

    @functools.wraps(tool)
    def translated(*args: Any, **kwargs: Any) -> Any:
        try:
            result = tool(*args, **kwargs)
        except ToolError as err:
            raise AnticipatedError(str(err)) from err
        if isinstance(result, Picture):
            return Image(data=result.data, format=result.image_format)
        return result

    if get_type_hints(tool).get("return") is Picture:
        signature = inspect.signature(tool)
        translated.__signature__ = signature.replace(return_annotation=Image)
        translated.__annotations__ = {**tool.__annotations__, "return": Image}
    return translated


class _Verifier:
    """Answers the SDK's question about a token by asking a :class:`TokenCheck`."""

    def __init__(self, check: TokenCheck) -> None:
        """Bind the verifier to the check it asks."""
        self._check = check

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return the SDK's access token for a valid token, None otherwise."""
        info = await self._check.check(token)
        if info is None:
            return None
        return AccessToken(
            token=token,
            client_id=info.client_id,
            scopes=list(info.scopes),
            subject=info.subject,
            expires_at=info.expires_at,
        )


def _auth_arguments(auth: AuthConfig | None) -> dict[str, Any]:
    """Translate the authentication for the SDK's constructor.

    Resource validation stays off: it is not established that the authorization
    server names the resource a token was issued for.
    """
    if auth is None:
        return {}
    return {
        "token_verifier": _Verifier(auth.check),
        "auth": AuthSettings(
            issuer_url=auth.issuer_url,
            resource_server_url=auth.resource_url,
            required_scopes=list(auth.required_scopes),
            validate_token_resource=False,
        ),
    }


def build(space: Workspace, auth: AuthConfig | None = None) -> MCPServer:
    """Return a server with the image tools published on it.

    With ``auth``, every HTTP request has to carry a bearer token the check
    accepts, and the server publishes its protected resource metadata. stdio
    is not affected, because a pipe carries no token.
    """
    server = MCPServer(
        name="mcp-image-tools",
        version=__version__,
        instructions=INSTRUCTIONS,
        **_auth_arguments(auth),
    )
    for name, tool in catalogue(space).items():
        server.add_tool(_published(tool), name=name)
    return server


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    """Read the server's arguments; host and port default to the environment."""
    parser = argparse.ArgumentParser(
        prog="mcp-image-tools",
        description="Serve the image tools over MCP. Authentication is read from "
        "MCP_OAUTH_ENABLED, MCP_OAUTH_SERVER_URL, MCP_PUBLIC_URL and "
        "MCP_AUTH_METHOD.",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="stdio for a client that starts the server itself, "
        "streamable-http to listen on a port (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", DEFAULT_HOST),
        help="HTTP: address to bind (default: MCP_HOST or 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("MCP_PORT", str(DEFAULT_PORT)),
        help="HTTP: port to bind (default: MCP_PORT or 8000)",
    )
    parser.add_argument(
        "--path", default="/mcp", help="HTTP: path the server answers on"
    )
    parser.add_argument(
        "--working-dir",
        default=str(Path.cwd()),
        help="Where relative paths start (default: the current directory)",
    )
    parser.add_argument(
        "--max-edge",
        type=int,
        default=DEFAULT_MAX_EDGE,
        help="Longest edge in pixels a picture is scaled to before it is handed "
        "out (default: %(default)s)",
    )
    return parser.parse_args(argv)


def workspace_from_args(args: argparse.Namespace) -> Workspace:
    """Build the workspace the tools will share.

    Raises:
        ToolError: The working directory does not exist, or the limit is not
            positive.
    """
    return workspace_from({"working_dir": args.working_dir, "max_edge": args.max_edge})


def main(argv: list[str] | None = None) -> int:
    """Run the server until it is stopped.

    Returns:
        0 after the server stopped, 2 when the configuration was refused
        before it started.
    """
    args = parse(argv)
    try:
        auth = auth_from_environment(os.environ, args.path)
        guard_exposure(args.transport, args.host, auth)
        space = workspace_from_args(args)
    except (ConfigurationError, ToolError) as err:
        print(f"mcp-image-tools: {err}", file=sys.stderr)
        return REFUSED

    server = build(space, auth)
    if args.transport == "stdio":
        server.run("stdio")
        return 0

    # Sessionless: nothing ties a caller to this process between requests.
    server.run(
        "streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path=args.path,
        stateless_http=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
