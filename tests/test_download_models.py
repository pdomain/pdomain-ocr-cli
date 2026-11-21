"""Exercise model caching through the CLI entry point."""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from pdomain_ocr_cli import _hf_models, ocr_to_txt


@pytest.mark.parametrize("layout_repo", ["pdomain/layout", None])
def test_download_models_caches_active_defaults(monkeypatch, capsys, layout_repo):
    resolve = Mock(return_value=(Path("det.pt"), Path("reco.pt")))
    layout = Mock(return_value=(layout_repo, "layout-revision", "layout"))
    prefetch = Mock()
    monkeypatch.setattr(_hf_models, "_resolve_ocr_models_kwargs", resolve)
    monkeypatch.setattr(_hf_models, "_resolve_layout_source_kwargs", layout)
    monkeypatch.setattr(_hf_models, "prefetch_layout_files", prefetch)
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", "download-models"])

    with pytest.raises(SystemExit) as result:
        ocr_to_txt.main()

    assert result.value.code == 0
    resolve.assert_called_once_with(
        repo=ocr_to_txt.DEFAULT_HF_REPO,
        revision=ocr_to_txt.DEFAULT_MODEL_REVISION,
        det_filename=ocr_to_txt.DEFAULT_DET_FILENAME,
        reco_filename=ocr_to_txt.DEFAULT_RECO_FILENAME,
    )
    layout.assert_called_once_with("pp-doclayout-plus-l")
    if layout_repo is None:
        prefetch.assert_not_called()
    else:
        prefetch.assert_called_once_with(layout_repo, "layout-revision")
    assert "cached" in capsys.readouterr().out


def test_download_models_reports_failure(monkeypatch, capsys):
    resolve = Mock(side_effect=OSError("network unavailable"))
    monkeypatch.setattr(_hf_models, "_resolve_ocr_models_kwargs", resolve)
    monkeypatch.setattr(sys, "argv", ["pdomain-ocr", "download-models"])

    with pytest.raises(SystemExit) as result:
        ocr_to_txt.main()

    assert result.value.code == 1
    assert "network unavailable" in capsys.readouterr().err
