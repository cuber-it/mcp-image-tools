"""What the package offers a caller who just imported it."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import mcp_image_tools
from mcp_image_tools import ToolError, Workspace, pictures

LOADED_SDK = (
    "import sys, mcp_image_tools, mcp_image_tools.server.registry; "
    "print(any(name == 'mcp' or name.startswith('mcp.') for name in sys.modules))"
)


def test_everything_promised_is_reachable() -> None:
    missing = [
        name for name in mcp_image_tools.__all__ if not hasattr(mcp_image_tools, name)
    ]

    assert missing == []


def test_the_refusal_from_the_facade_is_the_one_the_tools_raise(
    tmp_path: Path,
) -> None:
    with pytest.raises(ToolError):
        pictures.facts(Workspace(working_dir=tmp_path), "nowhere.png")


def test_the_version_is_a_string() -> None:
    assert isinstance(mcp_image_tools.__version__, str)
    assert mcp_image_tools.__version__


def test_the_library_and_the_catalogue_do_not_load_the_sdk() -> None:
    finished = subprocess.run(
        [sys.executable, "-c", LOADED_SDK],
        capture_output=True,
        text=True,
        check=True,
    )

    assert finished.stdout.strip() == "False"
