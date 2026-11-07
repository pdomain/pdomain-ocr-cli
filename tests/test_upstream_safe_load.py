"""Tripwire: fail if the installed ``pdomain_book_tools`` ever loads a
PyTorch checkpoint unsafely.

``pdomain_book_tools`` (>= 0.18.0) defends checkpoint deserialization by
always invoking ``torch.load`` -- however it is imported or aliased --
with a literal ``weights_only=True`` keyword; see
``pdomain_book_tools.ocr.doctr_support.get_finetuned_torch_doctr_predictor``,
which defaults its injectable loader to
``functools.partial(torch.load, weights_only=True)``. This CLI does not
duplicate that deserialization logic (see
``docs/specs/2026-07-21-model-provenance-design.md``), so it depends on the
upstream contract holding across upgrades.

This test scans every ``.py`` file the *installed* package ships -- not a
hard-coded module path -- and fails the moment any of them invokes
``torch.load`` without a literal ``weights_only=True`` keyword, whether the
call is direct, via ``from torch import load as X``, or wrapped in
``functools.partial``.

The scan is AST-based (not a substring match) precisely so it:

- does NOT false-positive on unrelated ``load`` functions such as
  ``from json import load`` (present in ``pdomain_book_tools.ocr.page``), or
  on the word "torch" appearing in prose/other torch APIs like
  ``torch.tensor`` / ``@torch.inference_mode()``.
- does NOT false-negative on the real aliasing pdomain_book_tools uses today
  (``from torch import load as _torch_load_fn`` then
  ``functools.partial(_torch_load_fn, weights_only=True)``) -- a plain
  ``"torch.load(" in source`` substring check would miss this entirely,
  which is why the original plan's literal assertion does not hold.

Known, deliberate blind spots (a static per-module scan can't do better
without becoming a bespoke type checker -- not fixed here):

- Re-aliasing a name already bound via ``from torch import load as X`` to a
  THIRD name (``Y = X``) and calling ``Y(...)`` is not tracked.
- A non-literal ``weights_only=some_variable`` is always treated as unsafe
  (its runtime value can't be proven statically) -- this trades occasional
  false positives for never silently missing a real regression.
- Aliases are tracked per module, not per lexical scope, so two different
  functions in one file binding the same alias name to two different things
  would confuse the scanner. Not a pattern used anywhere in
  pdomain_book_tools today.
"""

from __future__ import annotations

import ast
import importlib
import pickle
import sys
import textwrap
import types
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, override

import pytest

from pdomain_ocr_cli import ocr_to_txt

if TYPE_CHECKING:
    from collections.abc import Iterator

_SCANNED_PACKAGE = "pdomain_book_tools"


@dataclass(frozen=True, slots=True)
class UnsafeLoadCall:
    """One call site that invokes (or wraps) ``torch.load`` unsafely."""

    path: str
    lineno: int
    detail: str


def _package_python_files(package_name: str) -> Iterator[Path]:
    """Yield every ``.py`` file under the installed package's directory tree."""
    package = importlib.import_module(package_name)
    if package.__file__ is None:
        msg = f"{package_name!r} has no importable __file__; cannot scan it."
        raise RuntimeError(msg)
    package_dir = Path(package.__file__).resolve().parent
    yield from sorted(package_dir.rglob("*.py"))


class _TorchLoadAuditor(ast.NodeVisitor):
    """Collect unsafe ``torch.load`` call/wrap sites in one module's AST.

    Tracks, at module granularity (see the module docstring's blind-spots
    section):

    - names bound to the ``torch`` module itself (``import torch as X``)
    - names bound directly to ``torch.load`` (``from torch import load as X``)
    - names bound to ``functools.partial`` (module import or direct import)

    then walks every ``Call`` node and flags:

    - a direct call to a torch-load-bound name/attribute missing a literal
      ``weights_only=True`` keyword
    - a ``functools.partial(...)`` call wrapping a torch-load-bound
      reference missing a literal ``weights_only=True`` keyword
    """

    def __init__(self, path: Path) -> None:
        self._path: Path = path
        self._torch_module_names: set[str] = set()
        self._serialization_module_names: set[str] = set()
        self._torch_load_names: set[str] = set()
        self._partial_module_names: set[str] = set()
        self._partial_names: set[str] = set()
        self.violations: list[UnsafeLoadCall] = []

    def collect_bindings(self, tree: ast.Module) -> None:
        """First pass: record every import binding before any call is checked.

        A separate pass means a call that appears above its import in the
        source, such as a function body above a module-level import, is
        still resolved.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self._bind_import(node)
            elif isinstance(node, ast.ImportFrom):
                self._bind_import_from(node)

    def _bind_import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "functools":
                self._partial_module_names.add(alias.asname or alias.name)
            elif alias.name == "torch.serialization" and alias.asname is not None:
                self._serialization_module_names.add(alias.asname)
            elif alias.name == "torch" or alias.name.startswith("torch."):
                # ``import torch.x`` without ``as`` binds the name ``torch``.
                self._torch_module_names.add(alias.asname or "torch")

    def _bind_import_from(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            bound = alias.asname or alias.name
            if node.module in {"torch", "torch.serialization"} and alias.name == "load":
                self._torch_load_names.add(bound)
            elif node.module == "torch" and alias.name == "serialization":
                self._serialization_module_names.add(bound)
            elif node.module == "functools" and alias.name == "partial":
                self._partial_names.add(bound)

    def _is_torch_load_ref(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._torch_load_names
        if isinstance(node, ast.Attribute) and node.attr == "load":
            owner = node.value
            if isinstance(owner, ast.Name):
                return (
                    owner.id in self._torch_module_names
                    or owner.id in self._serialization_module_names
                )
            # ``torch.serialization.load``
            return (
                isinstance(owner, ast.Attribute)
                and owner.attr == "serialization"
                and isinstance(owner.value, ast.Name)
                and owner.value.id in self._torch_module_names
            )
        return False

    def _is_partial_ref(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self._partial_names
        if isinstance(node, ast.Attribute):
            return node.attr == "partial" and (
                isinstance(node.value, ast.Name) and node.value.id in self._partial_module_names
            )
        return False

    @staticmethod
    def _has_weights_only_true(keywords: list[ast.keyword]) -> bool:
        for kw in keywords:
            if kw.arg == "weights_only":
                return isinstance(kw.value, ast.Constant) and kw.value.value is True
        return False

    @override
    def visit_Call(self, node: ast.Call) -> None:
        if self._is_torch_load_ref(node.func):
            if not self._has_weights_only_true(node.keywords):
                self.violations.append(
                    UnsafeLoadCall(
                        path=str(self._path),
                        lineno=node.lineno,
                        detail="direct torch.load call missing weights_only=True",
                    )
                )
        elif self._is_partial_ref(node.func):
            wraps_torch_load = any(self._is_torch_load_ref(arg) for arg in node.args) or any(
                kw.arg == "func" and self._is_torch_load_ref(kw.value) for kw in node.keywords
            )
            if wraps_torch_load and not self._has_weights_only_true(node.keywords):
                self.violations.append(
                    UnsafeLoadCall(
                        path=str(self._path),
                        lineno=node.lineno,
                        detail="functools.partial(torch.load, ...) missing weights_only=True",
                    )
                )
        self.generic_visit(node)


def _find_unsafe_torch_loads(source: str, path: Path) -> list[UnsafeLoadCall]:
    """Return every unsafe ``torch.load`` call/wrap site found in ``source``."""
    tree = ast.parse(source, filename=str(path))
    auditor = _TorchLoadAuditor(path)
    auditor.collect_bindings(tree)
    auditor.visit(tree)
    return auditor.violations


def test_installed_pdomain_book_tools_never_loads_torch_checkpoints_unsafely() -> None:
    """Guard the upstream ``weights_only=True`` safe-loading contract.

    pdomain-ocr-cli relies on ``pdomain_book_tools`` to load OCR/layout
    PyTorch checkpoints safely. This scans the installed package rather
    than importing a hard-coded module path, so it keeps working if the
    safe-loading code moves to a different file inside pdomain_book_tools.
    """
    paths = list(_package_python_files(_SCANNED_PACKAGE))
    assert paths, f"found no .py files to scan in {_SCANNED_PACKAGE!r}"
    violations: list[UnsafeLoadCall] = []
    for path in paths:
        # A file that fails to parse fails this test with its path: an
        # unscannable file cannot be shown to be safe.
        source = path.read_text(encoding="utf-8")
        violations.extend(_find_unsafe_torch_loads(source, path))

    assert not violations, "unsafe torch.load call(s) found:\n" + "\n".join(
        f"  {v.path}:{v.lineno}: {v.detail}" for v in violations
    )


# ---------------------------------------------------------------------------
# Scanner self-test: proves the tripwire can actually fire, on synthetic
# sources shaped like both the real upstream pattern and plausible
# regressions of it.
# ---------------------------------------------------------------------------

_SAFE_DIRECT_CALL = textwrap.dedent("""
    import torch

    def load_checkpoint(path):
        return torch.load(path, weights_only=True)
    """)

_SAFE_ALIASED_PARTIAL = textwrap.dedent("""
    from functools import partial
    from torch import load as _torch_load_fn

    torch_load = partial(_torch_load_fn, weights_only=True)
    """)

_UNRELATED_JSON_LOAD = textwrap.dedent("""
    from json import load

    def read_config(fh):
        return load(fh)
    """)

_UNRELATED_TORCH_USAGE = textwrap.dedent("""
    import torch

    @torch.inference_mode()
    def to_tensor(size):
        return torch.tensor([size])
    """)

_UNSAFE_DIRECT_CALL = textwrap.dedent("""
    import torch

    def load_checkpoint(path):
        return torch.load(path)
    """)

_UNSAFE_ALIASED_PARTIAL = textwrap.dedent("""
    from functools import partial
    from torch import load as _torch_load_fn

    torch_load = partial(_torch_load_fn)
    """)

_UNSAFE_ALIASED_DIRECT_CALL = textwrap.dedent("""
    from torch import load as _torch_load_fn

    def load_checkpoint(path):
        return _torch_load_fn(path, weights_only=False)
    """)

_UNSAFE_SERIALIZATION_ATTRIBUTE = textwrap.dedent("""
    import torch.serialization

    def load_checkpoint(path):
        return torch.serialization.load(path)
    """)

_UNSAFE_SERIALIZATION_MODULE_ALIAS = textwrap.dedent("""
    from torch import serialization as ser

    def load_checkpoint(path):
        return ser.load(path)
    """)

_UNSAFE_SERIALIZATION_IMPORT_AS = textwrap.dedent("""
    import torch.serialization as s

    def load_checkpoint(path):
        return s.load(path)
    """)

_UNSAFE_SERIALIZATION_FROM_IMPORT = textwrap.dedent("""
    from torch.serialization import load

    def load_checkpoint(path):
        return load(path)
    """)

_UNSAFE_CALL_ABOVE_IMPORT = textwrap.dedent("""
    def load_checkpoint(path):
        return _torch_load_fn(path)

    from torch import load as _torch_load_fn
    """)


@pytest.mark.parametrize(
    "source",
    [_SAFE_DIRECT_CALL, _SAFE_ALIASED_PARTIAL, _UNRELATED_JSON_LOAD, _UNRELATED_TORCH_USAGE],
    ids=[
        "direct-call-weights-only-true",
        "aliased-partial-weights-only-true",
        "unrelated-json-load",
        "unrelated-torch-usage",
    ],
)
def test_find_unsafe_torch_loads_accepts_safe_patterns(source: str) -> None:
    assert _find_unsafe_torch_loads(source, Path("synthetic.py")) == []


@pytest.mark.parametrize(
    "source",
    [
        _UNSAFE_DIRECT_CALL,
        _UNSAFE_ALIASED_PARTIAL,
        _UNSAFE_ALIASED_DIRECT_CALL,
        _UNSAFE_SERIALIZATION_ATTRIBUTE,
        _UNSAFE_SERIALIZATION_MODULE_ALIAS,
        _UNSAFE_SERIALIZATION_IMPORT_AS,
        _UNSAFE_SERIALIZATION_FROM_IMPORT,
        _UNSAFE_CALL_ABOVE_IMPORT,
    ],
    ids=[
        "direct-call-missing-kwarg",
        "aliased-partial-missing-kwarg",
        "aliased-direct-call-weights-only-false",
        "torch-serialization-attribute",
        "torch-serialization-module-alias",
        "torch-serialization-import-as",
        "torch-serialization-from-import",
        "call-above-module-level-import",
    ],
)
def test_find_unsafe_torch_loads_flags_unsafe_patterns(source: str) -> None:
    violations = _find_unsafe_torch_loads(source, Path("synthetic.py"))
    assert violations


def test_find_unsafe_torch_loads_matches_real_upstream_pattern() -> None:
    """Regression pin: the exact aliasing shape ``doctr_support.py`` uses
    today is recognized as safe by the scanner (belt-and-braces alongside
    the real package scan above).
    """
    source = textwrap.dedent("""
        def get_finetuned_torch_doctr_predictor(torch_load=None):
            from torch import load as _torch_load_fn

            if torch_load is None:
                from functools import partial as _partial

                torch_load = _partial(_torch_load_fn, weights_only=True)

            det_params = torch_load("det.pt", map_location="cpu")
            return det_params
        """)
    assert _find_unsafe_torch_loads(source, Path("synthetic.py")) == []


# ---------------------------------------------------------------------------
# Behavioral contract: the scan above proves the source looks safe; these
# prove the real loader refuses a pickled object, and that this CLI does not
# bypass the safe default by passing its own loader.
# ---------------------------------------------------------------------------


class _Marker:
    """Any non-tensor class; ``weights_only=True`` refuses to unpickle it."""


def test_upstream_loader_refuses_pickled_objects(tmp_path: Path) -> None:
    """With ``weights_only=True``, ``torch.load`` raises ``UnpicklingError``.

    If upstream dropped it, the load would succeed and upstream's state-dict
    validation would raise ``ValueError`` instead, failing this test.
    """
    from pdomain_book_tools.ocr.doctr_support import get_finetuned_torch_doctr_predictor
    from torch import save

    det = tmp_path / "det.pt"
    reco = tmp_path / "reco.pt"
    # Both checkpoints are unsafe pickles, so the test does not depend on
    # which one upstream loads first.
    save(_Marker(), det)
    save(_Marker(), reco)
    with pytest.raises(pickle.UnpicklingError):
        _ = get_finetuned_torch_doctr_predictor(det, reco, device="cpu")


def test_cli_does_not_override_upstream_torch_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI must call the predictor with only the two checkpoint paths.

    Any extra argument, positional or keyword, could replace the safe loader.
    """
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _fake_predictor(*args: object, **kwargs: object) -> object:
        calls.append((args, kwargs))
        return object()

    fake_module = types.ModuleType("pdomain_book_tools.ocr.doctr_support")
    monkeypatch.setattr(
        fake_module, "get_finetuned_torch_doctr_predictor", _fake_predictor, raising=False
    )
    monkeypatch.setitem(sys.modules, "pdomain_book_tools.ocr.doctr_support", fake_module)

    det, reco = Path("det.pt"), Path("reco.pt")
    _ = ocr_to_txt._load_predictor(det, reco)  # pyright: ignore[reportPrivateUsage]  # the wrapper is the unit under test

    assert calls == [((det, reco), {})]
