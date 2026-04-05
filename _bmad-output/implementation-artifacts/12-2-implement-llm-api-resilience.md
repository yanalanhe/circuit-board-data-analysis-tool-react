# Story 12.2: Implement LLM API Resilience & Error Reporting

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want the app to surface clear errors when the LLM API is unavailable,
So that I can quickly diagnose and resolve issues without confusion.

## Acceptance Criteria

1. **Given** the OpenAI API is unreachable or returns `openai.APIError` **When** the pipeline runs **Then** the error is caught at the pipeline entry point and translated to: `"Unable to reach the AI service. Check your API key and connection."`

2. **Given** this error message **When** the user sees it in the UI **Then** it is displayed in the chat or report panel (never a raw stack trace), and is actionable

3. **Given** `OPENAI_API_KEY` is missing from `.env` **When** the app starts and I submit a query **Then** the error message identifies the missing key: `"OPENAI_API_KEY is not set. Add it to your .env file."`

4. **Given** a pipeline failure at any node (LLM timeout, rate limit, etc.) **When** the error is caught **Then** `pipeline_state["error_messages"]` is populated with a human-readable description of the failure

5. **Given** `requirements.txt` **When** I inspect it **Then** all Python library dependencies are explicitly pinned to exact versions (e.g., `langchain==0.3.27`, not `langchain>=0.3.0`) — ensuring consistent behavior across local installations (NFR16)

6. **Given** the app is run without any LangSmith configuration **When** it starts and I run the standard workflow (upload → query → execute → report) **Then** startup is clean, the workflow completes successfully, and no warnings about missing optional config appear (NFR15, NFR16)

## Tasks / Subtasks

- [x] Task 1: Fix `openai.AuthenticationError` message wording in `utils/error_translation.py` (AC: #3)
  - [x] 1.1: In `_translate_error_inner()` at line 44–45, change the `AuthenticationError` return message from `"Add OPENAI_API_KEY to your .env file"` to `"OPENAI_API_KEY is not set. Add it to your .env file."` — this is the only mandatory code change
  - [x] 1.2: Verify check order is still `AuthenticationError` → `RateLimitError` → `APIError` (most specific first) — should be unchanged

- [x] Task 2: Update tests in `tests/test_api_resilience.py` to match new message (AC: #3)
  - [x] 2.1: Update `test_translate_authentication_error`: change `assert result == "Add OPENAI_API_KEY to your .env file"` to `assert result == "OPENAI_API_KEY is not set. Add it to your .env file."`
  - [x] 2.2: Update `test_authentication_error_is_more_specific_than_api_error`: keep the `.env` assertion (`assert ".env" in auth_msg`) and update the key assertion to `assert "OPENAI_API_KEY is not set" in auth_msg`

- [x] Task 3: Verify AC1, AC2, AC4 — no changes expected (AC: #1, #2, #4)
  - [x] 3.1: Confirm `utils/error_translation.py` `openai.APIError` branch returns `"Unable to reach the AI service. Check your API key and connection."` (line 48–49) — verify only
  - [x] 3.2: Confirm `pipeline/graph.py` `run_pipeline()` outer `try/except` calls `translate_error(e)` and returns `error_messages` in state (lines 161–168) — verify only
  - [x] 3.3: Confirm `useChatHistory` hook (`src/hooks/useChatHistory.ts` line 51–54) captures `data.error?.message` from API response and passes to `ChatPanel` `error` prop — verify frontend error display path is intact

- [x] Task 4: Verify AC5, AC6 — no changes expected (AC: #5, #6)
  - [x] 4.1: Confirm `requirements.txt` has no un-pinned entries: every line matches `package==x.y.z` — test `test_requirements_all_pinned` covers this
  - [x] 4.2: Confirm `pipeline/graph.py` lines 29–36 have `try/except ImportError` fallback for `langsmith` import — LangSmith non-blocking (NFR15)

- [x] Task 5: Run backend regression tests (AC: #1–#6)
  - [x] 5.1: Run `pytest tests/test_api_resilience.py -v` — all 7 tests must pass with updated message
  - [x] 5.2: Run `pytest tests/ -v` — confirm baseline passes (477 passing + new total with 0 new failures)

## Dev Notes

### What This Story IS and IS NOT

**IS:**
- Updating the `openai.AuthenticationError` message in `utils/error_translation.py` from `"Add OPENAI_API_KEY to your .env file"` to `"OPENAI_API_KEY is not set. Add it to your .env file."` — AC3 specifies the exact wording
- Updating two assertions in `tests/test_api_resilience.py` to match the new message
- Verifying (not modifying) AC1, AC2, AC4, AC5, AC6 — all already implemented

**IS NOT:**
- Adding any new error handling logic (error propagation path is complete)
- Modifying any pipeline node files
- Changing the frontend — error display path is already correct
- Adding any new test files — `tests/test_api_resilience.py` covers all ACs
- Modifying `requirements.txt` — already fully pinned
- Changing `pipeline/graph.py` — already has outer try/except and LangSmith fallback

---

### Critical Code Change: Single Line in `utils/error_translation.py`

**File:** `utils/error_translation.py`
**Location:** `_translate_error_inner()`, line 44–45

**Current state (after Story 6.2 / 12.1):**
```python
if isinstance(exception, openai.AuthenticationError):
    return "Add OPENAI_API_KEY to your .env file"
```

**Required state after Story 12.2:**
```python
if isinstance(exception, openai.AuthenticationError):
    return "OPENAI_API_KEY is not set. Add it to your .env file."
```

**Why the change:** AC3 specifies the exact message string. The previous message was from the Streamlit era (Story 6.2). Story 12.2 standardizes it with the clearer "is not set" prefix, which is more diagnostically useful.

**Check order (do not disturb):**
```python
# utils/error_translation.py lines 40–51 — correct order, verify unchanged
try:
    import openai
    if isinstance(exception, openai.AuthenticationError):   # HTTP 401 — most specific
        return "OPENAI_API_KEY is not set. Add it to your .env file."
    if isinstance(exception, openai.RateLimitError):        # HTTP 429
        return "AI service rate limit reached. Please wait a moment and try again."
    if isinstance(exception, openai.APIError):              # all other API errors
        return "Unable to reach the AI service. Check your API key and connection."
except ImportError:
    pass
```

Both `AuthenticationError` and `RateLimitError` are subclasses of `APIError`. The check order must be most-specific → least-specific. If `APIError` is checked first, it will match `AuthenticationError` and the specific message is never reached.

---

### Test Updates Required: `tests/test_api_resilience.py`

**Test 1 — `test_translate_authentication_error` (line 24–33):**

```python
# BEFORE
def test_translate_authentication_error():
    ...
    assert result == "Add OPENAI_API_KEY to your .env file"

# AFTER
def test_translate_authentication_error():
    ...
    assert result == "OPENAI_API_KEY is not set. Add it to your .env file."
```

**Test 2 — `test_authentication_error_is_more_specific_than_api_error` (line 69–94):**

```python
# BEFORE
assert "OPENAI_API_KEY" in auth_msg
assert ".env" in auth_msg

# AFTER
assert "OPENAI_API_KEY is not set" in auth_msg   # new specific phrase
assert ".env" in auth_msg                         # still correct
```

No other test changes are needed. All other assertions in `test_api_resilience.py` are message-agnostic (`"Unable to reach"`, `"rate limit"`, `"APIConnectionError" not in`) and will pass without modification.

---

### Already Implemented — Verify-Only Items

#### AC1: APIError → "Unable to reach the AI service..."

`utils/error_translation.py` lines 48–49:
```python
if isinstance(exception, openai.APIError):
    return "Unable to reach the AI service. Check your API key and connection."
```
✅ Already correct — no change needed.

#### AC2: Error displayed in chat panel (not raw stack trace)

**Backend error path:**
1. `pipeline/graph.py` `run_pipeline()` outer `try/except` (lines 161–168) calls `translate_error(e)` and returns `{"error_messages": [translated_msg], "execution_success": False}`
2. `services/api.py` `/api/chat` endpoint (lines 679–688) wraps `run_pipeline()` in `try/except`, calls `translate_error(e)`, returns `{"status": "error", "error": {"message": error_msg, "code": "PIPELINE_ERROR"}}`
3. Same pattern in `/api/execute` (lines 748–762)

**Frontend error display path (React/Next.js):**
1. `src/hooks/useChatHistory.ts` lines 51–54: `if (data.status === "error") { setError(data.error?.message || "Failed to send message") }`
2. `src/components/ChatPanel.tsx` lines 120–124: `{(error || localError) && (<div className="px-4 py-2 bg-red-50 border-t border-red-200"><p className="text-sm text-red-700">{error || localError}</p></div>)}`
3. Result: error message appears in a red banner below the chat history — no raw stack trace ever reaches the user ✅

#### AC4: `pipeline_state["error_messages"]` populated

`pipeline/graph.py` lines 161–168:
```python
except Exception as e:
    from utils.error_translation import translate_error
    error_msg = translate_error(e)
    return {
        **state,
        "execution_success": False,
        "error_messages": list(state.get("error_messages", [])) + [error_msg],
    }
```
✅ Already correct — no change needed.

#### AC5: requirements.txt fully pinned

All 76 entries in `requirements.txt` use `==` (e.g., `langchain==0.3.27`, `openai==1.109.1`, `langsmith==0.7.0`). `test_requirements_all_pinned` asserts this.
✅ Already correct — no change needed.

#### AC6: LangSmith non-blocking

`pipeline/graph.py` lines 29–36 — `try/except ImportError` fallback:
```python
try:
    from langsmith import traceable as _traceable
except ImportError:  # pragma: no cover
    def _traceable(name=None, **kwargs):
        def decorator(fn):
            return fn
        return decorator
```
If `langsmith` is absent or key is unset, the decorator becomes a no-op. ✅ Already correct — no change needed.

---

### Previous Story Intelligence (from Story 12.1)

1. **Test baseline:** 477 tests passing; 14 pre-existing failures in `test_chat_api.py` and `test_execute_endpoint.py` (pre-date this epic, unrelated) — maintain this baseline, do not introduce new failures
2. **File reading on Windows:** Always use `encoding="utf-8", errors="replace"` when reading files in tests — prevents `UnicodeDecodeError` on Windows cp1252 encoding
3. **LangSmith 0.7.x reads `LANGSMITH_API_KEY` directly** — do not force-set `LANGCHAIN_API_KEY`. `streamlit_app.py::initialize_environment()` was fixed in Story 12.1 to remove the obsolete manual copy
4. **`load_dotenv()` confirmed at `services/api.py` line 61** — runs at module load time before any pipeline invocations
5. **No new Python dependencies** — `langsmith==0.7.0` and `openai==1.109.1` are already pinned in `requirements.txt`

---

### Module Boundary Rules (from Architecture)

```
# NEVER import fastapi or services inside pipeline/ modules
from services.session import sessions  # ❌ — never inside pipeline/

# NEVER write to session store from inside pipeline/ modules
sessions[sid]["pipeline_running"] = True  # ❌ — only in API layer

# All error translation happens in utils/error_translation.py
# No other module catches and displays exceptions directly
from utils.error_translation import translate_error  # ✅ — the only correct pattern
```

All error messages MUST go through `utils/error_translation.py` before surfacing to the API response. Never return raw exception strings like `str(e)` or `repr(e)` in any endpoint.

---

### openai SDK Error Hierarchy (v1.109.1 — pinned version)

```
openai.OpenAIError (base)
└── openai.APIError (base for all API errors)
    ├── openai.APIConnectionError  → network unreachable, DNS failure, timeout
    │   └── openai.APITimeoutError → specifically a timeout
    └── openai.APIStatusError      → HTTP response received (has .status_code)
        ├── openai.AuthenticationError  (HTTP 401) ← CHANGE MESSAGE HERE
        ├── openai.PermissionDeniedError (HTTP 403)
        ├── openai.NotFoundError        (HTTP 404)
        ├── openai.RateLimitError       (HTTP 429)
        └── openai.InternalServerError  (HTTP 5xx)
```

`openai.AuthenticationError` is raised when:
- `OPENAI_API_KEY` is absent from `.env` (key is `None`) → `ChatOpenAI` raises on first LLM call
- `OPENAI_API_KEY` is present but invalid → OpenAI API returns HTTP 401

When creating `openai.AuthenticationError` in tests, it requires `message`, `response`, and `body` parameters (APIStatusError interface). Use `unittest.mock.MagicMock()` for the response object:
```python
err = openai.AuthenticationError(
    message="No API key provided",
    response=unittest.mock.MagicMock(status_code=401, headers={}),
    body={"error": {"message": "No API key provided"}},
)
```

---

### File Structure Impact

| File | Change | Purpose |
|---|---|---|
| `utils/error_translation.py` | **Modify** — line 45: update `AuthenticationError` message string | AC3: "OPENAI_API_KEY is not set. Add it to your .env file." |
| `tests/test_api_resilience.py` | **Modify** — update 2 assertions | Match new message in `test_translate_authentication_error` and `test_authentication_error_is_more_specific_than_api_error` |
| `pipeline/graph.py` | Verify only — no changes | Outer try/except with translate_error already present (lines 161–168) |
| `requirements.txt` | Verify only — no changes | All 76 entries already pinned with `==` |
| `src/hooks/useChatHistory.ts` | Verify only — no changes | `data.error?.message` already captured and set as error state (line 52) |

---

### Architecture Compliance Checklist

- [ ] `AuthenticationError` check is BEFORE `APIError` in `_translate_error_inner()` — subclass ordering critical
- [ ] New message exactly: `"OPENAI_API_KEY is not set. Add it to your .env file."` — matches AC3 verbatim
- [ ] No raw `str(e)` or `repr(e)` in any API response — all errors via `translate_error()`
- [ ] No new Python dependencies
- [ ] No changes to frontend code — error display path is already correct
- [ ] No new API endpoints
- [ ] Module boundaries maintained: no `fastapi`/`services` imports inside `pipeline/` or `utils/`

### Project Structure Notes

- `utils/error_translation.py`: the single authoritative location for all exception → human-readable message translation [Source: _bmad-output/planning-artifacts/architecture.md#Utils-Boundary]
- `pipeline/graph.py`: pipeline entry point — wraps `compiled_graph.invoke()` with outer try/except (lines 158–168)
- `services/api.py`: API layer — wraps `run_pipeline()` calls with try/except at lines 679 and 748
- `src/hooks/useChatHistory.ts`: frontend error bridge — reads `data.error?.message` from API response (line 52)
- `tests/test_api_resilience.py`: 7 tests covering all 5 ACs for this story

### References

- `utils/error_translation.py` lines 40–51: error taxonomy with check order [Source: utils/error_translation.py#L40-L51]
- `pipeline/graph.py` lines 29–36: LangSmith ImportError fallback [Source: pipeline/graph.py#L29-L36]
- `pipeline/graph.py` lines 139–169: `run_pipeline()` with `@_traceable` and outer try/except [Source: pipeline/graph.py#L139-L169]
- `services/api.py` line 61: `load_dotenv()` at module load time [Source: services/api.py#L61]
- `services/api.py` lines 679–688: `/api/chat` exception handler with `translate_error()` [Source: services/api.py#L679-L688]
- `services/api.py` lines 748–762: `/api/execute` exception handler with `translate_error()` [Source: services/api.py#L748-L762]
- `src/hooks/useChatHistory.ts` lines 51–54: frontend error capture from API response [Source: src/hooks/useChatHistory.ts#L51-L54]
- `src/components/ChatPanel.tsx` lines 120–124: red error banner UI [Source: src/components/ChatPanel.tsx#L120-L124]
- `tests/test_api_resilience.py`: 7 tests covering all ACs [Source: tests/test_api_resilience.py]
- Architecture error taxonomy (NFR8, NFR14) [Source: _bmad-output/planning-artifacts/architecture.md#Communication-Patterns]
- Architecture NFR15: LangSmith non-blocking [Source: _bmad-output/planning-artifacts/architecture.md#L82]
- Architecture NFR16: pinned requirements.txt [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure-Deployment]
- Story 12.1 completion notes: LangSmith tracing integration + `initialize_environment()` fix [Source: _bmad-output/implementation-artifacts/12-1-implement-langsmith-tracing.md]
- Story 6.2 completion notes: original error taxonomy implementation context [Source: _bmad-output/implementation-artifacts/6-2-llm-api-resilience-developer-error-reporting.md]
- Epics Story 12.2 full acceptance criteria [Source: _bmad-output/planning-artifacts/epics.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- RED/GREEN cycle confirmed: Updated `test_translate_authentication_error` and `test_authentication_error_is_more_specific_than_api_error` to assert new message string first (tests failed against old code as expected), then updated `utils/error_translation.py` line 45 to pass. 2/2 tests went from FAILED → PASSED.
- Full suite: 477 passed, 14 pre-existing failures (identical baseline from Story 12.1) — `test_chat_api.py` (10) and `test_execute_endpoint.py` (4) — unrelated to this story. No new failures.

### Completion Notes List

- **Task 1 ✅:** Updated `utils/error_translation.py` `_translate_error_inner()` line 45: `AuthenticationError` now returns `"OPENAI_API_KEY is not set. Add it to your .env file."` (was `"Add OPENAI_API_KEY to your .env file"`). Check order `AuthenticationError → RateLimitError → APIError` preserved.
- **Task 2 ✅:** Updated `tests/test_api_resilience.py`: `test_translate_authentication_error` assertion updated to new message; `test_authentication_error_is_more_specific_than_api_error` updated to `assert "OPENAI_API_KEY is not set" in auth_msg`. Both tests pass.
- **Task 3 ✅:** Verified AC1 (`"Unable to reach the AI service..."` at line 48–49), AC4 (`pipeline/graph.py` lines 161–168 outer try/except), AC2 (`useChatHistory.ts` line 52 captures `data.error?.message`). No changes needed.
- **Task 4 ✅:** `test_requirements_all_pinned` passes (AC5). LangSmith `ImportError` fallback at `pipeline/graph.py` lines 29–36 confirmed (AC6). No changes needed.
- **Task 5 ✅:** `pytest tests/test_api_resilience.py` = 7/7 passing. Full suite: 477 passed, 14 pre-existing failures (no new regressions).
- **Acceptance criteria status:** AC1 ✅ (untouched, already correct), AC2 ✅ (frontend error path confirmed), AC3 ✅ (message updated to exact spec), AC4 ✅ (pipeline error_messages propagation intact), AC5 ✅ (test_requirements_all_pinned), AC6 ✅ (LangSmith non-blocking via ImportError fallback).

### File List

- `utils/error_translation.py` (modified — line 45: `AuthenticationError` message changed to `"OPENAI_API_KEY is not set. Add it to your .env file."`)
- `tests/test_api_resilience.py` (modified — updated 2 assertions to match new message in `test_translate_authentication_error` and `test_authentication_error_is_more_specific_than_api_error`)
- `_bmad-output/implementation-artifacts/12-2-implement-llm-api-resilience.md` (this story file)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — story status updated)

## Change Log

- 2026-03-30: Story 12.2 implemented — updated `openai.AuthenticationError` message in `utils/error_translation.py` to `"OPENAI_API_KEY is not set. Add it to your .env file."` per AC3 spec; updated 2 test assertions in `tests/test_api_resilience.py`. All 7 api_resilience tests pass. 477 baseline tests pass; 14 pre-existing failures (unrelated). No new regressions.
