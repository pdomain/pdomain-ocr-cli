"""Proves OPENCV_IO_MAX_IMAGE_PIXELS is set before cv2 is ever imported.

cv2 reads this env var at import time (no runtime-settable equivalent of
Pillow's ``MAX_IMAGE_PIXELS``), so ordering matters, not just the final
value. A shared pytest process may already have cv2 imported by an earlier
test or by conftest -- making that ordering unobservable in-process -- so
this runs in a fresh subprocess with a ``sys.meta_path`` hook that records
the env var's value at the exact moment cv2's own import is resolved.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

_PROBE_SCRIPT = textwrap.dedent("""
    import importlib.abc
    import os
    import sys

    seen = []

    class _RecordEnvOnCv2Import(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path, target=None):
            if name == "cv2":
                seen.append(os.environ.get("OPENCV_IO_MAX_IMAGE_PIXELS"))
                print("ENV_AT_CV2_IMPORT=" + repr(os.environ.get("OPENCV_IO_MAX_IMAGE_PIXELS")))
            return None  # defer to the real finders; only observe

    sys.meta_path.insert(0, _RecordEnvOnCv2Import())
    import pdomain_ocr_cli.ocr_to_txt  # noqa: F401

    print("ENV_AFTER_CLI_IMPORT=" + repr(os.environ.get("OPENCV_IO_MAX_IMAGE_PIXELS")))
    # Current book-tools does not import cv2 from the CLI package import.
    # Import it here so the hook still observes the value the CLI already set.
    if "cv2" not in sys.modules:
        import cv2  # noqa: F401
    assert seen, "cv2 import was not observed"
""")


def test_opencv_io_max_image_pixels_set_before_cv2_is_imported() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE_SCRIPT],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ENV_AT_CV2_IMPORT='100000000'" in result.stdout, result.stdout


def test_opencv_io_max_image_pixels_respects_caller_override() -> None:
    probe = textwrap.dedent("""
        import os
        os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = "42"
        import pdomain_ocr_cli.ocr_to_txt  # noqa: F401
        print("FINAL=" + os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"])
    """)
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "FINAL=42" in result.stdout, result.stdout
