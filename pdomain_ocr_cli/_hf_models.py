"""Argparse-shaped adapters around :mod:`pdomain_book_tools.hf`.

The canonical model-resolution primitives live in ``pdomain_book_tools.hf`` so
pdomain-ocr-cli, pdomain-ocr-labeler, and pdomain-prep-for-pgdp share them. This module keeps
only the argparse-flavoured wrappers that the CLI's ``ocr_to_txt`` driver
needs — the kwargs-shaped functions in ``pdomain_book_tools.hf`` are the right
target for non-CLI callers.
"""

from __future__ import annotations

import importlib
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable

_Result = TypeVar("_Result")


class _ModelComponents(Protocol):
    ModelCacheEntry: Callable[[Path, str, str, str], object]

    def track_model_download(
        self, app: str, source: str, entries: tuple[object, ...], download: Callable[[], _Result]
    ) -> _Result: ...


def _track_download(
    repo: str,
    revision: str | None,
    filenames: tuple[str, ...],
    download: Callable[[], _Result],
) -> _Result:
    if revision is None or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        return download()
    module_name = "pdomain_ops.suite.model_components"
    try:
        module = cast("_ModelComponents", cast("object", importlib.import_module(module_name)))
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        # The published dependency does not yet include the shared registry.
        return download()

    hub = importlib.import_module("huggingface_hub.constants")
    cache_path: object = getattr(hub, "HF_HUB_CACHE", None)
    if not isinstance(cache_path, str):
        raise TypeError("Hugging Face did not report a model cache path")
    cache = Path(cache_path).absolute()
    try:
        entries = tuple(module.ModelCacheEntry(cache, repo, revision, name) for name in filenames)
    except ValueError:
        # Keep support for custom names which the ownership adapter cannot verify.
        return download()
    source = "installer" if os.environ.get("PDOMAIN_OCR_MODEL_SOURCE") == "installer" else "runtime"
    return module.track_model_download("pdomain-ocr-cli", source, entries, download)


def _prepare_remote_files(
    label: str,
    repo: str,
    revision: str | None,
    required: tuple[str, ...],
    download: Callable[[], _Result],
    *,
    sidecars: tuple[str, ...] = (),
) -> _Result:
    """Announce missing required files immediately before the tracked fetch."""
    from huggingface_hub import try_to_load_from_cache

    def prepare() -> _Result:
        try:
            missing = any(
                not isinstance(try_to_load_from_cache(repo, name, revision=revision), str)
                for name in required
            )
        except (OSError, ValueError):
            # The resolver still handles unreadable caches and invalid source arguments.
            missing = False
        if missing:
            print(f"Downloading missing {label} model files...", flush=True)  # noqa: T201
        return download()

    return _track_download(repo, revision, required + sidecars, prepare)


def _ocr_sidecars(detection: str, recognition: str) -> tuple[str, ...]:
    from pathlib import PurePosixPath

    return tuple(
        str(PurePosixPath(name).with_suffix(ext))
        for name in (detection, recognition)
        for ext in OCR_MODEL_SIDECARS
    )


class _HfArgs(Protocol):
    detection: str | None
    recognition: str | None
    hf_repo: str
    model_version: str | None
    det_filename: str
    reco_filename: str
    layout_model: str
    layout_checkpoint: str | None


class _PdBookToolsHfModule(Protocol):
    DEFAULT_DET_FILENAME: str
    DEFAULT_HF_REPO: str
    DEFAULT_RECO_FILENAME: str
    LAYOUT_MODEL_FILES: tuple[str, ...]
    OCR_MODEL_SIDECARS: tuple[str, ...]

    def hf_download(self, *args: object, **kwargs: object) -> object: ...

    def prefetch_layout_files(self, *args: object, **kwargs: object) -> object: ...

    def resolve_layout_source(
        self, layout_model: str, layout_checkpoint: str | None = None
    ) -> tuple[str | None, str | None, str]: ...

    def resolve_ocr_models(
        self,
        *,
        repo: str = "pdomain/pdomain-ocr-models",
        revision: str | None = None,
        det_filename: str = "detection/pdomain-all-detection-model-finetuned.pt",
        reco_filename: str = "recognition/pdomain-all-recognition-model-finetuned.pt",
        detection_path: Path | None = None,
        recognition_path: Path | None = None,
    ) -> tuple[Path, Path]: ...

    def short_revision(self, rev: str | None) -> str: ...

    def silence_transformers_load_chatter(self, *args: object, **kwargs: object) -> object: ...

    def suppress_hf_unauth_warning(self, *args: object, **kwargs: object) -> object: ...


_HF = cast("_PdBookToolsHfModule", cast("object", importlib.import_module("pdomain_book_tools.hf")))

DEFAULT_DET_FILENAME = _HF.DEFAULT_DET_FILENAME
DEFAULT_HF_REPO = _HF.DEFAULT_HF_REPO
DEFAULT_RECO_FILENAME = _HF.DEFAULT_RECO_FILENAME
LAYOUT_MODEL_FILES = _HF.LAYOUT_MODEL_FILES
OCR_MODEL_SIDECARS = _HF.OCR_MODEL_SIDECARS
hf_download = _HF.hf_download
short_revision = _HF.short_revision
silence_transformers_load_chatter = _HF.silence_transformers_load_chatter
suppress_hf_unauth_warning = _HF.suppress_hf_unauth_warning
_resolve_layout_source_kwargs = _HF.resolve_layout_source
_resolve_ocr_models_kwargs = _HF.resolve_ocr_models


def prefetch_layout_files(repo: str, revision: str | None) -> object:
    """Prefetch layout models and track the exact pinned files."""
    return _prepare_remote_files(
        "layout",
        repo,
        revision,
        LAYOUT_MODEL_FILES,
        lambda: _HF.prefetch_layout_files(repo, revision),
    )


__all__ = [
    "DEFAULT_DET_FILENAME",
    "DEFAULT_HF_REPO",
    "DEFAULT_RECO_FILENAME",
    "LAYOUT_MODEL_FILES",
    "OCR_MODEL_SIDECARS",
    "det_source_descriptor",
    "hf_download",
    "prefetch_default_models",
    "prefetch_layout_files",
    "reco_source_descriptor",
    "resolve_layout_source",
    "resolve_ocr_models",
    "short_revision",
    "silence_transformers_load_chatter",
    "suppress_hf_unauth_warning",
]


# ---------------------------------------------------------------------------
# OCR detection + recognition models — argparse adapter
# ---------------------------------------------------------------------------


def resolve_ocr_models(args: _HfArgs) -> tuple[Path, Path]:
    """Return ``(det_path, reco_path)`` from argparse-shaped CLI args.

    Validates the partial-input case (one of ``--detection``/``--recognition``
    set without the other) before delegating to
    :func:`pdomain_book_tools.hf.resolve_ocr_models`.
    """
    if bool(args.detection) != bool(args.recognition):
        which = "--detection" if args.detection else "--recognition"
        print(  # noqa: T201  # CLI output
            f"ERROR: {which} requires its counterpart. Provide both --detection and --recognition.",
            file=sys.stderr,
        )
        sys.exit(1)

    det = Path(args.detection) if args.detection else None
    reco = Path(args.recognition) if args.recognition else None

    try:

        def resolve() -> tuple[Path, Path]:
            return _resolve_ocr_models_kwargs(
                repo=args.hf_repo,
                revision=args.model_version,
                det_filename=args.det_filename,
                reco_filename=args.reco_filename,
                detection_path=det,
                recognition_path=reco,
            )

        if det is not None:
            return resolve()
        return _prepare_remote_files(
            "OCR",
            args.hf_repo,
            args.model_version,
            (args.det_filename, args.reco_filename),
            resolve,
            sidecars=_ocr_sidecars(args.det_filename, args.reco_filename),
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)  # noqa: T201  # CLI output
        sys.exit(1)


def det_source_descriptor(args: _HfArgs, det_path: Path) -> str:
    """Human-readable source string for the detection model."""
    if args.detection:
        return str(det_path)
    return f"{args.hf_repo}/{args.det_filename}@{short_revision(args.model_version)}"


def reco_source_descriptor(args: _HfArgs, reco_path: Path) -> str:
    """Human-readable source string for the recognition model."""
    if args.recognition:
        return str(reco_path)
    return f"{args.hf_repo}/{args.reco_filename}@{short_revision(args.model_version)}"


# ---------------------------------------------------------------------------
# Layout model — argparse adapter
# ---------------------------------------------------------------------------


def resolve_layout_source(args: _HfArgs) -> tuple[str | None, str | None, str]:
    """Return ``(repo, revision, descriptor)`` from argparse-shaped args."""
    return _resolve_layout_source_kwargs(args.layout_model, args.layout_checkpoint)


def prefetch_default_models(*, revision: str, layout_model: str) -> None:
    """Cache the default OCR and layout files without loading the models."""
    _ = _prepare_remote_files(
        "OCR",
        DEFAULT_HF_REPO,
        revision,
        (DEFAULT_DET_FILENAME, DEFAULT_RECO_FILENAME),
        lambda: _resolve_ocr_models_kwargs(
            repo=DEFAULT_HF_REPO,
            revision=revision,
            det_filename=DEFAULT_DET_FILENAME,
            reco_filename=DEFAULT_RECO_FILENAME,
        ),
        sidecars=_ocr_sidecars(DEFAULT_DET_FILENAME, DEFAULT_RECO_FILENAME),
    )
    layout_repo, layout_revision, _descriptor = _resolve_layout_source_kwargs(layout_model)
    if layout_repo is not None:
        _ = prefetch_layout_files(layout_repo, layout_revision)
