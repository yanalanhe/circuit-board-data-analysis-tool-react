# Story 7.2: Implement Retry & Adaptive Replan Logic

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an engineer,
I want the system to retry failed code generation up to 3 times and replan when all retries are exhausted,
So that standard analysis requests succeed autonomously without my intervention.

## Acceptance Criteria

1. **Given** code execution fails
   **When** `route_after_execution` routes back to `generate_code`
   **Then** `retry_count` is incremented and the `generate_code` node runs again with context about the previous failure

2. **Given** a retry attempt in `generate_code`
   **When** the system prompt is constructed
   **Then** it includes information about the previous failure (error message, code snippet) to guide a better attempt

3. **Given** three consecutive code generation failures
   **When** `retry_count` reaches 3
   **Then** `route_after_execution` routes to `generate_plan` instead (adaptive replan)

4. **Given** the adaptive replan triggered
   **When** the `generate_plan` node runs with `replan_triggered = True`
   **Then** the system prompt instructs the LLM to devise a completely different analysis approach (not just tweak the code)

5. **Given** any retry or replan event
   **When** the error is caught
   **Then** a human-readable message is appended to `pipeline_state["error_messages"]` (translated, never raw exception repr)

6. **Given** the final plan after replan
   **When** code generation continues
   **Then** it succeeds and produces executable code, which is validated and executed

## Tasks / Subtasks

- [x] Verify AC #1: `executor.py` increments `retry_count` on all failure paths and `generate_code` receives failure context on retry (AC: #1)
  - [x] Confirm `execute_code` failure path returns `retry_count: current + 1`
  - [x] Confirm `generate_code` reads `retry_count > 0` and includes previous error context
  - [x] Run `tests/test_executor.py::TestStory35RetryCount` — all retry_count tests
  - [x] Run `tests/test_codegen.py` `test_retry_context_included_when_retry_count_gt_0`
- [x] Verify AC #2: `generate_code` includes previous failure info in user message (AC: #2)
  - [x] Confirm `codegen.py` builds `"Previous attempt failed (attempt N): {last_error}"` suffix when `retry_count > 0`
  - [x] Confirm only `error_messages[-1]` (last error) is used — not the full history
  - [x] Run `tests/test_codegen.py` `test_multiple_error_messages_uses_last_error_for_retry_context`
- [x] Verify AC #3: 3 failures → `replan_triggered=True` → route to `generate_plan` (AC: #3)
  - [x] Confirm `executor.py` sets `replan_triggered = new_retry >= 3`
  - [x] Confirm `route_after_execution` routes `"generate_plan"` when `retry_count >= 3`
  - [x] Run `tests/test_executor.py::TestStory35RetryCount::test_failure_sets_replan_triggered_at_threshold`
  - [x] Run `tests/test_graph.py::TestRouteAfterExecution` — all routing tests
- [x] Verify AC #4: `generate_plan` uses `replan_triggered` to prompt for different approach (AC: #4)
  - [x] Confirm `planner.py::_extract_retry_context` checks `replan_triggered` and includes `state["plan"]` (previous failed plan)
  - [x] Confirm `planner.py::_PLAN_RETRY_CONTEXT` template instructs LLM: "Please generate a DIFFERENT plan that avoids this issue"
  - [x] Run `tests/test_planner.py::test_generate_plan_includes_retry_context_on_replan`
  - [x] Run `tests/test_planner.py::test_generate_plan_includes_error_messages_in_retry`
  - [x] Run `tests/test_planner.py::test_generate_plan_no_retry_context_when_not_replanning`
- [x] Verify AC #5: All errors go through `translate_error()` — never raw exception repr (AC: #5)
  - [x] Confirm `executor.py` uses `translate_error(e)` for all failure paths (subprocess failure, timeout, generic exception)
  - [x] Confirm `codegen.py` uses `translate_error(e)` on LLM exception
  - [x] Confirm `planner.py` uses `translate_error(e)` on LLM exception
  - [x] Run `tests/test_error_translation.py` — all translation tests
- [x] Verify AC #6 (integration): full retry→replan loop wires correctly through graph (AC: #6)
  - [x] Confirm `graph.py` wiring: `execute_code` → (fail, retry_count>=3) → `generate_plan` → `generate_code` → `validate_code_node` → `execute_code`
  - [x] Run `tests/test_graph.py` — full suite (27 tests covering routing, structure, edge spec)
- [x] Run full test suite and confirm no new regressions
  - [x] `pytest tests/test_executor.py tests/test_codegen.py tests/test_planner.py tests/test_graph.py tests/test_error_translation.py -v`

## Dev Notes

### Architecture Patterns & Constraints

**CRITICAL INSIGHT — Implementation Is Already Complete:**

Based on Story 7.1 completion notes and direct codebase analysis, ALL retry/adaptive-replan logic is ALREADY IMPLEMENTED. This is a verification story — dev agent must verify each AC against existing code and run tests.

**The Complete Retry/Replan Flow:**
```
execute_code (fail, retry_count 0→1) → route_after_execution → generate_code (retry with error context)
execute_code (fail, retry_count 1→2) → route_after_execution → generate_code (retry with error context)
execute_code (fail, retry_count 2→3) → route_after_execution → generate_plan (ADAPTIVE REPLAN)
  └─ generate_plan (replan_triggered=True) → generates DIFFERENT plan
       └─ generate_code → validate_code_node → execute_code (fresh attempt)
```

Safety cap (additive enhancement, not a spec violation):
- `_MAX_REPLAN_RETRY = 6` in `graph.py` — after 6 total retries, routes to `render_report` as emergency fallback

[Source: pipeline/graph.py lines 60–79, architecture.md#Gap-2-LangGraph-conditional-edge-routing]

---

**AC #1 & #2 Implementation — `codegen.py` retry context:**

```python
# pipeline/nodes/codegen.py lines 86–94
retry_count = state.get("retry_count", 0)
if retry_count > 0:
    error_messages = state.get("error_messages", [])
    if error_messages:
        last_error = error_messages[-1]
        user_content += (
            f"\n\nPrevious attempt failed (attempt {retry_count}):\n{last_error}\n"
            "Please correct the issue and generate improved code."
        )
```

Key detail: Only `error_messages[-1]` (last error) is appended — not the full history. This prevents prompt bloat on multiple retries.

[Source: pipeline/nodes/codegen.py lines 86–94]

---

**AC #3 Implementation — `executor.py` sets `replan_triggered`:**

```python
# pipeline/nodes/executor.py lines 180–188 (failure path)
new_retry = current_retry + 1
return {
    ...
    "retry_count": new_retry,
    "replan_triggered": new_retry >= 3,
    "execution_success": False,
    ...
}
```

Also: validation guard short-circuit (executor.py lines 88–104) follows the same pattern:
```python
if state.get("validation_errors"):
    new_retry = state.get("retry_count", 0) + 1
    return {
        "execution_success": False,
        "retry_count": new_retry,
        "replan_triggered": new_retry >= 3,
        ...
    }
```

**IMPORTANT:** `retry_count` is incremented INSIDE `execute_code`, NOT in `route_after_execution`. The router reads the already-incremented value.

[Source: pipeline/nodes/executor.py lines 88–104, 178–188]

---

**AC #4 Implementation — `planner.py` adaptive replan prompting:**

```python
# pipeline/nodes/planner.py

_PLAN_RETRY_CONTEXT = """
Previous failure context:
{previous_context}

Please generate a DIFFERENT plan that avoids this issue.
Generate exactly 3-7 steps.
"""

def _extract_retry_context(state: PipelineState) -> str:
    context_parts = []
    if state.get("replan_triggered"):
        # Include previous plan that failed
        prev_plan = state.get("plan", [])
        if prev_plan:
            context_parts.append("Previous plan that failed:")
            for i, step in enumerate(prev_plan, 1):
                context_parts.append(f"  {i}. {step}")
    # Include last 3 error messages
    error_messages = state.get("error_messages", [])
    if error_messages:
        context_parts.append("\nExecution errors:")
        for error in error_messages[-3:]:
            context_parts.append(f"  - {error}")
    # Include last 3 validation errors
    validation_errors = state.get("validation_errors", [])
    if validation_errors:
        context_parts.append("\nValidation issues:")
        for error in validation_errors[-3:]:
            context_parts.append(f"  - {error}")
    return "\n".join(context_parts) if context_parts else ""
```

[Source: pipeline/nodes/planner.py lines 29–64, 111–161]

---

**AC #5 — Error Translation Pattern:**

All pipeline nodes use `utils/error_translation.py::translate_error()`:
- `executor.py`: wraps all exception paths (timeout, subprocess failure, generic)
- `codegen.py`: wraps LLM API call failure
- `planner.py`: wraps LLM API call failure (lazy import inside except block)

Error taxonomy (architecture-mandated):
| Exception Type | User-Facing Message |
|---|---|
| `openai.APIError` | "Unable to reach the AI service. Check your API key and connection." |
| `openai.RateLimitError` | "AI service rate limit reached. Please wait a moment and try again." |
| `subprocess.TimeoutExpired` | "Analysis took too long and was stopped. Try a simpler request or subset your data." |
| `SyntaxError` in validation | "Generated code had a syntax error — retrying with a corrected approach." |
| Allowlist violation | "Generated code used a restricted operation — retrying with safer code." |
| All other `Exception` | "An unexpected error occurred. Check the developer console for details." |

[Source: _bmad-output/planning-artifacts/architecture.md#Error-translation, utils/error_translation.py]

---

**LangGraph Node Return Convention (MANDATORY):**
- Nodes return ONLY changed keys as a dict — LangGraph merges automatically
- `return {**state, "key": value}` is an anti-pattern — NEVER do this
- Correct: `return {"retry_count": 2, "replan_triggered": False}`
- [Source: architecture.md#LangGraph-node-return]

**Module Boundary Rules (MANDATORY):**
- `pipeline/nodes/codegen.py` MUST NOT import `streamlit`
- `pipeline/nodes/planner.py` MUST NOT import `streamlit`
- `pipeline/nodes/executor.py` MUST NOT import `streamlit`
- These are pure Python, testable modules
- [Source: architecture.md#Module-Boundaries]

### PipelineState Fields Relevant to This Story

```python
class PipelineState(TypedDict):
    plan: list[str]              # Current execution plan (overwritten on replan)
    generated_code: str          # Current code (overwritten on each retry)
    validation_errors: list[str] # AST validation errors (causes execute_code short-circuit)
    execution_success: bool      # Set by execute_code — True if subprocess exit code 0
    retry_count: int             # Incremented by execute_code on failure; max 3 before replan
    replan_triggered: bool       # Set True by execute_code when retry_count reaches 3
    error_messages: list[str]    # Translated error messages appended throughout pipeline
    report_charts: list[bytes]   # PNG bytes from successful execution
    report_text: str             # Text output from successful execution
```

[Source: pipeline/state.py]

### Previous Story Intelligence (Story 7.1)

**Story 7.1 — Conditional Edge Routing (COMPLETED, in review):**
- `pipeline/graph.py` fully implements `route_after_execution` with correct routing logic
- `_MAX_REPLAN_RETRY = 6` safety cap prevents infinite loops (additive beyond spec's `3`)
- `execute_code` increments `retry_count` on failure (the "Story 3.5 addition")
- `tests/test_graph.py`: 27/27 tests pass covering all routing cases
- Dev notes confirmed: implementation was pre-existing from earlier sprint work

**Key Learnings from Story 7.1:**
- Epic 7 stories are verification-first — implementation was done incrementally during earlier stories
- Run existing tests BEFORE concluding any AC is satisfied
- The `_MAX_REPLAN_RETRY = 6` extension (retry_count >= 6 → render_report safety fallback) is an acceptable enhancement, not a spec violation
- `validate_code_node` (not `validate_code`) is the actual node string name — confirm in graph.py

**Story 6.1 (Code Generation) context:**
- `codegen.py::generate_code` already reads `retry_count` and `error_messages` from state for retry context
- The retry prompt format: `"Previous attempt failed (attempt N):\n{last_error}\nPlease correct the issue and generate improved code."`
- [Source: _bmad-output/implementation-artifacts/6-1-implement-code-generation-node.md]

**Story 6.3 (Executor) context:**
- `executor.py::execute_code` is the "Story 3.5 addition" that enables retry routing
- Validation guard short-circuits to retry if `validation_errors` is non-empty (avoids running invalid code)
- Success path does NOT return `retry_count`/`replan_triggered` — preserves test compatibility
- [Source: _bmad-output/implementation-artifacts/6-3-implement-subprocess-sandbox-executor.md]

**Story 6.4 (Error Translation) context:**
- `utils/error_translation.py::translate_error()` handles all error types
- `AllowlistViolationError` custom exception lives in `utils/error_translation.py`
- Error messages stored in `pipeline_state["error_messages"]` (translated, not raw)
- [Source: _bmad-output/implementation-artifacts/6-4-implement-error-translation-layer.md]

### Files to Touch for This Story

```
pipeline/
  nodes/
    codegen.py          # PRIMARY — verify retry context in generate_code (AC #1, #2)
    planner.py          # PRIMARY — verify replan prompting in generate_plan (AC #4)
    executor.py         # PRIMARY — verify retry_count increment and replan_triggered (AC #3, #5)
    error_handler.py    # READ ONLY — utility for alternative topologies (not in main graph)
  graph.py              # READ ONLY — verify routing (covered by Story 7.1)
  state.py              # READ ONLY — PipelineState definition

tests/
  test_codegen.py       # RUN — retry context tests (AC #2)
  test_planner.py       # RUN — replan prompt tests (AC #4)
  test_executor.py      # RUN — retry_count increment and replan_triggered tests (AC #1, #3)
  test_graph.py         # RUN — routing tests (AC #3, integration)
  test_error_translation.py  # RUN — translate_error coverage (AC #5)
```

**No new files expected.** This is a verification story — if all ACs are satisfied, close out without code changes.

### Project Structure Notes

**Alignment with Architecture:**
```
pipeline/
  nodes/
    codegen.py     # generate_code node (FR10) [architecture.md line 667]
    planner.py     # generate_plan node (FR7) [architecture.md line 666]
    executor.py    # execute_code node (FR14–18) [architecture.md line 669]
```

**Naming Note (from Story 7.1 learnings):**
- `validate_code_node` is the actual function and node string name (not `validate_code` as in epics.md)
- Confirmed by `tests/test_graph.py` line 249

**Potential Gap to Watch:**
- Epics.md AC #2 says the prompt should include "error message, code snippet" — current `codegen.py` only includes `error_messages[-1]` (not the code snippet explicitly). Check if this gap matters or if the code is implicitly part of the regenerated plan context. If AC #2 strictly requires the previous code snippet in the prompt, a small addition to `generate_code` may be needed.

### References

- **Epic 7 full spec:** [Source: _bmad-output/planning-artifacts/epics.md#Epic-7]
- **Story 7.2 ACs:** [Source: _bmad-output/planning-artifacts/epics.md#Story-7.2]
- **Architecture Gap 2 (routing spec):** [Source: _bmad-output/planning-artifacts/architecture.md#Gap-2-LangGraph-conditional-edge-routing]
- **Error translation taxonomy:** [Source: _bmad-output/planning-artifacts/architecture.md#Error-translation]
- **LangGraph node return pattern:** [Source: _bmad-output/planning-artifacts/architecture.md#LangGraph-node-return]
- **Retry context in codegen:** [Source: pipeline/nodes/codegen.py lines 85–94]
- **Adaptive replan prompting:** [Source: pipeline/nodes/planner.py lines 29–64, 111–161]
- **Retry count increment in executor:** [Source: pipeline/nodes/executor.py lines 88–104, 178–188]
- **Route logic:** [Source: pipeline/graph.py lines 60–79]
- **Existing codegen retry tests:** [Source: tests/test_codegen.py lines 162–271]
- **Existing planner replan tests:** [Source: tests/test_planner.py lines 277–345]
- **Existing executor retry tests:** [Source: tests/test_executor.py lines 565–661]
- **Existing graph routing tests:** [Source: tests/test_graph.py]
- **Story 7.1 (conditional edge routing):** [Source: _bmad-output/implementation-artifacts/7-1-implement-conditional-edge-routing.md]
- **PipelineState schema:** [Source: pipeline/state.py]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Story 7.2 context created: 2026-03-28
- `pipeline/nodes/codegen.py` analyzed: retry context implemented at lines 86–94 (`retry_count > 0` → append last error)
- `pipeline/nodes/planner.py` analyzed: `_extract_retry_context` + `_PLAN_RETRY_CONTEXT` template implemented for `replan_triggered=True`
- `pipeline/nodes/executor.py` analyzed: failure paths (both validation guard and subprocess) increment `retry_count` and set `replan_triggered = new_retry >= 3`
- `pipeline/graph.py` analyzed: routing verified in Story 7.1 — `route_after_execution` wired with safety cap at `_MAX_REPLAN_RETRY = 6`
- `tests/test_codegen.py` analyzed: retry context tests at lines 162–313 (3 retry-specific tests)
- `tests/test_planner.py` analyzed: replan tests at lines 277–345 (3 tests)
- `tests/test_executor.py` analyzed: retry/replan tests at lines 565–661 (7 tests)
- Potential AC #2 gap noted: epics.md mentions "code snippet" in retry prompt, but `codegen.py` only includes `error_messages[-1]` — verify if this gap is material

### Completion Notes List

**Story Status:** ✅ COMPLETE — READY FOR REVIEW

**Implemented:** 2026-03-28
**Approach:** Verification story with one gap fix. All retry/adaptive-replan logic was pre-existing from earlier sprint work (Story 3.5 executor enhancement, codegen retry context, planner replan prompting, graph conditional edges from Story 7.1).

**AC #2 Gap Resolved (code snippet in retry prompt):**
The epics.md AC #2 specifies "error message, code snippet" but `codegen.py` previously only included the error message. Added `prev_code = state.get("generated_code", "")` to the retry context block so the previous failing code is included alongside the error for better LLM guidance.

**All 6 Acceptance Criteria SATISFIED:**
1. ✅ AC #1: `execute_code` increments `retry_count` on all failure paths (validation guard + subprocess); `generate_code` includes previous error context when `retry_count > 0` [pipeline/nodes/executor.py:88–104, 178–188; pipeline/nodes/codegen.py:86–98]
2. ✅ AC #2: Retry prompt now includes BOTH error message AND previous code snippet; only `error_messages[-1]` used (not full history) [pipeline/nodes/codegen.py:86–98]
3. ✅ AC #3: `execute_code` sets `replan_triggered = new_retry >= 3`; `route_after_execution` routes `"generate_plan"` when `retry_count >= 3` [pipeline/nodes/executor.py:97,187; pipeline/graph.py:60–79]
4. ✅ AC #4: `generate_plan` detects `replan_triggered=True` via `_extract_retry_context`, includes previous failed plan + errors in prompt, instructs LLM: "Please generate a DIFFERENT plan" [pipeline/nodes/planner.py:29–64, 111–161]
5. ✅ AC #5: All error paths in `executor.py`, `codegen.py`, `planner.py` use `translate_error()` — never raw exception repr [utils/error_translation.py]
6. ✅ AC #6: Full retry→replan loop wired via `add_conditional_edges` in `graph.py`; safety cap `_MAX_REPLAN_RETRY=6` prevents infinite loops [pipeline/graph.py]

**Enhancement beyond spec (additive, not a violation):**
- `_MAX_REPLAN_RETRY = 6` safety cap: routes back to `"render_report"` when `retry_count >= 6` (from Story 7.1)

**Test Results:**
- New test added: `tests/test_codegen.py::test_retry_context_includes_previous_code_snippet` (AC #2 code snippet requirement)
- `tests/test_codegen.py`: 30/30 PASS
- `tests/test_executor.py`: 44/44 PASS
- `tests/test_planner.py`: 18/18 PASS
- `tests/test_graph.py`: 27/27 PASS
- `tests/test_error_translation.py`: 12/12 PASS
- Full suite: 410 passed, 15 pre-existing failures in unrelated test files (test_chat_api.py, test_execute_endpoint.py, test_langsmith_integration.py) — not introduced by this story

### File List

**Files Modified:**
- `pipeline/nodes/codegen.py` — Added previous code snippet to retry context (AC #2 gap fix); lines 86–98
- `tests/test_codegen.py` — Added `test_retry_context_includes_previous_code_snippet` for AC #2 code snippet requirement

**Files Verified (No Changes Required):**
- `pipeline/nodes/executor.py` — `execute_code` increments `retry_count` and sets `replan_triggered` on all failure paths (validation guard + subprocess)
- `pipeline/nodes/planner.py` — `generate_plan` with `replan_triggered=True` uses `_extract_retry_context` + `_PLAN_RETRY_CONTEXT` for adaptive replan
- `pipeline/nodes/error_handler.py` — `handle_error` utility available (not in main graph)
- `pipeline/graph.py` — `route_after_execution` wired with `add_conditional_edges`, safety cap at `_MAX_REPLAN_RETRY=6`
- `pipeline/state.py` — PipelineState with `retry_count`, `replan_triggered`, `error_messages` fields
- `utils/error_translation.py` — All error types handled by `translate_error()`

**Files Updated (Story Tracking):**
- `_bmad-output/implementation-artifacts/7-2-implement-retry-adaptive-replan.md` — Status: ready-for-dev → review; all tasks marked complete
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `7-2-implement-retry-adaptive-replan`: ready-for-dev → in-progress → review
