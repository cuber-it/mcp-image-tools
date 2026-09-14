"""What the tools share: the working directory and the size limit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp_image_tools.errors import ToolError

DEFAULT_MAX_EDGE = 1024


@dataclass
class Workspace:
    """The state the tools work against.

    Attributes:
        working_dir: Directory relative paths are resolved against.
        max_edge: Longest edge in pixels a picture is scaled to before it is
            handed out, unless a call asks for another.
    """

    working_dir: Path
    max_edge: int = DEFAULT_MAX_EDGE

    def resolve(self, path: str) -> Path:
        """Return a path from a caller as an absolute one."""
        candidate = Path(path).expanduser()
        return candidate if candidate.is_absolute() else self.working_dir / candidate


def workspace_from(config: dict[str, Any]) -> Workspace:
    """Build the workspace from a configuration mapping.

    Raises:
        ToolError: ``working_dir`` is not a directory, or ``max_edge`` is not a
            positive whole number.
    """
    working = Path(str(config.get("working_dir", Path.cwd()))).expanduser().resolve()
    if not working.is_dir():
        raise ToolError(f"working_dir is not a directory: {working}")
    try:
        max_edge = int(config.get("max_edge", DEFAULT_MAX_EDGE))
    except (TypeError, ValueError) as err:
        raise ToolError(f"max_edge is not a number: {config['max_edge']!r}") from err
    if max_edge <= 0:
        raise ToolError(f"max_edge has to be positive, not {max_edge}")
    return Workspace(working_dir=working, max_edge=max_edge)
