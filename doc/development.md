# Development

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Checks

All of them have to pass before a change is committed.

```bash
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/python -m pylint src tests
.venv/bin/python -m pytest
```

The limits are those in `pyproject.toml`: line length 88, cyclomatic complexity
10, and pylint's design checks. What a linter reports is taken apart, not
silenced.

The tests need no network beyond the loopback interface. A few start the server
as a subprocess; the authentication tests run the server against a stand-in
authorization server in `tests/loopback.py`.

## Release

1. Raise `version` in `pyproject.toml` and describe the change in `CHANGES.md`.
2. Build into an empty directory and check both archives:

   ```bash
   .venv/bin/python -m build --outdir /tmp/mcp-image-tools-dist
   .venv/bin/python -m twine check --strict /tmp/mcp-image-tools-dist/*
   ```

3. Upload with an API token of the PyPI account that owns `mcp-image-tools`;
   twine asks for it, the user name is `__token__`:

   ```bash
   .venv/bin/python -m twine upload /tmp/mcp-image-tools-dist/*
   ```

The wheel holds the package only. The source archive also carries the tests,
the documentation and `CHANGES.md` (see `MANIFEST.in`), and the test suite
passes from it.

## Layout

```text
src/mcp_image_tools/
  __init__.py        public names of the library
  errors.py          ToolError
  workspace.py       working directory and the size limit
  pictures.py        reading, scaling, converting and writing pictures
  server/
    registry.py      the tools as a catalogue, no SDK
    auth.py          token checks and their configuration, no SDK
    app.py           the MCP server, the only module importing the SDK
tests/
doc/
```

## Rules the code keeps

- **One module imports the SDK.** Only `server/app.py` imports `mcp`; Ruff
  refuses it anywhere else, and a test makes sure the library and the catalogue
  load without it. When the SDK changes, the change is felt in one place.
- **A picture leaves the library as a `Picture`.** The server turns it into the
  SDK's image and gives the tool `Image` as its return type; with `Picture`
  there, the SDK builds an output schema and every call fails.
- **Refusals are `ToolError`s.** A tool that will not do what it was asked
  raises one with a sentence for the caller; the server passes exactly those on.
- **The docstring of a catalogue entry is the description a client reads.** It
  has an English paragraph, a German paragraph and a line starting with
  `Stichworte:`; a test holds every tool to that.
- **The documentation keeps up.** Tests check that every tool, every server
  option and every environment variable appears in the README.
