# Changes

## cb76ed3

- Pictures in CMYK, 16-bit or floating point greyscale are read and converted
  instead of refused: colour spaces become RGB, deep greyscale is stretched to
  8 bits instead of being cut to white
- The check that data is a picture happens in `write` only, not again for a
  picture `convert` has just encoded
- `Picture.image_format` is written in capitals like `Facts.image_format`; the
  server lowers it for the SDK

## 35262c4

- Version 8.0.0: completely rewritten and revised
- Package metadata for PyPI: documentation and changelog links
- `MANIFEST.in` puts tests, documentation and `CHANGES.md` into the source
  archive
- Release steps and the rules the code keeps in `doc/development.md`
- Tests check that the README names every tool, server option and environment
  variable, and links only absolutely

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
