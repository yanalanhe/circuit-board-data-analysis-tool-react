# Story 8.1: Implement Report Rendering Node

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the backend to take successful execution output (charts + text) and format it for display,
So that the frontend can render a complete, polished report.

## Acceptance Criteria

1. **Given** successful code execution with chart output
   **When** the subprocess produces `CHART:<base64_png>` lines on stdout
   **Then** each chart is decoded from base64 and stored as bytes in `pipeline_state["report_charts"]`

2. **Given** successful execution with text output (trend analysis, summary statistics)
   **When** stdout is captured
   **Then** all non-`CHART:` lines are concatenated and stored in `pipeline_state["report_text"]`

3. **Given** the `render_report` node in `pipeline/nodes/reporter.py`
   **When** it runs
   **Then** it formats the charts and text into a structured report payload

4. **Given** large data that was downsampled
   **When** the report is rendered
   **Then** a note is included: "Downsampled to 10,000 points using uniform stride" (context for the user about data reduction)

5. **Given** the report payload
   **When** it is stored in the pipeline state
   **Then** it includes: `report_charts: [bytes]`, `report_text: str`, `pipeline_state["execution_success"] = True`

## Tasks / Subtasks

- [x] Verify AC #1 & #2: `executor.py` already parses CHART: lines and populates report_charts/report_text (AC: #1, #2)
  - [x] Confirm `_parse_stdout()` in `pipeline/nodes/executor.py` decodes `CHART:<base64_png>` lines → `list[bytes]`
  - [x] Confirm non-CHART stdout lines are joined and stored in `report_text`
  - [x] Run `tests/test_executor.py` — confirm chart parsing tests pass
- [x] Verify AC #3 & #5: reporter.py node exists and pipeline state fields are correct (AC: #3, #5)
  - [x] Confirm `pipeline/nodes/reporter.py::render_report()` is wired in graph.py and runs after execute_code success
  - [x] Confirm `pipeline/state.py` has `report_charts: list[bytes]` and `report_text: str` fields
  - [x] Run `tests/test_reporter.py` — all existing contract/immutability/boundary tests pass
- [x] Implement AC #4: Add downsampling note to reporter.py (AC: #4)
  - [x] In `reporter.py::render_report()`, check `state.get("recovery_applied")` — if truthy, append downsample note to `report_text`
  - [x] Return `{"report_text": updated_text}` only when `recovery_applied` is set; return `{}` otherwise (LangGraph merge pattern)
  - [x] Add tests to `tests/test_reporter.py`: `test_render_report_adds_downsample_note_when_recovery_applied`
  - [x] Add tests: `test_render_report_no_note_when_no_recovery_applied` (regression guard)
  - [x] Run full test suite and confirm no regressions

## Dev Notes

### Critical Insight — Mostly a Verification Story with One Gap Fix

Based on analysis of the existing codebase, ACs #1, #2, #3 (partial), and #5 are **already implemented**. The pipeline wiring for `render_report` is complete. Only AC #4 (downsampling note) requires a small code change in `reporter.py`.

**The existing implementation breakdown:**
- `executor.py::_parse_stdout()` already handles CHART: prefix decoding (ACs #1, #2)
- `reporter.py::render_report()` exists as a passthrough node returning `{}` (AC #3 partial — node exists but doesn't add the downsample note)
- `pipeline/state.py` already has all required fields (AC #5)
- `graph.py` already wires `render_report` → END

### AC #4 Implementation — Downsampling Note in reporter.py

Current `reporter.py` returns `{}` unconditionally. It needs to check `recovery_applied` and append the note to `report_text` when downsampling was applied.

**Implementation pattern:**
```python
# pipeline/nodes/reporter.py
def render_report(state: PipelineState) -> dict:
    if state.get("recovery_applied"):
        existing_text = state.get("report_text", "")
        note = "Downsampled to 10,000 points using uniform stride"
        separator = "\n\n" if existing_text else ""
        return {"report_text": existing_text + separator + note}
    return {}
```

**Key constraints:**
- MUST NOT import streamlit (module boundary rule — `pipeline/nodes/` are pure Python)
- Return ONLY changed keys — LangGraph merges automatically (`return {**state, ...}` is an anti-pattern)
- `recovery_applied` is set by `utils/large_data.py` when downsampling is applied; it's a string (non-empty when applied)
- [Source: pipeline/state.py lines 27–29, architecture.md#LangGraph-node-return, architecture.md#Module-Boundaries]

### AC #1 & #2 — Already Implemented: executor.py stdout parsing

```python
# pipeline/nodes/executor.py — _parse_stdout() function
def _parse_stdout(stdout: str) -> tuple[list[bytes], str]:
    charts: list[bytes] = []
    text_lines: list[str] = []
    for line in stdout.split('\n'):
        if line.startswith("CHART:"):
            try:
                charts.append(base64.b64decode(line[6:]))
            except Exception:
                pass  # skip malformed CHART: lines
        else:
            text_lines.append(line)
    report_text = "\n".join(text_lines).strip()
    return charts, report_text
```

On success path, executor.py returns:
```python
return {
    "report_charts": report_charts,   # list[bytes] — PNG bytes
    "report_text": report_text,        # str — non-CHART stdout
    "execution_output": execution_output,
    "execution_success": True,
    "error_messages": existing_errors + new_errors,
}
```
[Source: pipeline/nodes/executor.py lines 44–64, 168–176]

### AC #3 — Pipeline Graph Wiring

`render_report` is wired in `pipeline/graph.py`:
```python
from pipeline.nodes.reporter import render_report
_builder.add_node("render_report", render_report)
_builder.add_edge("render_report", END)
```

`route_after_execution` routes to `"render_report"` when `execution_success` is True or max replans exhausted:
```python
def route_after_execution(state: PipelineState) -> str:
    if state["execution_success"]:
        return "render_report"
    elif state["retry_count"] >= _MAX_REPLAN_RETRY:   # _MAX_REPLAN_RETRY = 6
        return "render_report"  # safety fallback
    ...
```
[Source: pipeline/graph.py lines 25, 60–79, 94, 129]

### PipelineState Fields Relevant to This Story

```python
class PipelineState(TypedDict):
    execution_success: bool      # Set True by execute_code on subprocess exit 0
    report_charts: list[bytes]   # PNG bytes via BytesIO from subprocess (FR19)
    report_text: str             # written trend analysis (FR20)
    large_data_detected: bool    # Set by upload handler via utils/large_data.py
    large_data_message: str      # Human-readable warning message
    recovery_applied: str        # Set when downsampling was applied (non-empty string)
```
[Source: pipeline/state.py]

### LangGraph Node Return Convention (MANDATORY)

- Nodes return ONLY changed keys as a dict — LangGraph merges automatically
- `return {**state, "key": value}` is an ANTI-PATTERN — NEVER do this
- Correct: `return {"report_text": updated_text}` or `return {}`
- [Source: architecture.md#LangGraph-node-return]

### Module Boundary Rule (MANDATORY)

- `pipeline/nodes/reporter.py` MUST NOT import `streamlit`
- It is a pure Python module testable without Streamlit running
- Rendering logic (st.image, st.markdown) lives in `streamlit_app.py`
- [Source: architecture.md#Module-Boundaries]

### Subprocess Chart Output Convention (for Context)

The generated code instructs matplotlib to output charts as base64 via CHART: prefix:
```python
# Generated code pattern (from codegen.py system prompt)
import base64, io
buf = io.BytesIO()
plt.savefig(buf, format='png')
print("CHART:" + base64.b64encode(buf.getvalue()).decode())
```
This is the "CHART:" prefix pattern that executor.py's `_parse_stdout()` decodes.
[Source: pipeline/nodes/codegen.py lines 33–35, architecture.md#CHART-prefix]

### Existing Tests Coverage

`tests/test_reporter.py` has 10 tests covering:
- Returns dict / returns empty dict passthrough
- Empty state / charts only / text only
- Does not raise on valid state
- State immutability (does not mutate input)
- Module boundary (no streamlit import)

**All existing tests expect `render_report()` to return `{}`** — they use default `recovery_applied: ""` which is falsy. Adding the downsample note logic will NOT break these tests.

New tests needed:
1. `test_render_report_adds_downsample_note_when_recovery_applied` — verify note is appended to report_text when `recovery_applied` is non-empty
2. `test_render_report_no_note_when_no_recovery_applied` — regression guard: `recovery_applied = ""` still returns `{}`
3. `test_render_report_appends_to_existing_report_text` — note is appended after existing text with `\n\n` separator
4. `test_render_report_note_when_empty_report_text` — when `report_text = ""` and `recovery_applied` set, note appears without leading separator

### Project Structure Notes

**Files to touch:**
```
pipeline/
  nodes/
    reporter.py     # PRIMARY — add downsample note logic (AC #4)
  state.py          # READ ONLY — verify PipelineState fields
  graph.py          # READ ONLY — verify wiring

tests/
  test_reporter.py  # ADD tests for downsample note behavior (AC #4)
  test_executor.py  # RUN — chart parsing tests (AC #1, #2 verification)
```

**No new files required.**

### References

- **Epic 8 full spec:** [Source: _bmad-output/planning-artifacts/epics.md#Epic-8]
- **Story 8.1 ACs:** [Source: _bmad-output/planning-artifacts/epics.md#Story-8.1]
- **Architecture FR19–22:** [Source: _bmad-output/planning-artifacts/architecture.md]
- **LangGraph node return pattern:** [Source: _bmad-output/planning-artifacts/architecture.md#LangGraph-node-return]
- **Module boundary rules:** [Source: _bmad-output/planning-artifacts/architecture.md#Module-Boundaries]
- **CHART: prefix pattern:** [Source: pipeline/nodes/codegen.py lines 33–35]
- **executor.py _parse_stdout():** [Source: pipeline/nodes/executor.py lines 44–64]
- **executor.py success path:** [Source: pipeline/nodes/executor.py lines 168–176]
- **reporter.py current implementation:** [Source: pipeline/nodes/reporter.py]
- **graph.py wiring:** [Source: pipeline/graph.py lines 25, 60–79, 94, 129]
- **PipelineState schema:** [Source: pipeline/state.py]
- **Existing reporter tests:** [Source: tests/test_reporter.py]
- **Story 7.2 (retry/replan) — previous story learnings:** [Source: _bmad-output/implementation-artifacts/7-2-implement-retry-adaptive-replan.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Story 8.1 implemented: 2026-03-28
- `pipeline/nodes/executor.py::_parse_stdout()` verified: decodes `CHART:<base64_png>` lines → `list[bytes]`; non-CHART stdout → `report_text` (lines 43–68)
- `pipeline/nodes/reporter.py` verified: exists as passthrough node in graph.py; wired `execute_code → render_report → END`
- `pipeline/state.py` verified: `report_charts: list[bytes]`, `report_text: str`, `recovery_applied: str` fields present
- AC #4 gap confirmed: `reporter.py` returned `{}` unconditionally, not appending downsample note
- AC #4 fix applied: added `_DOWNSAMPLE_NOTE` constant + `state.get("recovery_applied")` check; returns `{"report_text": ...}` when set
- All 5 new downsample note tests pass; 17/17 reporter tests pass
- Full suite: 415 passed, 15 pre-existing failures (test_chat_api.py ×10, test_execute_endpoint.py ×4, test_langsmith_integration.py ×1) — not introduced by this story

### Completion Notes List

**Story Status:** ✅ COMPLETE — READY FOR REVIEW

**Implemented:** 2026-03-28

**Approach:** Verification story with one gap fix. ACs #1, #2, #3, #5 were pre-existing; only AC #4 (downsampling note) required a code change.

**AC #4 Implementation:**
- Added `_DOWNSAMPLE_NOTE = "Downsampled to 10,000 points using uniform stride"` constant to `reporter.py`
- Updated `render_report()` to check `state.get("recovery_applied")` — appends the note to `report_text` with `\n\n` separator when set, returns `{}` otherwise
- Fully LangGraph-compliant: returns only changed keys (no `{**state, ...}` anti-pattern)
- No streamlit import — module boundary respected

**All 5 Acceptance Criteria SATISFIED:**
1. ✅ AC #1: `executor.py::_parse_stdout()` decodes `CHART:<base64>` lines → `list[bytes]` in `report_charts` [pipeline/nodes/executor.py:43–68]
2. ✅ AC #2: Non-CHART stdout lines joined + stripped → `report_text` [pipeline/nodes/executor.py:43–68]
3. ✅ AC #3: `render_report` node wired in `graph.py`; runs as final terminal node after execution success [pipeline/graph.py:94,129]
4. ✅ AC #4: `reporter.py` now appends "Downsampled to 10,000 points using uniform stride" to `report_text` when `recovery_applied` is truthy [pipeline/nodes/reporter.py]
5. ✅ AC #5: `report_charts: list[bytes]`, `report_text: str`, `execution_success: True` — all set by `executor.py` success path [pipeline/nodes/executor.py:168–176]

**Test Results:**
- `tests/test_reporter.py`: 17/17 PASS (12 pre-existing + 5 new downsample note tests)
- `tests/test_executor.py`: 44/44 PASS
- Full suite: 415 passed, 15 pre-existing failures in unrelated test files

### File List

**Files Modified:**
- `pipeline/nodes/reporter.py` — Added `_DOWNSAMPLE_NOTE` constant and downsample note logic to `render_report()` (AC #4)
- `tests/test_reporter.py` — Added `TestRenderReportDownsampleNote` class with 5 new tests for AC #4
