from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

from pdomain_ocr_cli._artifacts import (
    PageOutputTransaction,
    atomic_write_json_document,
    atomic_write_text,
)


def test_atomic_write_rejects_preexisting_symlink_temp_target(tmp_path: Path) -> None:
    target = tmp_path / "page.txt"
    outside = tmp_path / "outside.txt"
    outside.write_text("safe", encoding="utf-8")
    legacy_tmp = tmp_path / ".page.txt.tmp"
    legacy_tmp.symlink_to(outside)

    atomic_write_text(target, "new")

    assert target.read_text(encoding="utf-8") == "new"
    assert outside.read_text(encoding="utf-8") == "safe"
    assert legacy_tmp.is_symlink()


def test_atomic_write_uses_unique_temp_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "page.txt"
    opened: list[str] = []
    real_open = os.open

    def tracking_open(path, flags, mode=0o777):
        opened.append(str(path))
        return real_open(path, flags, mode)

    monkeypatch.setattr("pdomain_ocr_cli._artifacts.os.open", tracking_open)
    atomic_write_text(target, "hello")

    assert target.read_text(encoding="utf-8") == "hello"
    assert all(name != str(tmp_path / ".page.txt.tmp") for name in opened)


@pytest.mark.parametrize(("mask", "expected"), [(0o002, 0o664), (0o022, 0o644), (0o077, 0o600)])
def test_atomic_write_mode_follows_the_umask(tmp_path: Path, mask: int, expected: int) -> None:
    """The staging file carries an explicit mode, so the kernel masks it.

    A hardcoded mode would hand a 0644 file to someone who deliberately runs a
    private umask. Letting the umask decide keeps them private.
    """
    target = tmp_path / "page.txt"

    previous = os.umask(mask)
    try:
        atomic_write_text(target, "hello")
    finally:
        _ = os.umask(previous)

    assert target.stat().st_mode & 0o777 == expected


def test_atomic_write_json_document_uses_unique_temp_and_cleans_failure(
    tmp_path: Path,
) -> None:
    class BrokenDoc:
        def to_json_file(self, file_path: str | Path) -> None:
            Path(file_path).write_text("partial", encoding="utf-8")
            raise RuntimeError("boom")

    target = tmp_path / "page.json"

    with pytest.raises(RuntimeError, match="boom"):
        atomic_write_json_document(target, BrokenDoc())

    assert not target.exists()
    assert not list(tmp_path.glob(".page.json.*.tmp"))


def test_atomic_write_json_document_mode_follows_the_umask(tmp_path: Path) -> None:
    """Same rule for the JSON writer: no chmod, so the umask decides."""

    class Doc:
        def to_json_file(self, file_path: str | Path) -> None:
            Path(file_path).write_text("{}", encoding="utf-8")

    target = tmp_path / "page.json"

    previous = os.umask(0o022)
    try:
        atomic_write_json_document(target, Doc())
    finally:
        _ = os.umask(previous)

    assert target.stat().st_mode & 0o777 == 0o644


def _fail_for(
    real_promote: Callable[[Path, Path], None], failing_path: Path
) -> Callable[[Path, Path], None]:
    """Promote normally, except raise OSError("forced") for one destination."""

    def _promote(destination: Path, staged: Path) -> None:
        if destination == failing_path:
            raise OSError("forced")
        real_promote(destination, staged)

    return _promote


def test_page_output_transaction_commit_writes_all_staged_artifacts(tmp_path: Path) -> None:
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")

    transaction.commit()

    assert json_path.read_bytes() == b"new-json"
    assert txt_path.read_text(encoding="utf-8") == "new-text"


def test_page_output_transaction_successful_overwrite_leaves_only_final_artifacts(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    _ = json_path.write_bytes(b"old-json")
    _ = txt_path.write_text("old-text", encoding="utf-8")

    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")
    transaction.commit()

    assert json_path.read_bytes() == b"new-json"
    assert txt_path.read_text(encoding="utf-8") == "new-text"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["page.json", "page.txt"]


def test_page_output_transaction_abort_removes_files_staged_before_commit(
    tmp_path: Path,
) -> None:
    target = tmp_path / "page.json"
    transaction = PageOutputTransaction()
    transaction.add_bytes(target, b"staged")

    transaction.abort()

    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_page_output_transaction_abort_after_commit_keeps_destination(tmp_path: Path) -> None:
    target = tmp_path / "page.txt"
    transaction = PageOutputTransaction()
    transaction.add_text(target, "kept")
    transaction.commit()

    transaction.abort()

    assert target.read_text(encoding="utf-8") == "kept"
    assert list(tmp_path.iterdir()) == [target]


def test_page_output_transaction_add_bytes_cleans_up_failed_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "page.json"
    transaction = PageOutputTransaction()

    def boom(_fd: int, _data: bytes) -> int:
        raise OSError("staging boom")

    monkeypatch.setattr("pdomain_ocr_cli._artifacts.os.write", boom)

    with pytest.raises(OSError, match="staging boom"):
        transaction.add_bytes(target, b"data")

    assert list(tmp_path.iterdir()) == []


def test_page_output_transaction_removes_new_sidecars_when_text_promotion_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")
    real_promote = transaction._promote

    monkeypatch.setattr(transaction, "_promote", _fail_for(real_promote, txt_path))
    with pytest.raises(OSError, match="forced"):
        transaction.commit()
    assert not json_path.exists()
    assert not txt_path.exists()


def test_page_output_transaction_restores_overwritten_files_when_text_promotion_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    _ = json_path.write_bytes(b"old-json")
    _ = txt_path.write_text("old-text", encoding="utf-8")
    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")
    real_promote = transaction._promote

    monkeypatch.setattr(transaction, "_promote", _fail_for(real_promote, txt_path))
    with pytest.raises(OSError, match="forced"):
        transaction.commit()
    assert json_path.read_bytes() == b"old-json"
    assert txt_path.read_text(encoding="utf-8") == "old-text"


def test_page_output_transaction_rolls_back_when_fsync_parent_dir_fails_after_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    txt_path = tmp_path / "page.txt"
    transaction = PageOutputTransaction()
    transaction.add_text(txt_path, "new-text")

    def boom_fsync_parent_dir(_path: Path) -> None:
        raise OSError("fsync boom")

    monkeypatch.setattr("pdomain_ocr_cli._artifacts._fsync_parent_dir", boom_fsync_parent_dir)

    with pytest.raises(OSError, match="fsync boom"):
        transaction.commit()

    assert not txt_path.exists()
    assert list(tmp_path.iterdir()) == []


def test_page_output_transaction_rolls_back_on_keyboard_interrupt_during_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    _ = json_path.write_bytes(b"old-json")
    _ = txt_path.write_text("old-text", encoding="utf-8")

    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")
    real_promote = transaction._promote

    def flaky_promote(destination: Path, staged: Path) -> None:
        if destination == txt_path:
            raise KeyboardInterrupt
        real_promote(destination, staged)

    monkeypatch.setattr(transaction, "_promote", flaky_promote)

    with pytest.raises(KeyboardInterrupt):
        transaction.commit()

    assert json_path.read_bytes() == b"old-json"
    assert txt_path.read_text(encoding="utf-8") == "old-text"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["page.json", "page.txt"]


def test_page_output_transaction_keyboard_interrupt_with_failing_rollback_stays_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")
    real_promote = transaction._promote

    def flaky_promote(destination: Path, staged: Path) -> None:
        if destination == txt_path:
            raise KeyboardInterrupt
        real_promote(destination, staged)

    monkeypatch.setattr(transaction, "_promote", flaky_promote)

    real_unlink = Path.unlink

    def flaky_unlink(self: Path, missing_ok: bool = False) -> None:
        if self == json_path:
            raise OSError("rollback unlink boom")
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    with pytest.raises(KeyboardInterrupt) as excinfo:
        transaction.commit()

    assert not isinstance(excinfo.value, BaseExceptionGroup)
    notes = excinfo.value.__notes__
    assert any("rollback unlink boom" in note for note in notes)


def test_page_output_transaction_raises_exception_group_when_rollback_also_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    _ = json_path.write_bytes(b"old-json")
    _ = txt_path.write_text("old-text", encoding="utf-8")
    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")
    real_promote = transaction._promote

    def flaky_promote(destination: Path, staged: Path) -> None:
        if destination == txt_path:
            raise OSError("forced")
        real_promote(destination, staged)

    monkeypatch.setattr(transaction, "_promote", flaky_promote)

    real_unlink = Path.unlink

    def flaky_unlink(self: Path, missing_ok: bool = False) -> None:
        if self == json_path:
            raise OSError("rollback unlink boom")
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    real_replace = Path.replace

    def flaky_replace(self: Path, target: Path) -> Path:
        if Path(target) == txt_path:
            raise OSError("rollback replace boom")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)

    with pytest.raises(ExceptionGroup) as excinfo:
        transaction.commit()

    group = excinfo.value
    assert "artifact promotion and rollback failed" in str(group)
    assert len(group.exceptions) == 3
    assert isinstance(group.exceptions[0], OSError)
    assert str(group.exceptions[0]) == "forced"
    assert json_path.read_bytes() == b"old-json"


def test_page_output_transaction_rollback_survives_non_oserror_unlink_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")
    real_promote = transaction._promote

    monkeypatch.setattr(transaction, "_promote", _fail_for(real_promote, txt_path))

    real_unlink = Path.unlink

    def flaky_unlink(self: Path, missing_ok: bool = False) -> None:
        if self == json_path:
            raise RuntimeError("permission-like cleanup failure")
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    with pytest.raises(BaseExceptionGroup) as excinfo:
        transaction.commit()

    group = excinfo.value
    assert isinstance(group.exceptions[0], OSError)
    assert str(group.exceptions[0]) == "forced"
    assert any(
        isinstance(exc, RuntimeError) and "permission-like" in str(exc)
        for exc in group.exceptions[1:]
    )


def test_page_output_transaction_discard_staged_survives_non_oserror_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    json_path = tmp_path / "page.json"
    txt_path = tmp_path / "page.txt"
    transaction = PageOutputTransaction()
    transaction.add_bytes(json_path, b"new-json")
    transaction.add_text(txt_path, "new-text")
    real_promote = transaction._promote

    monkeypatch.setattr(transaction, "_promote", _fail_for(real_promote, txt_path))

    real_unlink = Path.unlink

    def flaky_unlink(self: Path, missing_ok: bool = False) -> None:
        if self.suffix == ".stage":
            raise RuntimeError("stage cleanup failure")
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    with pytest.raises(BaseExceptionGroup) as excinfo:
        transaction.commit()

    group = excinfo.value
    assert isinstance(group.exceptions[0], OSError)
    assert str(group.exceptions[0]) == "forced"
    assert any(isinstance(exc, RuntimeError) for exc in group.exceptions[1:])
