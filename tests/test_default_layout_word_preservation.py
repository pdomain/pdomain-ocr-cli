"""Default layout reorganization keeps every OCR word.

DocTR and PP-DocLayout are mocked. A drop is allowed only when
``--experimental-drop-layout-words`` is on.
"""

from collections import Counter
from collections.abc import Callable
from pathlib import Path

import pytest
from pdomain_book_tools.geometry.bounding_box import BoundingBox
from pdomain_book_tools.geometry.point import Point
from pdomain_book_tools.layout.types import LayoutRegion, PageLayout, RegionType
from pdomain_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pdomain_book_tools.ocr.page import Page
from pdomain_book_tools.ocr.word import Word

from pdomain_ocr_cli import ocr_to_txt
from pdomain_ocr_cli._runtime import DefaultRuntimeSession

_PAGE_W = 1000
_PAGE_H = 1500


def _word(text: str, left: float, top: float, right: float, bottom: float) -> Word:
    box = BoundingBox(
        top_left=Point(left, top, is_normalized=False),
        bottom_right=Point(right, bottom, is_normalized=False),
        is_normalized=False,
    )
    return Word(text=text, bounding_box=box, ocr_confidence=0.9)


def _line(words: list[Word]) -> Block:
    return Block(items=words, child_type=BlockChildType.WORDS, block_category=BlockCategory.LINE)


def _paragraph(lines: list[Block]) -> Block:
    return Block(
        items=lines,
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.PARAGRAPH,
    )


def _page_with_figure_words() -> Page:
    figure_words = [
        _word("BALI", 100, 200, 140, 230),
        _word("cat", 160, 200, 200, 230),
        _word("cat", 220, 200, 260, 230),
    ]
    body_words = [
        _word("body", 100, 1000, 200, 1030),
        _word("text", 210, 1000, 350, 1030),
    ]
    return Page(
        width=_PAGE_W,
        height=_PAGE_H,
        page_index=0,
        blocks=[
            _paragraph([_line(figure_words)]),
            _paragraph([_line(body_words)]),
        ],
    )


def _figure_layout() -> PageLayout:
    return PageLayout(
        regions=[
            LayoutRegion(
                type=RegionType.figure,
                L=50,
                R=400,
                T=150,
                B=300,
                confidence=0.95,
            ),
            LayoutRegion(
                type=RegionType.text,
                L=50,
                R=400,
                T=950,
                B=1100,
                confidence=0.95,
            ),
        ],
        image_width=_PAGE_W,
        image_height=_PAGE_H,
        detector="test",
    )


class _FixedLayout:
    def __init__(self, layout: PageLayout) -> None:
        self.layout = layout
        self.calls = 0

    def detect(self, source: object) -> PageLayout:
        del source
        self.calls += 1
        return self.layout


def _run(
    monkeypatch: pytest.MonkeyPatch,
    run_main: object,
    image: Path,
    out: Path,
    page: Page,
    *extra_args: str,
    layout: PageLayout | None = None,
) -> None:
    assert callable(run_main)

    def runner(
        images: list[object],
        *,
        predictor: object,
        device: str,
        source_identifiers: list[str],
    ) -> list[Page]:
        del images, predictor, device, source_identifiers
        return [page]

    session = DefaultRuntimeSession(predictor=object(), device="cpu", runner=runner)
    monkeypatch.setattr(ocr_to_txt, "_create_runtime_session", lambda _det, _reco: session)
    detector = _FixedLayout(layout if layout is not None else _figure_layout())
    monkeypatch.setattr(ocr_to_txt, "_load_layout_detector", lambda _args, _device: detector)
    run_main("--no-update-check", *extra_args, "-o", str(out), str(image))
    assert detector.calls == 1


def _counts(page: Page) -> Counter[str]:
    return Counter(word.text for word in page.words)


def test_default_layout_preserves_every_ocr_word(
    mock_heavy_deps: object,
    monkeypatch: pytest.MonkeyPatch,
    run_main: object,
    single_image: tuple[Path, Path],
) -> None:
    assert callable(mock_heavy_deps)
    mock_heavy_deps()
    image, out = single_image
    page = _page_with_figure_words()
    before = _counts(page)

    _run(monkeypatch, run_main, image, out, page)

    assert _counts(page) == before
    written = (out / "page.txt").read_text(encoding="utf-8")
    assert written.count("cat") == 2
    assert "BALI" in written
    assert "body" in written
    assert "text" in written


def test_experimental_drop_layout_words_may_drop_figure_words(
    mock_heavy_deps: object,
    monkeypatch: pytest.MonkeyPatch,
    run_main: object,
    single_image: tuple[Path, Path],
) -> None:
    assert callable(mock_heavy_deps)
    mock_heavy_deps()
    image, out = single_image
    page = _page_with_figure_words()

    _run(
        monkeypatch,
        run_main,
        image,
        out,
        page,
        "--experimental-drop-layout-words",
    )

    remaining = _counts(page)
    assert remaining == Counter({"body": 1, "text": 1})
    written = (out / "page.txt").read_text(encoding="utf-8")
    assert "BALI" not in written
    assert "cat" not in written
    assert "body" in written
    assert "text" in written


def _region(kind: RegionType, left: int, top: int, right: int, bottom: int) -> LayoutRegion:
    return LayoutRegion(type=kind, L=left, R=right, T=top, B=bottom, confidence=0.95)


def _layout(*regions: LayoutRegion) -> PageLayout:
    return PageLayout(
        regions=list(regions), image_width=_PAGE_W, image_height=_PAGE_H, detector="test"
    )


def _page(*lines: list[Word]) -> Page:
    return Page(
        width=_PAGE_W,
        height=_PAGE_H,
        page_index=0,
        blocks=[_paragraph([_line(words)]) for words in lines],
    )


def _overlapping_regions() -> tuple[Page, PageLayout]:
    page = _page(
        [_word("shared", 100, 500, 200, 530), _word("shared", 210, 500, 300, 530)],
        [_word("edge", 390, 500, 450, 530)],
    )
    layout = _layout(
        _region(RegionType.text, 50, 450, 410, 600),
        _region(RegionType.text, 380, 450, 700, 600),
    )
    return page, layout


def _figure_with_caption() -> tuple[Page, PageLayout]:
    page = _page(
        [_word("inside", 120, 200, 220, 230)],
        [_word("Fig.", 120, 420, 170, 450), _word("one", 180, 420, 240, 450)],
        [_word("body", 120, 800, 220, 830)],
    )
    layout = _layout(
        _region(RegionType.figure, 100, 150, 500, 400),
        _region(RegionType.caption, 100, 410, 500, 460),
        _region(RegionType.text, 100, 780, 500, 900),
    )
    return page, layout


def _two_columns() -> tuple[Page, PageLayout]:
    page = _page(
        [_word("left", 100, 200, 200, 230), _word("same", 210, 200, 300, 230)],
        [_word("right", 600, 200, 700, 230), _word("same", 710, 200, 800, 230)],
        [_word("lower", 100, 600, 200, 630)],
        [_word("end", 600, 600, 700, 630)],
    )
    layout = _layout(
        _region(RegionType.text, 80, 150, 450, 900),
        _region(RegionType.text, 560, 150, 950, 900),
    )
    return page, layout


def _word_identities(page: Page) -> Counter[tuple[str, float, float, float, float]]:
    return Counter(
        (
            word.text,
            word.bounding_box.top_left.x,
            word.bounding_box.top_left.y,
            word.bounding_box.bottom_right.x,
            word.bounding_box.bottom_right.y,
        )
        for word in page.words
    )


@pytest.mark.parametrize("scene", [_overlapping_regions, _figure_with_caption, _two_columns])
def test_default_layout_keeps_text_and_position_of_every_word(
    mock_heavy_deps: object,
    monkeypatch: pytest.MonkeyPatch,
    run_main: object,
    single_image: tuple[Path, Path],
    capsys: pytest.CaptureFixture[str],
    scene: Callable[[], tuple[Page, PageLayout]],
) -> None:
    assert callable(mock_heavy_deps)
    real_validator = ocr_to_txt._load_validate_word_preservation
    mock_heavy_deps()
    monkeypatch.setattr(ocr_to_txt, "_load_validate_word_preservation", real_validator)
    image, out = single_image
    page, layout = scene()
    before = _word_identities(page)

    _run(monkeypatch, run_main, image, out, page, "--validate-reorg", layout=layout)

    assert _word_identities(page) == before
    assert "reorganize dropped" not in capsys.readouterr().err
    written = Counter((out / "page.txt").read_text(encoding="utf-8").split())
    assert written == Counter(identity[0] for identity in before.elements())
