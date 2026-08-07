---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: plan
---

# Image Resource Limits Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reject oversized compressed and decoded image inputs before OCR work.

**Architecture:** A pure admission helper checks stat size and Pillow dimensions. Collection records rejected paths through the current per-file error channel and batches only accepted files.

**Tech Stack:** Python, Pillow, pytest

**Spec:** [image resource limits design](../specs/2026-07-21-image-resource-limits-design.md)

---

## Task 1: Add and enforce admission limits

**Files:**

- Create: `pdomain_ocr_cli/_image_limits.py`
- Create: `tests/test_image_limits.py`
- Modify: `pdomain_ocr_cli/_pipeline.py`

- [ ] **Step 1: Add failing boundary tests**

```python
def test_accepts_exact_limits(tmp_path, monkeypatch):
    path = tmp_path / "page.png"
    path.write_bytes(b"x")
    monkeypatch.setattr(
        pathlib.Path, "stat", lambda self: SimpleNamespace(st_size=100 * 1024 * 1024)
    )
    assert validate_image_limits(path, dimensions=(10_000, 10_000)) is None


def test_rejects_one_pixel_over_limit(tmp_path):
    with pytest.raises(ImageLimitError, match="100000001 pixels"):
        validate_image_limits(tmp_path / "page.png", dimensions=(100_000_001, 1))
```

Add a byte-size case at `100 * 1024 * 1024 + 1`.

- [ ] **Step 2: Confirm tests fail**

Run: `uv run pytest -n auto tests/test_image_limits.py -v`
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement the pure validator**

```python
MAX_IMAGE_BYTES = 100 * 1024 * 1024
MAX_IMAGE_PIXELS = 100_000_000


def validate_image_limits(path: Path, *, dimensions: tuple[int, int]) -> None:
    size = path.stat().st_size
    if size > MAX_IMAGE_BYTES:
        raise ImageLimitError(f"{path}: {size} bytes exceeds {MAX_IMAGE_BYTES}")
    pixels = dimensions[0] * dimensions[1]
    if pixels > MAX_IMAGE_PIXELS:
        raise ImageLimitError(f"{path}: {pixels} pixels exceeds {MAX_IMAGE_PIXELS}")
```

- [ ] **Step 4: Wire checks before batching**

Stat before `Image.open`. After opening, read only `image.size`, call the validator, and close rejected images. Use the existing error reporter and continue to the next file.

- [ ] **Step 5: Verify focused behavior**

Run: `make test-k K='image_limits or collect_images' AI=1`
Expected: PASS.

## Task 2: Document and verify limits

**Files:**

- Modify: `docs/usage/cli-usage.md`
- Modify: `tests/test_main_errors.py`

- [ ] **Step 1: Add a CLI rejection test**

Create an oversized-dimension Pillow stub, run `main`, and assert stderr names the path, pixel count, and limit while a second valid input still produces text.

- [ ] **Step 2: Document fixed limits**

Add a section stating the 100 MiB compressed limit, 100-million-pixel decoded limit, per-file continuation behavior, and absence of a processing timeout.

- [ ] **Step 3: Run all gates and commit**

Run: `make ci AI=1`
Expected: `✅`.

```bash
git add pdomain_ocr_cli/_image_limits.py pdomain_ocr_cli/_pipeline.py tests/test_image_limits.py tests/test_main_errors.py docs/usage/cli-usage.md
git commit -m "feat: enforce image input resource limits"
```
