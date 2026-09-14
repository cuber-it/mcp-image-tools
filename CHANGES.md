# Changes

## c6dcd4c

- Version 1.0.0, rebuilt on the scaffold of mcp-shell-tools 8.0.0 for MCP SDK 2.x
  and protocol revision 2026-07-28
- Library without the SDK: `read`, `facts`, `resize`, `convert`, `write`
- `read` and `resize` answer with an image content block, scaled to a longest
  edge of 1024 pixels by default; `--max-edge` and `max_edge` move the limit
- `convert` and `write` refuse data that is not a picture and formats Pillow
  cannot write; a picture is written to a partial file first and then moved
- Server over stdio or streamable HTTP, OAuth token introspection, refusal to
  listen beyond this machine without authentication
