"""Contracts on published package metadata: bounded deps, exact build pins."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PYPROJECT = REPO / "pyproject.toml"


def _is_bounded(requirement: str) -> bool:
    """An upper cap or an exact pin both stop a breaking major from installing."""
    return "<" in requirement or "==" in requirement


def test_direct_dependencies_have_upper_bounds() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    requirements = list(data["project"]["dependencies"])
    requirements += data["project"]["optional-dependencies"].get("gpu", [])
    assert requirements
    assert all(_is_bounded(requirement) for requirement in requirements)


def test_build_backends_are_exactly_pinned() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    requires = data["build-system"]["requires"]
    assert requires
    assert all("==" in requirement for requirement in requires)
