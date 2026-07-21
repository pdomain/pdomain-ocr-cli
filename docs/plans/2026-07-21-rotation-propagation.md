---
Status: active
Owner: CT
Created: 2026-07-21
Last verified: 2026-07-21
Kind: plan
---

# Rotation Propagation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Feed OCR-selected orientation into layout detection and illustration cropping.

**Architecture:** The upstream OCR result supplies the authoritative quarter-turn angle. The CLI validates it once and creates an oriented image shared by layout, debug, and crop consumers.

**Tech Stack:** Python, Pillow, DocTR, pytest, pdomain-book-tools

**Spec:** [rotation propagation design](../specs/2026-07-21-rotation-propagation-design.md)

---

### Task 1: Land the upstream result contract

**Files:**
- Modify in sibling repo: `../pdomain-book-tools/pdomain_book_tools/ocr/models.py`
- Test in sibling repo: `../pdomain-book-tools/tests/ocr/test_models.py`

- [ ] **Step 1: Add a failing serialization test**

```python
def test_page_result_round_trips_rotation() -> None:
    result = PageResult(..., rotation_degrees=90)
    assert PageResult.from_dict(result.to_dict()).rotation_degrees == 90
```

- [ ] **Step 2: Run the upstream test**

Run from `../pdomain-book-tools`: `make test-k K='round_trips_rotation' AI=1`
Expected: FAIL because the result has no rotation field.

- [ ] **Step 3: Add `rotation_degrees: Literal[0, 90, 180, 270] = 0`**

Persist the field through `to_dict` and `from_dict`, and set it from the OCR orientation decision.

- [ ] **Step 4: Verify and commit upstream**

Run: `make ci AI=1`
Expected: `✅`.

```bash
git add pdomain_book_tools tests
git commit -m "feat: expose OCR page rotation"
```

### Task 2: Orient the shared image in the CLI

**Files:**
- Modify: `pdomain_ocr_cli/_pipeline.py`
- Modify: `pdomain_ocr_cli/ocr_to_txt.py`
- Test: `tests/test_pipeline_integration.py`

- [ ] **Step 1: Add a failing unit test for quarter turns**

```python
@pytest.mark.parametrize(("degrees", "size"), [(0, (20, 10)), (90, (10, 20)), (180, (20, 10)), (270, (10, 20))])
def test_orient_image_uses_ocr_rotation(degrees, size):
    image = Image.new("RGB", (20, 10))
    assert orient_image(image, degrees).size == size
```

- [ ] **Step 2: Confirm the test fails**

Run: `uv run pytest -n auto tests/test_pipeline_integration.py -k orient_image -v`
Expected: FAIL because `orient_image` does not exist.

- [ ] **Step 3: Implement validated orientation**

```python
def orient_image(image: Image.Image, rotation_degrees: int) -> Image.Image:
    if rotation_degrees not in {0, 90, 180, 270}:
        raise ValueError(f"unsupported OCR rotation: {rotation_degrees}")
    return image if rotation_degrees == 0 else image.rotate(-rotation_degrees, expand=True)
```

Pass the result to every layout, debug, and crop call for that page.

- [ ] **Step 4: Add the rotated fixture regression**

Run the existing test helper on `tests/fixtures/rotated_page.png` with layout and illustration extraction enabled. Assert that the oriented dimensions reach the layout fake and each crop stays inside those dimensions.

- [ ] **Step 5: Verify and commit CLI changes**

Run: `make test-k K='rotation or crop or layout' AI=1 && make ci AI=1`
Expected: both commands print `✅`.

```bash
git add pdomain_ocr_cli tests
git commit -m "fix: align layout processing with OCR rotation"
```
