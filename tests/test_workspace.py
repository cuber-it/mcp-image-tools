"""How paths are resolved and how the workspace is configured."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_image_tools import ToolError, Workspace, workspace_from
from mcp_image_tools.workspace import DEFAULT_MAX_EDGE


def test_a_relative_path_is_taken_from_the_working_directory(
    space: Workspace, tmp_path: Path
) -> None:
    assert space.resolve("below/a.png") == tmp_path / "below/a.png"


def test_an_absolute_path_is_kept(space: Workspace) -> None:
    assert space.resolve("/srv/pictures/a.png") == Path("/srv/pictures/a.png")


def test_a_tilde_is_expanded(space: Workspace) -> None:
    assert space.resolve("~/a.png") == Path.home() / "a.png"


def test_configuration_is_read(tmp_path: Path) -> None:
    space = workspace_from({"working_dir": str(tmp_path), "max_edge": 512})

    assert space == Workspace(working_dir=tmp_path, max_edge=512)


def test_an_empty_configuration_takes_the_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    space = workspace_from({})

    assert space == Workspace(working_dir=tmp_path.resolve(), max_edge=DEFAULT_MAX_EDGE)


def test_a_working_directory_that_is_no_directory_is_refused(tmp_path: Path) -> None:
    afile = tmp_path / "afile"
    afile.write_text("x", encoding="utf-8")

    with pytest.raises(ToolError, match="not a directory"):
        workspace_from({"working_dir": str(afile)})


@pytest.mark.parametrize(
    ("value", "message"), [("big", "not a number"), (0, "positive"), (-1, "positive")]
)
def test_an_unusable_limit_is_refused(
    tmp_path: Path, value: object, message: str
) -> None:
    with pytest.raises(ToolError, match=message):
        workspace_from({"working_dir": str(tmp_path), "max_edge": value})
