"""Fixtures shared by the test modules."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from drawing import make_picture
from loopback import Issuer, serve_issuer
from mcp_image_tools import Workspace


@pytest.fixture
def issuer() -> Iterator[Issuer]:
    """Return a stand-in authorization server that rejects every token."""
    with serve_issuer() as running:
        yield running


@pytest.fixture
def space(tmp_path: Path) -> Workspace:
    """Return a workspace rooted in a fresh temporary directory."""
    return Workspace(working_dir=tmp_path)


@pytest.fixture
def picture(tmp_path: Path) -> Path:
    """Return a small PNG, 40 by 20 pixels, in the workspace."""
    return make_picture(tmp_path / "a.png")


@pytest.fixture
def large_picture(tmp_path: Path) -> Path:
    """Return a PNG of 3000 by 1500 pixels, larger than the default limit."""
    return make_picture(tmp_path / "big.png", size=(3000, 1500))
