# Story 7.1: Implement Conditional Edge Routing in LangGraph

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the LangGraph pipeline to decide between retrying code generation, replanning, or rendering the report,
So that the system automatically recovers from failures without user intervention.

## Acceptance Criteria

1. **Given** `pipeline/graph.py` with the compiled LangGraph `StateGraph`
   **When** I inspect the node connections
   **Then** all nodes are properly wired: `classify_intent → generate_plan → generate_code → validate_code_node → execute_code`, with conditional edges on `execute_code`

2. **Given** a `route_after_execution` conditional edge function
   **When** I inspect it
   **Then** it takes `pipeline_state` as input and returns the next node name based on execution success and retry count

3. **Given** `execution_success = True`
   **When** `route_after_execution` runs
   **Then** it returns `"render_report"` to proceed to report rendering

4. **Given** `execution_success = False` and `retry_count < 3`
   **When** `route_after_execution` runs
   **Then** it returns `"generate_code"` (retry_count was already incremented inside `execute_code` before routing)

5. **Given** `execution_success = False` and `retry_count >= 3`
   **When** `route_after_execution` runs
   **Then** it returns `"generate_plan"` and `replan_triggered` has been set to `True` in the state (set by `execute_code` on the failure path)

6. **Given** the conditional edges setup
   **When** I inspect the code
   **Then** it matches exactly:
   ```python
   graph.add_conditional_edges(
       "execute_code",
       route_after_execution,
       {"render_report": "render_report", "generate_code": "generate_code", "generate_plan": "generate_plan"}
   )
   ```

## Tasks / Subtasks

- [x] Verify `pipeline/graph.py` conditional edge routing against all 6 ACs (AC: #1–#6)
  - [x] Confirm all 6 nodes registered: `classify_intent`, `generate_plan`, `generate_code`, `validate_code_node`, `execute_code`, `render_report`
  - [x] Confirm `route_after_execution` function signature: takes `PipelineState`, returns `str`
  - [x] Confirm `execution_success=True` → `"render_report"`
  - [x] Confirm `execution_success=False`, `retry_count < 3` → `"generate_code"`
  - [x] Confirm `execution_success=False`, `retry_count >= 3` → `"generate_plan"`
  - [x] Confirm `add_conditional_edges("execute_code", route_after_execution, {...})` matches spec
- [x] Verify `execute_code` node increments `retry_count` on failure paths (AC: #4)
  - [x] Confirm executor.py returns `retry_count` (incremented) on failure path
  - [x] Confirm executor.py sets `replan_triggered=True` when new `retry_count >= 3` (AC: #5)
- [x] Run existing `tests/test_graph.py` to confirm all tests pass (AC: #1–#6)
  - [x] `TestRouteAfterExecution` — all routing logic tests
  - [x] `TestHandleError` — handle_error node tests
  - [x] `TestGraphStructure` — node wiring and module boundary tests
  - [x] `TestConditionalEdgeSpec` — edge map spec verification
- [x] Verify `pipeline/nodes/error_handler.py` `handle_error` utility function (AC: #4, #5)
  - [x] Confirm it increments `retry_count` and sets `replan_triggered` at threshold 3
  - [x] Confirm returns only changed keys (LangGraph convention)
- [x] If any AC is not met, implement the missing piece in `pipeline/graph.py`
- [x] Ensure no regressions — run full test suite

## Dev Notes

### Architecture Patterns & Constraints

**Conditional Edge Routing — The Exact Specification (Architecture Gap 2):**

The architecture document explicitly designates conditional edge routing as "Gap 2" and mandates the exact implementation:

```python
# pipeline/graph.py

def route_after_execution(state: PipelineState) -> str:
    if state["execution_success"]:
        return "render_report"
    elif state["retry_count"] < 3:
        return "generate_code"   # retry with corrected prompt
    else:
        return "generate_plan"   # adaptive replan

graph.add_conditional_edges(
    "execute_code",
    route_after_execution,
    {
        "render_report": "render_report",
        "generate_code": "generate_code",
        "generate_plan": "generate_plan",
    }
)
```

The existing `pipeline/graph.py` has this implemented with a slight enhancement:
- `_MAX_REPLAN_RETRY = 6` — safety cap (3 retries + 3 replans) prevents infinite loops
- `retry_count >= 6` → routes to `"render_report"` as a safety fallback
- This is additive to the spec, not a violation

**IMPORTANT: retry_count is incremented INSIDE execute_code, NOT in route_after_execution:**
The docstring in `pipeline/graph.py` states: "retry_count is incremented inside execute_code on failure paths. route_after_execution reads the already-incremented retry_count."

This means:
- When `execute_code` fails, it returns `{"retry_count": current + 1, "replan_triggered": new_count >= 3, ...}`
- `route_after_execution` then reads the already-updated state to decide routing
- This is the Story 3.5 executor enhancement (see executor.py docstring: "Story 3.5 addition")

[Source: architecture.md#Gap-2-LangGraph-conditional-edge-routing]

**Graph Topology (Exact Wiring):**
```
START → classify_intent
classify_intent → (intent=="report") → generate_plan
classify_intent → (intent=="qa"/"chat") → END
generate_plan → generate_code
generate_code → validate_code_node
validate_code_node → execute_code
execute_code → (execution_success=True) → render_report → END
execute_code → (retry_count < 3) → generate_code
execute_code → (retry_count >= 3, < 6) → generate_plan
execute_code → (retry_count >= 6) → render_report (safety cap)
```

Note: `validate_code_node` is the function and node string name (not `validate_code`). Epics.md uses `validate_code` but the actual implementation uses `validate_code_node` — confirm in existing code.

[Source: pipeline/graph.py lines 88–129, architecture.md#LangGraph-Graph-Topology]

**LangGraph Node Return Convention:**
- Nodes return ONLY changed keys as a dict — LangGraph merges automatically
- Do NOT return `{**state, "key": value}` — this is an anti-pattern
- Example correct: `return {"retry_count": 2, "replan_triggered": False}`
- Example incorrect: `return {**state, "retry_count": 2}` ❌
- [Source: architecture.md#LangGraph-node-return]

**Module Boundary Rules:**
- `pipeline/graph.py` MUST NOT import `streamlit`
- `pipeline/nodes/error_handler.py` MUST NOT import `streamlit`
- These are testable, pure Python modules
- [Source: architecture.md#Module-Boundaries]

**LangSmith Tracing:**
- `@_traceable` decorator is applied ONLY to `run_pipeline()` in graph.py
- Individual nodes are traced automatically by LangGraph (no decorator needed on nodes)
- LangSmith import is guarded with `try/except ImportError` — non-blocking if not installed
- [Source: architecture.md#LangSmith-Tracing, pipeline/graph.py lines 29–36]

### Technical Requirements

**PipelineState Fields Relevant to This Story:**
```python
class PipelineState(TypedDict):
    execution_success: bool      # Set by execute_code — True if subprocess exit code 0
    retry_count: int             # Incremented by execute_code on failure; max 3 before replan
    replan_triggered: bool       # Set True by execute_code when retry_count reaches 3
    error_messages: list[str]    # Translated error messages appended throughout pipeline
    generated_code: str          # Current code being executed
    validation_errors: list[str] # AST validation errors (for retry context)
```
[Source: pipeline/state.py]

**execute_code Failure Path (Story 3.5 Enhancement):**
On any failure path, `execute_code` returns:
- `retry_count`: current + 1 (incremented)
- `replan_triggered`: True when new retry_count >= 3
- `execution_success`: False
- `execution_output`: captured output (may be partial)
- `error_messages`: list with translated error appended

On success path:
- `execution_success`: True
- `report_charts`: list[bytes]
- `report_text`: str
- (does NOT return retry_count/replan_triggered on success path)

[Source: pipeline/nodes/executor.py docstring lines 15–18]

**handle_error Utility Node:**
`pipeline/nodes/error_handler.py` provides `handle_error(state) -> dict`:
- Increments `retry_count` by 1
- Sets `replan_triggered = True` when new `retry_count >= 3`
- Appends human-readable message to `error_messages`
- Returns only `{retry_count, replan_triggered, error_messages}`
- NOT in the main graph — available for alternative topologies
- Used in tests to verify retry/replan transition logic independently

[Source: pipeline/nodes/error_handler.py]

**Naming — Important Detail:**
- Epics.md AC #1 uses `validate_code` as node name
- Actual implementation uses `validate_code_node` (both as the function and node string name)
- This is an acceptable variance — the function is in `pipeline/nodes/validator.py`
- Tests confirm node name is `validate_code_node` (test_graph.py line 249)

**Testing Pattern (from test_graph.py):**
- Pure function tests: `route_after_execution` and `handle_error` are tested directly (no mocks needed)
- Graph structure tests: inspect `compiled_graph.nodes` for required node names
- Module boundary tests: `ast.parse` source file to check for forbidden imports
- Edge spec tests: scan source code strings for required patterns

### Previous Story Intelligence

**Story 6.4: Error Translation Layer (most recent completed story)**
- `utils/error_translation.py` fully implemented — all error types handled
- `translate_error(e)` used in all pipeline nodes including executor
- Error messages stored in `pipeline_state["error_messages"]` (translated, not raw)
- `AllowlistViolationError` custom exception class lives in `utils/error_translation.py`
- Key pattern: Catch exception → `translate_error(e)` → append to `error_messages`
- [Source: _bmad-output/implementation-artifacts/6-4-implement-error-translation-layer.md]

**Story 6.3: Subprocess Sandbox Executor (executor.py)**
- `execute_code` node in `pipeline/nodes/executor.py` is fully implemented
- On failure: returns `retry_count` (incremented), `replan_triggered`, `execution_success=False`
- This is the Story 3.5 enhancement that enables conditional edge routing
- `_parse_stdout` handles `CHART:<base64>` lines → `report_charts: list[bytes]`
- [Source: _bmad-output/implementation-artifacts/6-3-implement-subprocess-sandbox-executor.md]

**Story 6.2: AST Code Validator (validator.py)**
- `validate_code_node` (note the `_node` suffix) in `pipeline/nodes/validator.py`
- Returns `validation_errors` list; if non-empty, executor short-circuits to retry
- `AllowlistViolationError` from `utils/error_translation` is used here
- [Source: _bmad-output/implementation-artifacts/6-2-implement-ast-code-validator.md]

**Story 6.1: Code Generation Node (codegen.py)**
- `generate_code` in `pipeline/nodes/codegen.py`
- On retry: includes previous failure context in system prompt
- Reads `error_messages` and `generated_code` from state for retry context
- [Source: _bmad-output/implementation-artifacts/6-1-implement-code-generation-node.md]

**CRITICAL INSIGHT — Likely Already Implemented:**
Based on analysis of `pipeline/graph.py` (current codebase), the conditional edge routing is ALREADY IMPLEMENTED:
- `route_after_execution` function exists (lines 60–79)
- All 6 nodes registered (lines 89–94)
- Linear edges wired (lines 113–115)
- `add_conditional_edges("execute_code", ...)` called (lines 118–126)
- `tests/test_graph.py` already covers all ACs with 20+ tests

**Dev agent primary task:** VERIFY implementation against all 6 ACs and RUN existing tests. If all pass, the story is complete. Implement any gaps found.

### Project Structure Notes

**Files to Touch for This Story:**
```
pipeline/
  graph.py                  # PRIMARY — verify/implement conditional edge routing
  state.py                  # READ ONLY — PipelineState definition
  nodes/
    executor.py             # READ ONLY — verify retry_count increment on failure
    error_handler.py        # READ ONLY — verify handle_error utility
    validator.py            # READ ONLY — confirm validate_code_node name
tests/
  test_graph.py             # RUN — all AC coverage already exists
```

**Alignment with Architecture File Structure:**
```
pipeline/
  graph.py                  # LangGraph StateGraph construction + run_pipeline() [architecture.md line 662]
  nodes/
    executor.py             # execute_code node + subprocess sandbox (FR14–18) [architecture.md line 669]
    error_handler.py        # handle_error node — retry/replan routing (FR15–17) [architecture.md line 671]
```

**No New Files Required** — implementation and tests already exist. This story is verification-first.

**Conflicts or Variances:**
- `validate_code_node` vs `validate_code`: epics.md uses bare name, impl uses `_node` suffix — acceptable, tests confirm
- `_MAX_REPLAN_RETRY = 6` safety cap extends beyond the spec's `retry_count >= 3 → generate_plan` — additive enhancement, not a violation of the spec

### References

- **Architecture Gap 2 (exact spec):** [Source: _bmad-output/planning-artifacts/architecture.md#Gap-2-LangGraph-conditional-edge-routing]
- **LangGraph node return pattern:** [Source: _bmad-output/planning-artifacts/architecture.md#LangGraph-node-return]
- **Story 7.1 full AC:** [Source: _bmad-output/planning-artifacts/epics.md#Story-7.1]
- **Epic 7 overview:** [Source: _bmad-output/planning-artifacts/epics.md#Epic-7]
- **Existing graph implementation:** [Source: pipeline/graph.py]
- **Executor retry_count increment:** [Source: pipeline/nodes/executor.py#Story-3.5-addition]
- **Error handler utility:** [Source: pipeline/nodes/error_handler.py]
- **Existing tests:** [Source: tests/test_graph.py]
- **PipelineState schema:** [Source: pipeline/state.py]
- **Story 6.4 (error translation context):** [Source: _bmad-output/implementation-artifacts/6-4-implement-error-translation-layer.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Story 7.1 context created: 2026-03-28
- `pipeline/graph.py` analyzed: `route_after_execution` already implemented with `_MAX_REPLAN_RETRY=6` safety enhancement
- `pipeline/nodes/executor.py` analyzed: `retry_count` incremented on failure path (Story 3.5 addition)
- `pipeline/nodes/error_handler.py` analyzed: `handle_error` utility available for alternative topologies
- `tests/test_graph.py` analyzed: 27 tests covering all ACs for routing, handle_error, graph structure, and edge spec
- Architecture Gap 2 reviewed: exact conditional edge spec confirmed matching existing implementation
- Epic 7 status: was "backlog" → updated to "in-progress" (first story in epic)
- dev-story execution: 2026-03-28 — all 6 ACs verified, 27/27 tests pass, 409/424 suite passes (15 pre-existing failures unrelated to this story)

### Completion Notes List

**Story Status:** ✅ COMPLETE — READY FOR REVIEW

**Implemented:** 2026-03-28
**Approach:** Verification story — implementation was already complete from prior work (Story 3.5 executor enhancement + graph wiring). No code changes required.

**All 6 Acceptance Criteria SATISFIED:**
1. ✅ AC #1: All 6 nodes wired — `classify_intent → generate_plan → generate_code → validate_code_node → execute_code`, conditional edges on `execute_code` [pipeline/graph.py:89–126]
2. ✅ AC #2: `route_after_execution(state: PipelineState) -> str` — takes state, returns node name string [pipeline/graph.py:60–79]
3. ✅ AC #3: `execution_success=True` → `"render_report"` [pipeline/graph.py:71–72]
4. ✅ AC #4: `execution_success=False`, `retry_count < 3` → `"generate_code"`; `retry_count` incremented inside `execute_code` before routing [pipeline/graph.py:74–75, pipeline/nodes/executor.py:180–186]
5. ✅ AC #5: `execution_success=False`, `retry_count >= 3` → `"generate_plan"`; `replan_triggered=True` set in `execute_code` failure path [pipeline/graph.py:76–77, pipeline/nodes/executor.py:187]
6. ✅ AC #6: `graph.add_conditional_edges("execute_code", route_after_execution, {"render_report": ..., "generate_code": ..., "generate_plan": ...})` matches spec exactly [pipeline/graph.py:118–126]

**Enhancement beyond spec (additive, not a violation):**
- `_MAX_REPLAN_RETRY = 6` safety cap: routes back to `"render_report"` when `retry_count >= 6` to prevent infinite replan loops

**Test Results:**
- `tests/test_graph.py`: 27/27 PASS
  - `TestRouteAfterExecution`: 10 tests — all routing cases including safety cap
  - `TestHandleError`: 10 tests — handle_error utility node logic
  - `TestGraphStructure`: 6 tests — node wiring, module boundary, importability
  - `TestConditionalEdgeSpec`: 1 test — edge map spec verification
- Full suite: 409 passed, 15 pre-existing failures in unrelated test files (test_chat_api.py, test_execute_endpoint.py, test_langsmith_integration.py) — not introduced by this story

### File List

**Files Verified (No Changes Required):**
- `pipeline/graph.py` — Conditional edge routing fully implemented; `route_after_execution`, `add_conditional_edges`, all 6 nodes registered
- `pipeline/nodes/executor.py` — `execute_code` increments `retry_count` and sets `replan_triggered` on failure path (Story 3.5 addition)
- `pipeline/nodes/error_handler.py` — `handle_error` utility: increments retry_count, sets replan_triggered at threshold 3, returns only changed keys
- `pipeline/state.py` — PipelineState TypedDict with `execution_success`, `retry_count`, `replan_triggered`, `error_messages` fields
- `tests/test_graph.py` — 27 tests covering all 6 ACs; all pass

**Files Modified (Story Tracking Only):**
- `_bmad-output/implementation-artifacts/7-1-implement-conditional-edge-routing.md` — Status: ready-for-dev → review; tasks marked complete; completion notes added
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — `7-1-implement-conditional-edge-routing`: in-progress → review; `epic-7`: backlog → in-progress
