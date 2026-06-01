"""Regression guard: the hf_xet.download_files() DeprecationWarning filter
must suppress the warning even when it is emitted from an arbitrary module
(e.g., huggingface_hub.file_download), NOT from the hf_xet module itself.

Background
----------
The previous filterwarnings entry included a module field ``:hf_xet`` which
caused the ignore to silently never apply: pytest requires ALL specified fields
(message, category, AND module) to match, so a warning emitted from any module
other than ``hf_xet`` would still trip the ``filterwarnings = ["error"]`` base
rule and fail the test.

This test is the proof that the module-less filter works: the warning is
emitted from THIS module (tests.test_hf_xet_filter), not hf_xet, and must
be silently ignored.
"""

import warnings


def test_hf_xet_dep_ignored_from_arbitrary_module() -> None:
    """Warning emitted from a non-hf_xet module must be ignored."""
    warnings.warn(
        "hf_xet.download_files() is deprecated. Use XetSession().new_file_download_group().start_download_file() instead.",
        DeprecationWarning,
        stacklevel=1,
    )
    # If we reach here without an exception the warning was ignored.
    # Under filterwarnings=error, an un-ignored DeprecationWarning becomes an
    # error, which would cause this test to fail.
