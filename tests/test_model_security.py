from __future__ import annotations

from types import SimpleNamespace

import pytest

from pdomain_ocr_cli._hf_models import DEFAULT_HF_REPO
from pdomain_ocr_cli._model_security import model_security_warnings


def _args(**overrides: object) -> SimpleNamespace:
    values = {
        "hf_repo": DEFAULT_HF_REPO,
        "model_version": None,
        "detection": None,
        "recognition": None,
        "layout_checkpoint": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_warns_when_default_model_revision_is_mutable() -> None:
    warnings = model_security_warnings(_args())
    assert any("mutable latest OCR model revision" in warning for warning in warnings)


def test_warns_when_explicit_revision_is_latest() -> None:
    warnings = model_security_warnings(_args(model_version="latest"))
    assert any("mutable latest OCR model revision" in warning for warning in warnings)


def test_pinned_default_revision_has_no_mutable_warning() -> None:
    warnings = model_security_warnings(_args(model_version="v0.7"))
    assert not any("mutable latest OCR model revision" in warning for warning in warnings)


@pytest.mark.parametrize("revision", ["main", "master", "dev", "refs/pr/1"])
def test_warns_when_revision_looks_like_a_branch(revision: str) -> None:
    warnings = model_security_warnings(_args(model_version=revision))
    assert any(f"{revision!r} looks like a branch name" in warning for warning in warnings)


@pytest.mark.parametrize(
    "revision",
    ["8b7f9b31d55015d16febaa99ae1d42960904028c", "8b7f9b3", "v0.7", "0.5", "v1.2.3-rc1"],
)
def test_commit_and_version_tag_revisions_do_not_warn(revision: str) -> None:
    assert model_security_warnings(_args(model_version=revision)) == ()


def test_branch_warning_is_skipped_for_custom_repo() -> None:
    warnings = model_security_warnings(_args(hf_repo="someone/model", model_version="main"))
    assert not any("looks like a branch name" in warning for warning in warnings)


def test_warns_for_custom_hf_repo() -> None:
    warnings = model_security_warnings(_args(hf_repo="someone/model"))
    assert any("custom Hugging Face OCR repo" in warning for warning in warnings)


def test_warns_for_local_pt_paths() -> None:
    warnings = model_security_warnings(_args(detection="det.pt", recognition="reco.pt"))
    assert any("local PyTorch checkpoint" in warning for warning in warnings)
    assert not any("mutable latest OCR model revision" in warning for warning in warnings)


def test_warns_for_layout_checkpoint() -> None:
    warnings = model_security_warnings(_args(layout_checkpoint="layout.pt"))
    assert any("layout checkpoint" in warning for warning in warnings)
