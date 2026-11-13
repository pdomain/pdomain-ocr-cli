"""Quote and dash cleanup the CLI applies before it writes page text.

These drive :func:`pdomain_ocr_cli._pipeline.apply_text_normalizations`, the
function ``ocr_to_txt`` calls for ``--straight-quotes`` and
``--em-dash-to-double-hyphen``. String literals that contain curly quotes or
em dashes use ``\\uXXXX`` escapes so ERA001 does not treat them as code.
"""

from __future__ import annotations

import pytest

from pdomain_ocr_cli._pipeline import apply_text_normalizations

# U+2018 LEFT SINGLE QUOTATION MARK
# U+2019 RIGHT SINGLE QUOTATION MARK
# U+201A SINGLE LOW-9 QUOTATION MARK
# U+201B SINGLE HIGH-REVERSED-9 QUOTATION MARK
# U+201C LEFT DOUBLE QUOTATION MARK
# U+201D RIGHT DOUBLE QUOTATION MARK
# U+201E DOUBLE LOW-9 QUOTATION MARK
# U+201F DOUBLE HIGH-REVERSED-9 QUOTATION MARK
# U+2013 EN DASH
# U+2014 EM DASH

_SINGLE = ("\u2018", "\u2019", "\u201a", "\u201b")
_DOUBLE = ("\u201c", "\u201d", "\u201e", "\u201f")


@pytest.mark.parametrize("src", _SINGLE)
def test_straight_quotes_maps_curly_singles(src: str) -> None:
    assert (
        apply_text_normalizations(src, straight_quotes=True, em_dash_to_double_hyphen=False) == "'"
    )


@pytest.mark.parametrize("src", _DOUBLE)
def test_straight_quotes_maps_curly_doubles(src: str) -> None:
    assert (
        apply_text_normalizations(src, straight_quotes=True, em_dash_to_double_hyphen=False) == '"'
    )


def test_straight_quotes_in_a_sentence() -> None:
    src = "\u201cHello,\u201d she said, \u201cit\u2019s fine.\u201d"
    assert (
        apply_text_normalizations(src, straight_quotes=True, em_dash_to_double_hyphen=False)
        == '"Hello," she said, "it\'s fine."'
    )


def test_flags_off_leave_curly_quotes_and_em_dash() -> None:
    src = "plain ASCII \"quotes\" and 'apostrophes' \u2014 unchanged"
    assert (
        apply_text_normalizations(src, straight_quotes=False, em_dash_to_double_hyphen=False) == src
    )


def test_straight_quotes_leave_ascii_and_en_dash() -> None:
    src = "plain ASCII \"quotes\" and 'apostrophes' \u2013 unchanged"
    assert (
        apply_text_normalizations(src, straight_quotes=True, em_dash_to_double_hyphen=True) == src
    )


def test_em_dash_becomes_double_hyphen() -> None:
    assert (
        apply_text_normalizations(
            "foo\u2014bar", straight_quotes=False, em_dash_to_double_hyphen=True
        )
        == "foo--bar"
    )
    assert (
        apply_text_normalizations(
            "a\u2014b\u2014c", straight_quotes=False, em_dash_to_double_hyphen=True
        )
        == "a--b--c"
    )


@pytest.mark.parametrize("falsy", [None, ""])
def test_empty_or_missing_page_text_stays_empty(falsy: str | None) -> None:
    assert (
        apply_text_normalizations(falsy, straight_quotes=True, em_dash_to_double_hyphen=True) == ""
    )


def test_both_flags_straighten_quotes_then_em_dash() -> None:
    src = "\u201cwait\u2014really?\u201d"
    assert (
        apply_text_normalizations(src, straight_quotes=True, em_dash_to_double_hyphen=True)
        == '"wait--really?"'
    )
