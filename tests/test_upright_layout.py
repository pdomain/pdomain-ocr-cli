"""Layout and crops follow the upright image OCR kept.

DocTR and PP-DocLayout stay mocked. These tests never download weights.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from _fakes import FakeArray, FakePage

from pdomain_ocr_cli import ocr_to_txt
from pdomain_ocr_cli._runtime import DefaultRuntimeSession

FIXTURES = Path(__file__).parent / "fixtures"
ROTATED_PAGE = FIXTURES / "rotated_page.png"


class _RecordingDetector:
    def __init__(self, layout: SimpleNamespace) -> None:
        self.layout = layout
        self.sources: list[object] = []

    def detect(self, source: object) -> SimpleNamespace:
        self.sources.append(source)
        return self.layout


class _Cv2:
    def __init__(self, image: object | None) -> None:
        self.image = image
        self.imread_paths: list[str] = []
        self.encoded: list[object] = []

    def imread(self, path: str) -> object | None:
        self.imread_paths.append(path)
        return self.image

    def imencode(self, ext: str, image: object) -> tuple[bool, bytes]:
        del ext
        self.encoded.append(image)
        return True, b"\x00"


def _install_page(
    monkeypatch: pytest.MonkeyPatch,
    page_for_image: object,
) -> None:
    def runner(
        images: list[object],
        *,
        predictor: object,
        device: str,
        source_identifiers: list[str],
    ) -> list[object]:
        del predictor, device, source_identifiers
        page = page_for_image(images[0]) if callable(page_for_image) else page_for_image
        return [page]

    session = DefaultRuntimeSession(predictor=object(), device="cpu", runner=runner)
    monkeypatch.setattr(ocr_to_txt, "_create_runtime_session", lambda _det, _reco: session)


def _figure_layout() -> SimpleNamespace:
    figure = SimpleNamespace(type="figure", confidence=0.9, T=0, B=10, L=0, R=10)
    return SimpleNamespace(regions=[figure], inference_ms=1)


def test_upright_layout_source_keeps_path_when_unrotated(tmp_path: Path) -> None:
    from pdomain_ocr_cli._pipeline import upright_layout_source

    image_path = tmp_path / "page.png"
    source = np.zeros((4, 6, 3), dtype=np.uint8)
    chosen = upright_layout_source(
        image_path,
        source,
        page_image=source,
        rotation_degrees=0,
    )
    assert chosen is image_path


def test_upright_layout_source_rotates_when_angle_is_kept() -> None:
    from pdomain_ocr_cli._pipeline import upright_layout_source

    source = np.zeros((2, 3, 3), dtype=np.uint8)
    source[0, 0, 0] = 7
    chosen = upright_layout_source(
        Path("page.png"),
        source,
        page_image=None,
        rotation_degrees=90,
    )
    assert isinstance(chosen, np.ndarray)
    assert chosen.shape == (3, 2, 3)
    assert int(chosen[0, 1, 0]) == 7


def test_upright_layout_source_rejects_non_quarter_turn() -> None:
    from pdomain_ocr_cli._pipeline import upright_layout_source

    source = np.zeros((2, 2, 3), dtype=np.uint8)
    with pytest.raises(ValueError, match="unsupported OCR rotation"):
        _ = upright_layout_source(
            Path("page.png"),
            source,
            page_image=None,
            rotation_degrees=45,
        )
    with pytest.raises(ValueError, match="unsupported OCR rotation"):
        _ = upright_layout_source(
            Path("page.png"),
            source,
            page_image=None,
            rotation_degrees="sideways",
        )


def test_upright_layout_source_rejects_a_non_array_when_rotating() -> None:
    from pdomain_ocr_cli._pipeline import upright_layout_source

    with pytest.raises(TypeError, match="decoded page array"):
        _ = upright_layout_source(
            Path("page.png"),
            "not-an-array",
            page_image=None,
            rotation_degrees=90,
        )


def test_upright_layout_source_uses_stashed_upright_buffer() -> None:
    from pdomain_ocr_cli._pipeline import upright_layout_source

    source = np.zeros((2, 3, 3), dtype=np.uint8)
    upright = np.ones((3, 2, 3), dtype=np.uint8)
    chosen = upright_layout_source(
        Path("page.png"),
        source,
        page_image=upright,
        rotation_degrees=None,
    )
    assert chosen is upright


def test_rotated_page_layout_and_crops_use_upright_image(
    mock_heavy_deps: object,
    monkeypatch: pytest.MonkeyPatch,
    run_main: object,
    tmp_path: Path,
) -> None:
    """A rotated page feeds detect() and crops the upright buffer, not the file."""
    assert callable(mock_heavy_deps)
    assert callable(run_main)
    mock_heavy_deps()
    image = tmp_path / "rotated_page.png"
    shutil.copy(ROTATED_PAGE, image)
    out = tmp_path / "out"
    upright = FakeArray(100)

    def page_for_image(source: object) -> FakePage:
        del source
        page = FakePage(text="UPRIGHT TEXT")
        page.cv2_numpy_page_image = upright
        page.ocr_rotation_degrees = 90
        return page

    _install_page(monkeypatch, page_for_image)
    detector = _RecordingDetector(_figure_layout())
    monkeypatch.setattr(ocr_to_txt, "_load_layout_detector", lambda _args, _device: detector)
    cv2_fake = _Cv2(image=FakeArray(100))
    monkeypatch.setattr(ocr_to_txt, "_load_illustration_deps", lambda: (cv2_fake, {"figure"}))

    run_main(
        "--no-update-check",
        "--layout-model",
        "pp-doclayout-plus-l",
        "--extract-illustrations",
        "-o",
        str(out),
        str(image),
    )

    assert detector.sources == [upright]
    assert cv2_fake.imread_paths == []
    assert cv2_fake.encoded
    assert (out / "i_rotated_page_01.jpg").exists()


def test_unrotated_page_keeps_on_disk_layout_and_crops(
    mock_heavy_deps: object,
    monkeypatch: pytest.MonkeyPatch,
    run_main: object,
    single_image: tuple[Path, Path],
) -> None:
    """Rotation 0 still detects and crops from the on-disk path."""
    assert callable(mock_heavy_deps)
    assert callable(run_main)
    mock_heavy_deps()
    image, out = single_image

    def page_for_image(source: object) -> FakePage:
        page = FakePage(text="FLAT TEXT")
        page.cv2_numpy_page_image = source
        page.ocr_rotation_degrees = 0
        return page

    _install_page(monkeypatch, page_for_image)
    detector = _RecordingDetector(_figure_layout())
    monkeypatch.setattr(ocr_to_txt, "_load_layout_detector", lambda _args, _device: detector)
    cv2_fake = _Cv2(image=FakeArray(100))
    monkeypatch.setattr(ocr_to_txt, "_load_illustration_deps", lambda: (cv2_fake, {"figure"}))

    run_main(
        "--no-update-check",
        "--layout-model",
        "pp-doclayout-plus-l",
        "--extract-illustrations",
        "-o",
        str(out),
        str(image),
    )

    assert detector.sources == [image]
    assert cv2_fake.imread_paths == [str(image)]
    assert (out / "i_page_01.jpg").exists()


def test_kept_angle_orients_layout_when_no_buffer_is_stashed(
    mock_heavy_deps: object,
    monkeypatch: pytest.MonkeyPatch,
    run_main: object,
    tmp_path: Path,
) -> None:
    """The single-image angle is applied when the page has no upright buffer."""
    assert callable(mock_heavy_deps)
    assert callable(run_main)
    mock_heavy_deps()
    image = tmp_path / "rotated_page.png"
    shutil.copy(ROTATED_PAGE, image)
    out = tmp_path / "out"
    seen: dict[str, object] = {}

    def page_for_image(source: object) -> FakePage:
        seen["source"] = source
        page = FakePage(text="ANGLE ONLY")
        page.ocr_rotation_degrees = 90
        return page

    _install_page(monkeypatch, page_for_image)
    detector = _RecordingDetector(SimpleNamespace(regions=[], inference_ms=1))
    monkeypatch.setattr(ocr_to_txt, "_load_layout_detector", lambda _args, _device: detector)

    run_main(
        "--no-update-check",
        "--layout-model",
        "pp-doclayout-plus-l",
        "-o",
        str(out),
        str(image),
    )

    source = seen["source"]
    assert isinstance(source, np.ndarray)
    assert source.shape[0] != source.shape[1]
    layout_input = detector.sources[0]
    assert isinstance(layout_input, np.ndarray)
    assert layout_input.shape == (source.shape[1], source.shape[0], source.shape[2])


def test_single_image_compat_keeps_rotation_degrees(monkeypatch: pytest.MonkeyPatch) -> None:
    page = SimpleNamespace(text="A")

    class _Document:
        @staticmethod
        def from_image_ocr_via_doctr(
            image: object,
            *,
            source_identifier: str,
            predictor: object,
        ) -> tuple[SimpleNamespace, int]:
            del image, source_identifier, predictor
            return SimpleNamespace(pages=[page]), 90

    monkeypatch.setattr(
        ocr_to_txt.importlib,
        "import_module",
        lambda _name: SimpleNamespace(Document=_Document),
    )

    result = ocr_to_txt._run_doctr_batch_single_image_compat(
        ["img-a"],
        predictor="predictor",
        source_identifiers=["rotated_page.png"],
    )

    assert result == [page]
    assert getattr(page, "ocr_rotation_degrees", None) == 90
