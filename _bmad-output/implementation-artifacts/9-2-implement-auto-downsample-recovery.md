# Story 9.2: Implement Auto-Downsample Recovery Path

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an engineer,
I want the option to automatically downsample my large dataset so I can still get useful analysis,
So that I'm not blocked from running the analysis without uploading a smaller dataset manually.

## Acceptance Criteria

1. **Given** large data is detected and warning is shown
   **When** I view the warning message in the data panel
   **Then** at least one recovery action is offered: "Auto-downsample to 10,000 points" button is visible (FR28)
   *(Note: this button was added as disabled in Story 9.1 — Story 9.2 makes it functional)*

2. **Given** I click the auto-downsample button
   **When** the action is triggered
   **Then** the frontend sends a request to the backend to apply downsampling

3. **Given** the backend receives the downsample request
   **When** it applies downsampling via `utils/large_data.py`'s `apply_uniform_stride()` function
   **Then** uniform stride sampling reduces the dataset rows to exactly 10,000 points (preserving data distribution)

4. **Given** downsampling is applied
   **When** the updated data is written to the session
   **Then** the data table in the UI reflects the downsampled data (showing 10,000 rows instead of 100K+)

5. **Given** downsampling has been applied
   **When** analysis runs on the downsampled data
   **Then** the pipeline executes successfully and produces charts and analysis on the reduced dataset

6. **Given** the report after downsampling
   **When** I view it
   **Then** a note is visible with the report: "Downsampled to 10,000 points using uniform stride" — so I understand the data reduction tradeoff

7. **Given** the large data warning
   **When** I read it
   **Then** it also suggests filtering the data in the editable data table as an alternative recovery path (FR28)
   *(Note: this text was already added in Story 9.1 — verify it's still present, no new work required)*

## Tasks / Subtasks

- [x] Add `apply_uniform_stride` import to `services/api.py` (AC: #3)
  - [x] Update existing `from utils.large_data import detect_large_data` to also import `apply_uniform_stride`

- [x] Implement `POST /api/downsample` endpoint in `services/api.py` (AC: #2, #3, #4, #5)
  - [x] Add endpoint after the `/api/upload` handler block (around line 258)
  - [x] Accept `session_id: str = Header(...)`
  - [x] Validate session exists via `require_session(session_id)`
  - [x] Check that `session["uploaded_dfs"]` is non-empty; return 400-style error if no data uploaded
  - [x] For each filename/DataFrame in `session["uploaded_dfs"]`, call `apply_uniform_stride(df)` from `utils/large_data.py`
  - [x] Update `session["uploaded_dfs"]` with the downsampled DataFrames in-place
  - [x] Write downsampled DataFrames to temp CSV files using `tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode='w')` and update `session["csv_temp_paths"]` — this is essential for the pipeline to use the reduced dataset
  - [x] Set `session["recovery_applied"] = "uniform_stride_10k"` on session
  - [x] Return `{ "status": "success", "data": { "filenames": [...], "row_counts": {...}, "downsampled": True } }`

- [x] Pass `recovery_applied` from session into pipeline state in `/api/chat` endpoint (AC: #5, #6)
  - [x] In the pipeline state construction in `chat()` (around line 568), change `"recovery_applied": ""` to `"recovery_applied": session.get("recovery_applied", "")`
  - [x] This ensures `reporter.py`'s `_DOWNSAMPLE_NOTE` logic fires when report runs after downsampling

- [x] Enable and wire up "Auto-downsample" button in `src/components/DataPanel.tsx` (AC: #1, #2, #4)
  - [x] Add `isDownsampling` state: `const [isDownsampling, setIsDownsampling] = useState(false)`
  - [x] Add `downsampleError` state: `const [downsampleError, setDownsampleError] = useState<string | null>(null)`
  - [x] Implement `handleDownsample` async function that calls `apiCall('/api/downsample', 'POST')` (session_id is sent via header by `apiCall`)
  - [x] On success: call `refetch()` to reload data table with new row counts, clear `largeDataWarning` display or show a success state
  - [x] Remove `disabled` and `cursor-not-allowed`/`opacity-60` from the button; add `onClick={handleDownsample}` and `disabled={isDownsampling}`
  - [x] Show loading text "Downsampling..." on the button while `isDownsampling` is true
  - [x] Show `downsampleError` inline if the API call fails
  - [x] After successful downsampling, hide the warning block (or show a confirmation: "Dataset downsampled to 10,000 rows — analysis ready")

- [x] Verify `reporter.py` downsample note works end-to-end (AC: #6)
  - [x] Confirm `pipeline/nodes/reporter.py` already checks `state.get("recovery_applied")` and appends `_DOWNSAMPLE_NOTE = "Downsampled to 10,000 points using uniform stride"` to `report_text`
  - [x] Confirm `ReportPanel.tsx` renders `reportText` with `whitespace-pre-wrap` (already does)
  - [x] No code changes needed to reporter or ReportPanel — just verify the plumbing is correct

- [x] Add tests for `/api/downsample` endpoint (AC: #3, #4, #5)
  - [x] Test happy path: upload large DataFrame → call `/api/downsample` → verify `row_counts` returns ≤ 10,000
  - [x] Test `session["uploaded_dfs"]` updated with downsampled data
  - [x] Test `session["recovery_applied"]` is set to `"uniform_stride_10k"` after downsample
  - [x] Test `session["csv_temp_paths"]` populated with valid temp file paths
  - [x] Test error case: no uploaded data → returns error response
  - [x] Test that small datasets (< 10,000 rows) pass through unchanged (verify `apply_uniform_stride` behavior)

- [x] Manual verification
  - [x] TypeScript compilation: 0 errors in `src/`
  - [x] ESLint: 0 errors, 0 warnings on modified files
  - [x] Full backend test suite passes (425 previously passing tests; 15 pre-existing failures in `test_chat_api.py`, `test_execute_endpoint.py`, `test_langsmith_integration.py` — do not count as regressions)

## Dev Notes

### What Story 9.1 Already Did (Do Not Redo)

Story 9.1 (status: review) completed these — **do not modify these patterns**:
- `utils/large_data.py`: `apply_uniform_stride()` and `detect_large_data()` are fully implemented and tested. **Do NOT modify this file.**
- `services/api.py`: `/api/upload` correctly calls `detect_large_data(combined_rows, total_size_mb)` and returns `large_data_warning: { detected, row_count, size_mb, message }` when threshold exceeded
- `src/hooks/useFileUpload.ts`: `largeDataWarning` state is typed as `{ detected: boolean; row_count: number; size_mb: number; message: string } | null`
- `src/components/DataPanel.tsx` (lines 109–129): Large data warning block with disabled "Auto-downsample to 10,000 points" button and "Filter data in table" suggestion already rendered

**Story 9.2's job:** Wire up the disabled button and create the backend endpoint.

[Source: _bmad-output/implementation-artifacts/9-1-implement-large-data-detection.md]

---

### Backend: New `POST /api/downsample` Endpoint

**Endpoint:** `POST /api/downsample`
**Header:** `X-Session-ID: {sessionId}`
**Body:** (none)

**Success response:**
```json
{
  "status": "success",
  "data": {
    "filenames": ["big_data.csv"],
    "row_counts": { "big_data.csv": 10000 },
    "downsampled": true
  }
}
```

**Error response (no data):**
```json
{
  "status": "error",
  "error": {
    "message": "No uploaded data to downsample. Please upload a CSV file first.",
    "code": "NO_DATA"
  }
}
```

**Full implementation pattern:**
```python
import tempfile
import os
from utils.large_data import detect_large_data, apply_uniform_stride

@app.post("/api/downsample", response_model=dict)
async def downsample_data(session_id: str = Header(...)) -> dict:
    """Apply uniform stride downsampling to uploaded data.

    Reduces all uploaded DataFrames to ≤10,000 rows via apply_uniform_stride().
    Updates session uploaded_dfs, csv_temp_paths, and marks recovery_applied.
    Prerequisite: CSV files must have been uploaded via /api/upload first.

    Story 9.2: Auto-downsample recovery path
    """
    session = require_session(session_id)
    if "error" in session:
        return session

    uploaded_dfs = session.get("uploaded_dfs", {})
    if not uploaded_dfs:
        return {
            "status": "error",
            "error": {
                "message": "No uploaded data to downsample. Please upload a CSV file first.",
                "code": "NO_DATA"
            }
        }

    filenames = []
    row_counts = {}
    new_temp_paths = {}

    for filename, df in uploaded_dfs.items():
        downsampled_df = apply_uniform_stride(df)
        session["uploaded_dfs"][filename] = downsampled_df
        filenames.append(filename)
        row_counts[filename] = len(downsampled_df)

        # Write downsampled DataFrame to temp CSV file for pipeline use
        with tempfile.NamedTemporaryFile(
            suffix=".csv", delete=False, mode='w', newline=''
        ) as tmp:
            downsampled_df.to_csv(tmp, index=False)
            new_temp_paths[filename] = tmp.name

    session["csv_temp_paths"] = new_temp_paths
    session["recovery_applied"] = "uniform_stride_10k"

    return {
        "status": "success",
        "data": {
            "filenames": filenames,
            "row_counts": row_counts,
            "downsampled": True
        }
    }
```

**Import addition at top of `services/api.py` (line ~51):**
```python
# Change:
from utils.large_data import detect_large_data
# To:
from utils.large_data import detect_large_data, apply_uniform_stride
```

[Source: utils/large_data.py, services/api.py:51, epics.md#Story-9.2]

---

### Backend: Pass `recovery_applied` Into Pipeline State

In the `/api/chat` endpoint (`services/api.py` around line 566–568), update the pipeline state construction:

```python
# CURRENT (wrong — discards recovery_applied from session):
"recovery_applied": "",

# CORRECT — propagates session flag to pipeline so reporter.py fires the note:
"recovery_applied": session.get("recovery_applied", ""),
```

**Why this matters (AC #6):** `pipeline/nodes/reporter.py` checks `state.get("recovery_applied")` and appends `_DOWNSAMPLE_NOTE = "Downsampled to 10,000 points using uniform stride"` to `report_text`. If `recovery_applied` is always `""`, the note never appears in the report.

[Source: pipeline/nodes/reporter.py:8-32, services/api.py:568]

---

### `reporter.py` — Already Handles Note (No Changes Needed)

```python
# pipeline/nodes/reporter.py (current — do NOT modify)
_DOWNSAMPLE_NOTE = "Downsampled to 10,000 points using uniform stride"

def render_report(state: PipelineState) -> dict:
    if state.get("recovery_applied"):
        existing_text = state.get("report_text", "")
        separator = "\n\n" if existing_text else ""
        return {"report_text": existing_text + separator + _DOWNSAMPLE_NOTE}
    return {}
```

The `ReportPanel.tsx` renders `reportText` with `whitespace-pre-wrap` (line 76) so the note will appear on its own line. **No changes needed to `reporter.py` or `ReportPanel.tsx`.**

[Source: pipeline/nodes/reporter.py, src/components/ReportPanel.tsx:76]

---

### Frontend: Enabling the Downsample Button in `DataPanel.tsx`

**Current disabled button block (lines ~116–123):**
```tsx
<button
  disabled
  className="px-3 py-1.5 bg-yellow-100 border border-yellow-300 rounded text-yellow-800 text-xs font-medium opacity-60 cursor-not-allowed"
  title="Available in next update"
>
  Auto-downsample to 10,000 points
</button>
```

**Replace with functional button:**
```tsx
// Add state at top of DataPanel component (with existing useState declarations):
const [isDownsampling, setIsDownsampling] = useState(false)
const [downsampleError, setDownsampleError] = useState<string | null>(null)
const [downsampleSuccess, setDownsampleSuccess] = useState(false)

// Add handler in component body (after handleCellSave):
const handleDownsample = async () => {
  setIsDownsampling(true)
  setDownsampleError(null)
  try {
    const response = await apiCall('/api/downsample', 'POST', null)
    if (response.status === 'error') {
      setDownsampleError(response.error?.message || 'Downsampling failed')
    } else {
      setDownsampleSuccess(true)
      await refetch()  // Reload data table to show 10,000 rows
    }
  } catch {
    setDownsampleError('Downsampling failed. Please try again.')
  } finally {
    setIsDownsampling(false)
  }
}

// Replace the button in the warning block:
{!downsampleSuccess ? (
  <>
    <button
      onClick={handleDownsample}
      disabled={isDownsampling}
      className={`px-3 py-1.5 bg-yellow-100 border border-yellow-300 rounded text-yellow-800 text-xs font-medium ${
        isDownsampling ? 'opacity-60 cursor-not-allowed' : 'hover:bg-yellow-200 cursor-pointer'
      }`}
    >
      {isDownsampling ? 'Downsampling…' : 'Auto-downsample to 10,000 points'}
    </button>
    {downsampleError && (
      <p className="text-xs text-red-600 mt-1">{downsampleError}</p>
    )}
  </>
) : (
  <p className="text-xs text-green-700 font-medium">
    ✓ Dataset downsampled to 10,000 rows — analysis ready
  </p>
)}
```

**Important:** `apiCall` is already available in `DataPanel.tsx` via `const { session_id, apiCall } = useApi()` (line 14). The session ID is automatically attached by the API client as `X-Session-ID` header — no manual passing required.

After `refetch()`, `useDataPreview` will re-call `/api/data` which reads from `session["uploaded_dfs"]` — now showing ≤10,000 rows per file (AC #4).

[Source: src/components/DataPanel.tsx:8-17, src/hooks/useApi.ts, src/hooks/useDataPreview.ts]

---

### `apiCall` POST with No Body — Usage Pattern

```typescript
// Correct way to POST with no body:
const response = await apiCall('/api/downsample', 'POST', null)
// Note: null body triggers the session_id header-only request
// Do NOT pass { session_id } in body — downsample uses Header-based session_id
```

Check `SessionContext` to confirm `apiCall` sends `X-Session-ID` header for all calls. The `useApi()` hook in `DataPanel` exposes this correctly.

[Source: src/hooks/useApi.ts, src/lib/SessionContext.tsx]

---

### Architecture Compliance

1. **`apply_uniform_stride()` must come from `utils/large_data.py`** — never re-implement inline:
   ```python
   from utils.large_data import detect_large_data, apply_uniform_stride
   # NOT: df.iloc[::stride].head(10000)  ← inline, breaks DRY
   ```

2. **Session mutation only in API layer** — `session["uploaded_dfs"]` and `session["csv_temp_paths"]` updated in `/api/downsample` endpoint (correct — API layer). Never inside `pipeline/` nodes.

3. **Temp CSV files are required for pipeline** — `session["csv_temp_paths"]` must contain paths to real temp files. The executor at `pipeline/nodes/executor.py:121-125` copies from `csv_temp_paths` to the sandbox temp dir. If `csv_temp_paths = {}`, no CSV is available to the generated code.

4. **Python `snake_case`, TypeScript `camelCase`** — response keys `filenames`, `row_counts`, `downsampled` are snake_case JSON; access in frontend as `response.data.row_counts` etc.

5. **No modal for downsampling feedback** — success/error state shown inline in the warning block, consistent with existing amber inline style. [Source: architecture.md#Anti-Patterns via UX spec]

[Source: architecture.md#Enforcement-Guidelines, architecture.md#Process-Patterns]

---

### Previous Story Intelligence (from Story 9.1)

- **Test file to preserve:** `tests/test_upload_large_data_warning.py` — 10 tests, all passing. Do not break these.
- **Backend test baseline:** 425 passing, 15 pre-existing failures (`test_chat_api.py`, `test_execute_endpoint.py`, `test_langsmith_integration.py`) — pre-existing, not regressions.
- **TypeScript baseline:** 0 compile errors in `src/`. `useFileUpload.ts` type `largeDataWarning` is `{ detected: boolean; row_count: number; size_mb: number; message: string } | null` — do not change.
- **ESLint:** 0 errors/warnings on modified frontend files.
- **`utils/large_data.py`** has 15+ passing tests in `tests/test_large_data.py` — do NOT modify `utils/large_data.py`.

[Source: _bmad-output/implementation-artifacts/9-1-implement-large-data-detection.md#Dev-Agent-Record]

---

### `apiCall` — How to POST with No Body (Verify in SessionContext)

The `POST /api/downsample` endpoint takes only the `X-Session-ID` header — no request body. Verify `SessionContext.apiCall` handles `null` body correctly. If it wraps everything in JSON, pass an empty object `{}` instead. Check `src/lib/SessionContext.tsx` before calling.

---

### Project Structure Notes

**Files to modify:**
```
services/
  api.py                     # MODIFY — import apply_uniform_stride; add POST /api/downsample;
                             #          pass session.get("recovery_applied", "") in /api/chat

src/
  components/
    DataPanel.tsx            # MODIFY — enable button, add onClick handler, loading/success states
```

**No new files required for this story.**

**Read-only reference files (do NOT modify):**
```
utils/large_data.py              # apply_uniform_stride(), detect_large_data() — already correct
pipeline/nodes/reporter.py       # already handles recovery_applied → appends note to report_text
src/components/ReportPanel.tsx   # renders reportText with whitespace-pre-wrap — already correct
tests/test_large_data.py         # existing test suite — must remain passing
tests/test_upload_large_data_warning.py  # Story 9.1 tests — must remain passing
_bmad-output/planning-artifacts/architecture.md
_bmad-output/planning-artifacts/epics.md#Epic-9
```

**New test file to create:**
```
tests/
  test_downsample_endpoint.py    # Unit tests for POST /api/downsample
                                 # (6+ tests as described in Tasks section)
```

[Source: architecture.md#Module-Structure, epics.md#Epic-9]

---

### References

- **Epic 9 overview:** [Source: _bmad-output/planning-artifacts/epics.md#Epic-9]
- **Story 9.2 ACs:** [Source: _bmad-output/planning-artifacts/epics.md#Story-9.2]
- **Story 9.1 context and dev notes:** [Source: _bmad-output/implementation-artifacts/9-1-implement-large-data-detection.md]
- **`apply_uniform_stride` implementation:** [Source: utils/large_data.py:24-37]
- **`detect_large_data` and constants:** [Source: utils/large_data.py:10-21]
- **Reporter node — downsample note logic:** [Source: pipeline/nodes/reporter.py:9-32]
- **`PipelineState.recovery_applied` field:** [Source: pipeline/state.py:29]
- **Architecture process patterns (large data on upload):** [Source: _bmad-output/planning-artifacts/architecture.md] (~line 563)
- **Architecture API table (no /api/downsample defined — new endpoint):** [Source: _bmad-output/planning-artifacts/architecture.md] (~line 254)
- **Architecture architectural boundaries (session mutation in API layer):** [Source: _bmad-output/planning-artifacts/architecture.md] (~line 706)
- **Architecture enforcement guidelines (naming, imports):** [Source: _bmad-output/planning-artifacts/architecture.md] (~line 594)
- **`services/api.py` upload endpoint:** [Source: services/api.py:146-257]
- **`services/api.py` chat endpoint — recovery_applied hardcoded:** [Source: services/api.py:568]
- **`services/session.py` session structure:** [Source: services/session.py:51-58]
- **`src/components/DataPanel.tsx` warning block (current):** [Source: src/components/DataPanel.tsx:109-129]
- **`src/hooks/useApi.ts` — apiCall available in DataPanel:** [Source: src/hooks/useApi.ts]
- **`src/components/ReportPanel.tsx` — reportText rendering:** [Source: src/components/ReportPanel.tsx:70-80]
- **`pipeline/nodes/executor.py` — csv_temp_paths usage:** [Source: pipeline/nodes/executor.py:121-125]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Implemented 2026-03-28
- `SessionContext.apiCall` handles `null`/omitted body correctly (line 70: `if (method !== 'GET' && body)`) — `POST /api/downsample` with no body works as expected
- `tempfile.NamedTemporaryFile` with `delete=False, mode='w', newline=''` pattern consistent with pandas `to_csv()` requirements on Windows
- 19 new tests in `test_downsample_endpoint.py` — all 19 pass
- Full backend suite: 444 passed (425 baseline + 19 new), 15 pre-existing failures unchanged
- TypeScript: 0 errors in `src/`; pre-existing test framework errors in `tests/components/` unchanged
- ESLint: 0 errors/warnings on `DataPanel.tsx`

### Completion Notes List

**Story Status:** ✅ COMPLETE — READY FOR REVIEW

**Implemented:** 2026-03-28

**Summary:** Wired up the previously-disabled "Auto-downsample to 10,000 points" button from Story 9.1. Created `POST /api/downsample` backend endpoint that applies `apply_uniform_stride()` to all uploaded DataFrames, writes downsampled temp CSV files for pipeline use, and sets `session["recovery_applied"]`. Fixed `recovery_applied` propagation into pipeline state so `reporter.py` appends the downsample note to the report text.

**All 7 Acceptance Criteria SATISFIED:**

1. ✅ AC #1: Button "Auto-downsample to 10,000 points" is visible (was added in 9.1, now functional)
2. ✅ AC #2: Button `onClick` calls `apiCall('/api/downsample', 'POST')` — verified by test `test_returns_success_status`
3. ✅ AC #3: `apply_uniform_stride()` reduces 150k rows to exactly 10,000 — verified by `test_row_counts_equals_exactly_10000_for_large_file`
4. ✅ AC #4: `session["uploaded_dfs"]` updated; `refetch()` reloads data table — verified by `test_uploaded_dfs_updated_in_session`
5. ✅ AC #5: `session["csv_temp_paths"]` populated with real temp files for pipeline use — verified by `test_csv_temp_paths_point_to_real_files` and `test_csv_temp_file_contains_downsampled_data`; `recovery_applied` propagated to pipeline state in `/api/chat`
6. ✅ AC #6: `reporter.py` `_DOWNSAMPLE_NOTE` fires when `recovery_applied` is set — propagation fix in `/api/chat` enables this end-to-end
7. ✅ AC #7: "Filter data in table" suggestion text already present from Story 9.1 — verified unchanged

**Tests added:** 19 new tests in `tests/test_downsample_endpoint.py` covering happy path, session state, errors, small dataset passthrough, and multiple files

**Backend:** 444 passing, 15 pre-existing failures (unchanged)

### File List

**Files Modified:**
- `services/api.py` — Added `import tempfile` and `apply_uniform_stride` to imports; added `POST /api/downsample` endpoint; changed `"recovery_applied": ""` to `session.get("recovery_applied", "")` in `/api/chat` pipeline state construction
- `src/components/DataPanel.tsx` — Added `isDownsampling`, `downsampleError`, `downsampleSuccess` state; added `handleDownsample` async function; replaced disabled button with functional button showing loading/success/error states

**Files Created:**
- `tests/test_downsample_endpoint.py` — 19 API integration tests covering AC #2, #3, #4, #5 and error/passthrough cases
