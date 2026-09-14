# mcp-image-tools

**Version 8.0 — completely rewritten and revised.**

Image tools for AI assistants: look at a picture, describe it, scale it,
convert it, write one. Usable as a Python library or served over the Model
Context Protocol.

- **A picture arrives as a picture.** `read` and `resize` answer with an image
  content block, not with a path or a base64 string.
- **Large pictures are scaled down** before they are handed out, to a longest
  edge of 1024 pixels unless the server or a call sets another limit.
- **Server** over stdio or streamable HTTP with the MCP SDK, protocol revision
  2026-07-28, OAuth for HTTP.

## Installation

Python 3.12 or later.

```bash
pip install mcp-image-tools            # the library
pip install "mcp-image-tools[server]"  # and the MCP server
```

## Quick start

A client that starts the server itself, over stdio:

```json
{
  "mcpServers": {
    "images": {
      "command": "mcp-image-tools",
      "args": ["--working-dir", "/home/you/pictures"]
    }
  }
}
```

Over HTTP, with OAuth:

```bash
MCP_OAUTH_ENABLED=true \
MCP_OAUTH_SERVER_URL=https://auth.example.org/ \
MCP_PUBLIC_URL=https://mcp.example.org/ \
mcp-image-tools --transport streamable-http --host 0.0.0.0 --port 12205 --path /images
```

As a library:

```python
from pathlib import Path

from mcp_image_tools import Workspace, pictures

space = Workspace(working_dir=Path.cwd(), max_edge=800)
shown = pictures.read(space, "screenshot.png")
print(shown.image_format, shown.width, shown.height)
```

## Tools

| Tool | What it does |
|---|---|
| `read` | Open a picture and return it as a picture, scaled to the limit |
| `facts` | Format, width, height, colour mode, transparency and file size, without showing it |
| `resize` | Return a picture scaled to a given longest edge |
| `convert` | Write a picture in another format: PNG, JPEG, WebP, GIF, BMP |
| `write` | Write a picture from base64 data |

`convert` and `write` refuse data that is not a picture before anything is
written. Transparency is laid on white where the target format cannot carry it.

## Server options

| Option | Default | Meaning |
|---|---|---|
| `--transport` | `stdio` | `stdio` or `streamable-http` |
| `--host` | `MCP_HOST`, else `127.0.0.1` | address to bind (HTTP) |
| `--port` | `MCP_PORT`, else `8000` | port to bind (HTTP) |
| `--path` | `/mcp` | path the endpoint answers on (HTTP) |
| `--working-dir` | current directory | where relative paths start |
| `--max-edge` | `1024` | longest edge a picture is scaled to |

Authentication over HTTP is configured with `MCP_OAUTH_ENABLED`,
`MCP_OAUTH_SERVER_URL`, `MCP_PUBLIC_URL` and `MCP_AUTH_METHOD`; the server
refuses to listen beyond this machine without it.

## Development

Setup, checks, release steps and the rules the code keeps:
[doc/development.md](https://github.com/cuber-it/mcp-image-tools/blob/master/doc/development.md).
Changes are listed in
[CHANGES.md](https://github.com/cuber-it/mcp-image-tools/blob/master/CHANGES.md).

## License

MIT, see
[LICENSE](https://github.com/cuber-it/mcp-image-tools/blob/master/LICENSE).
