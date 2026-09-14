"""Image tools: look at a picture, describe it, scale it, convert it, write one.

The tools are plain functions in :mod:`mcp_image_tools.pictures`. Every one of
them takes the :class:`Workspace` it works against as its first argument.

    from pathlib import Path
    from mcp_image_tools import Workspace, pictures

    space = Workspace(working_dir=Path.cwd())
    shown = pictures.read(space, "screenshot.png")

Nothing here knows about MCP. :mod:`mcp_image_tools.server` publishes these
functions; the library itself never imports it.
"""

from importlib.metadata import PackageNotFoundError, version

from mcp_image_tools import pictures
from mcp_image_tools.errors import ToolError
from mcp_image_tools.pictures import Facts, Picture
from mcp_image_tools.workspace import Workspace, workspace_from

try:
    __version__ = version("mcp-image-tools")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0.0.0"

__all__ = [
    "Facts",
    "Picture",
    "ToolError",
    "Workspace",
    "__version__",
    "pictures",
    "workspace_from",
]
