"""Contracts on published package metadata: bounded deps, exact build pins."""

from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement

REPO = Path(__file__).resolve().parents[1]
PYPROJECT = REPO / "pyproject.toml"


def _is_bounded(requirement: str) -> bool:
    """An upper cap or an exact pin both stop a breaking major from installing."""
    specifiers = Requirement(requirement).specifier
    return any(spec.operator in {"<", "<=", "==", "===", "~="} for spec in specifiers)


@pytest.mark.parametrize(
    ("requirement", "bounded"),
    [
        ("foo>=1,<2", True),
        ("foo==1.2.3", True),
        ("foo<=1.9", True),
        ("foo~=1.2", True),
        ("foo>=1,<2; python_version < '3.12'", True),
        ("foo>=1; python_version < '3.12'", False),
        ("foo>=1; python_version == '3.12'", False),
        ("foo>=1,!=1.5", False),
        ("foo", False),
    ],
)
def test_is_bounded_reads_the_version_specifier_only(requirement: str, bounded: bool) -> None:
    assert _is_bounded(requirement) is bounded


def test_direct_dependencies_have_upper_bounds() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    requirements = list(data["project"]["dependencies"])
    for extra in data["project"]["optional-dependencies"].values():
        requirements += extra
    assert requirements
    assert all(_is_bounded(requirement) for requirement in requirements)


def test_build_backends_are_exactly_pinned() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    requires = data["build-system"]["requires"]
    assert requires
    assert all("==" in requirement for requirement in requires)


OPENCV_DISTRIBUTIONS = frozenset(
    {
        "opencv-python",
        "opencv-contrib-python",
        "opencv-python-headless",
        "opencv-contrib-python-headless",
    }
)


def test_environment_has_one_opencv_distribution() -> None:
    """Exactly one OpenCV package provides ``cv2``.

    All four OpenCV packages write the same ``cv2/`` folder, and a second one
    leaves a mix of files that breaks ``import cv2``. python-doctr requires
    ``opencv-python``, and pdomain-book-tools 0.31.3 declares the same one.
    See pdomain-book-tools
    ``docs/decisions/2026-11-14-opencv-python-not-contrib.md``.
    """
    installed = {
        name.lower()
        for dist in importlib.metadata.distributions()
        if (name := dist.metadata["Name"])
    }
    assert installed & OPENCV_DISTRIBUTIONS == {"opencv-python"}
