# Story 9.1: Implement Large Data Detection on Upload

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an engineer,
I want the system to detect when my data is too large for visualization,
So that I'm warned upfront and can choose a recovery action before running analysis.

## Acceptance Criteria

1. **Given** CSV file(s) are uploaded
   **When** the backend `/api/upload` handler processes them
   **Then** `utils/large_data.py`'s `detect_large_data()` is called with the **combined** dataset size (total row count across all uploaded files, total size in MB)

2. **Given** the detection logic
   **When** I inspect it
   **Then** it triggers on dual thresholds: ≥100,000 rows OR ≥20MB (FR26) — enforced via `detect_large_data()` constants `LARGE_DATA_ROW_THRESHOLD` and `LARGE_DATA_SIZE_THRESHOLD_MB`

3. **Given** large data is detected
   **When** the upload completes
   **Then** the response includes `large_data_warning: { detected: true, row_count: <combined_rows>, size_mb: <combined_size>, message: "Your dataset has X rows / Y MB, which exceeds the visualization threshold." }`

4. **Given** large data is detected
   **When** the frontend receives the warning
   **Then** it displays immediately in the data panel (inline message, no modal) with two recovery options visible: "Auto-downsample to 10,000 points" button and a "Filter data in table" inline suggestion

5. **Given** the upload detection
   **When** I measure the detection time
   **Then** it is immediate (<100ms for typical uploads) — no blocking or frozen UI (NFR5)

6. **Given** a normal dataset (below both thresholds)
   **When** upload completes
   **Then** `large_data_warning` is absent from the response — no spurious warnings

## Tasks / Subtasks

- [x] Fix backend `/api/upload` to call `detect_large_data()` from `utils/large_data.py` (AC: #1, #2)
  - [x] Import `detect_large_data` from `utils.large_data` in `services/api.py`
  - [x] Accumulate `combined_rows` and `combined_size_mb` across ALL uploaded files (not per-file)
  - [x] Replace inline `if len(df) >= 100_000 or file_size_mb >= 20:` check with `detect_large_data(combined_rows, combined_size_mb)`
  - [x] Call `detect_large_data()` AFTER all files have been parsed (so combined stats are known)
- [x] Fix backend response format to match AC spec (AC: #3)
  - [x] Change `large_data_warning` shape to: `{ detected: True, row_count: combined_rows, size_mb: round(combined_size_mb, 1), message: "Your dataset has {combined_rows:,} rows / {combined_size_mb:.1f} MB, which exceeds the visualization threshold." }`
  - [x] Remove `code`, `affected_files`, `max_row_count` fields from the warning object (not in AC spec)
  - [x] Ensure warning is only added when `detect_large_data()` returns `True` (AC: #6)
- [x] Update frontend type definition to match new response shape (AC: #3)
  - [x] Update `UploadResponse` interface in `src/hooks/useFileUpload.ts`: change `large_data_warning` type to `{ detected: boolean; row_count: number; size_mb: number; message: string } | undefined`
- [x] Update `DataPanel.tsx` large data warning UI to show recovery options (AC: #4)
  - [x] Replace current basic `<p>{largeDataWarning.message}</p>` with structured warning block
  - [x] Add "Auto-downsample to 10,000 points" button (disabled/non-functional in this story — wired in Story 9.2)
  - [x] Add "Filter data in table" inline suggestion text below the warning
  - [x] Keep inline (no modal) — amber styling using existing yellow-50/yellow-200 pattern
- [x] Manual verification
  - [x] TypeScript compilation: all modified files compile cleanly (0 errors in `src/`)
  - [x] ESLint: 0 errors, 0 warnings on modified files
  - [x] Verify existing `tests/test_large_data.py` still passes (no regressions to `utils/large_data.py`)
  - [x] Confirm `detect_large_data()` is imported and called in `services/api.py` (not inline check)

## Dev Notes

### Critical Gap: Current Implementation vs. Required Implementation

The existing `services/api.py` `/api/upload` endpoint has a large data check but it does NOT match the architecture or AC requirements. Here is the exact diff required:

**Problem 1 — Inline check instead of utility function:**
```python
# CURRENT (wrong) — in the per-file loop:
if len(df) >= 100_000 or file_size_mb >= 20:
    large_data_detected = True
    large_data_files.append(file.filename)

# CORRECT — after ALL files are processed:
from utils.large_data import detect_large_data, DOWNSAMPLE_TARGET_ROWS
# ... after the file loop ...
combined_rows = sum(len(df) for df in session["uploaded_dfs"].values())
if detect_large_data(combined_rows, total_size_mb):
    ...
```

**Problem 2 — Response format mismatch:**
```python
# CURRENT (wrong):
response_data["data"]["large_data_warning"] = {
    "message": message,
    "code": "LARGE_DATA_WARNING",
    "affected_files": large_data_files,
    "total_size_mb": round(total_size_mb, 1),
    "max_row_count": max_rows
}

# CORRECT (per AC spec):
response_data["data"]["large_data_warning"] = {
    "detected": True,
    "row_count": combined_rows,
    "size_mb": round(total_size_mb, 1),
    "message": (
        f"Your dataset has {combined_rows:,} rows / {total_size_mb:.1f} MB, "
        "which exceeds the visualization threshold."
    )
}
```

[Source: services/api.py:143-264, utils/large_data.py, epics.md#Story-9.1]

### Backend API Contract — `/api/upload` (post-fix)

**Endpoint:** `POST /api/upload`
**Header:** `X-Session-ID: {sessionId}`
**Form Data:** `files` — one or more CSV files

**Success response (no large data):**
```json
{
  "status": "success",
  "data": {
    "filenames": ["data.csv"],
    "row_counts": { "data.csv": 5000 }
  }
}
```

**Success response (large data detected):**
```json
{
  "status": "success",
  "data": {
    "filenames": ["big_data.csv"],
    "row_counts": { "big_data.csv": 150000 },
    "large_data_warning": {
      "detected": true,
      "row_count": 150000,
      "size_mb": 25.3,
      "message": "Your dataset has 150,000 rows / 25.3 MB, which exceeds the visualization threshold."
    }
  }
}
```

[Source: epics.md#Story-9.1-AC3, architecture.md#API-Communication-Patterns]

### Frontend Type Update — `useFileUpload.ts`

Update `UploadResponse` interface (line 7–14 of `src/hooks/useFileUpload.ts`):
```typescript
export interface UploadResponse {
  filenames: string[]
  row_counts: Record<string, number>
  large_data_warning?: {
    detected: boolean
    row_count: number
    size_mb: number
    message: string
  }
}
```

Also update the `largeDataWarning` state type annotation from `any | null` to:
```typescript
const [largeDataWarning, setLargeDataWarning] = useState<{
  detected: boolean
  row_count: number
  size_mb: number
  message: string
} | null>(null)
```

[Source: src/hooks/useFileUpload.ts:7-14, 23, 36]

### Frontend DataPanel — Warning Block with Recovery Options

The UX spec defines a `<LargeDataAlert>` component. For this story, implement the warning block inline in `DataPanel.tsx` (no need to extract to a separate component in this story unless it keeps the file clean). For Story 9.2, the "Auto-downsample" button will be wired up.

Replace the current warning block (lines 109–115 of `DataPanel.tsx`):
```tsx
{/* Large Data Warning */}
{largeDataWarning && (
  <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-sm">
    <p className="font-medium">⚠️ Large Dataset Warning</p>
    <p>{largeDataWarning.message}</p>
    <div className="mt-3 flex flex-col gap-2">
      <div className="flex gap-2">
        <button
          disabled
          className="px-3 py-1.5 bg-yellow-100 border border-yellow-300 rounded text-yellow-800 text-xs font-medium opacity-60 cursor-not-allowed"
          title="Available in next update"
        >
          Auto-downsample to 10,000 points
        </button>
      </div>
      <p className="text-xs text-yellow-600">
        Or filter your data directly in the table below, then run analysis on the reduced dataset.
      </p>
    </div>
  </div>
)}
```

**Why disabled button:** Story 9.1 is detection only. The actual downsample API call (`POST /api/downsample` or similar) and its backend implementation are Story 9.2. The button must be visible per AC #4 ("recovery options visible") but should not yet be functional.

[Source: ux-design-specification.md#LargeDataAlert, DataPanel.tsx:109-115, epics.md#Story-9.1-AC4]

### Architecture Compliance — Key Rules

1. **Never duplicate threshold constants** — always import from `utils/large_data.py`:
   ```python
   from utils.large_data import detect_large_data
   # NOT: if combined_rows >= 100_000 or size_mb >= 20.0 (inline — breaks DRY)
   ```

2. **Detection on upload, never at execution time:**
   > "Large data check — always on upload, never at execution time" [Source: architecture.md#Process-Patterns]
   — Story 9.1 detection is already in the upload endpoint. Do not move it.

3. **No modal dialogs for warnings:** Inline message in the Data panel. `DataPanel.tsx` already uses inline amber block — keep this pattern. [Source: ux-design-specification.md#Anti-Patterns]

4. **Python snake_case, TypeScript camelCase** — the API response uses `row_count`, `size_mb` (snake_case JSON), but the React state variable is `largeDataWarning` (camelCase). The `useFileUpload.ts` hook maps the JSON keys directly via `response.data.large_data_warning` (JS auto-maps snake_case JSON keys to object properties, accessed as `largeDataWarning.row_count` in components).

5. **Session state mutation only in API layer or `services/session.py`** — no changes to this rule; upload handler in `services/api.py` is the correct place for this detection.

[Source: architecture.md#Enforcement-Guidelines, architecture.md#Process-Patterns]

### Existing `utils/large_data.py` — No Changes Required

The utility file is already correct and complete. Do NOT modify it:
```python
LARGE_DATA_ROW_THRESHOLD = 100_000
LARGE_DATA_SIZE_THRESHOLD_MB = 20.0
DOWNSAMPLE_TARGET_ROWS = 10_000

def detect_large_data(row_count: int, size_mb: float) -> bool:
    return row_count >= LARGE_DATA_ROW_THRESHOLD or size_mb >= LARGE_DATA_SIZE_THRESHOLD_MB

def apply_uniform_stride(df: pd.DataFrame, target_rows: int = DOWNSAMPLE_TARGET_ROWS) -> pd.DataFrame:
    ...
```

`tests/test_large_data.py` has 15+ comprehensive tests already passing for both functions. Any changes to `utils/large_data.py` would be a regression risk with no benefit.

[Source: utils/large_data.py, tests/test_large_data.py]

### Backend `/api/upload` — Full Correct Implementation Pattern

Here is the corrected upload logic (only the relevant sections — preserve all other error handling):
```python
from utils.large_data import detect_large_data

@app.post("/api/upload", response_model=dict)
async def upload_files(
    session_id: str = Header(...),
    files: list[UploadFile] = File(...)
) -> dict:
    session = require_session(session_id)
    if "error" in session:
        return session

    filenames = []
    row_counts = {}
    total_size_mb = 0.0

    # Parse each uploaded file (keep all existing error handling)
    for file in files:
        # ... existing file size / empty / CSV parse / empty-rows error handling ...
        session["uploaded_dfs"][file.filename] = df
        filenames.append(file.filename)
        row_counts[file.filename] = len(df)
        total_size_mb += file_size_mb

    # Combined detection — after ALL files processed
    combined_rows = sum(len(df) for df in session["uploaded_dfs"].values())

    response_data = {
        "status": "success",
        "data": {
            "filenames": filenames,
            "row_counts": row_counts
        }
    }

    if detect_large_data(combined_rows, total_size_mb):
        response_data["data"]["large_data_warning"] = {
            "detected": True,
            "row_count": combined_rows,
            "size_mb": round(total_size_mb, 1),
            "message": (
                f"Your dataset has {combined_rows:,} rows / {total_size_mb:.1f} MB, "
                "which exceeds the visualization threshold."
            )
        }

    return response_data
```

[Source: services/api.py:143-264, utils/large_data.py, architecture.md#Process-Patterns]

### Project Structure Notes

**Files to modify:**
```
services/
  api.py                 # MODIFY — fix large data check to use detect_large_data(),
                         #          combine stats across all files, fix response format

src/
  hooks/
    useFileUpload.ts     # MODIFY — update large_data_warning type in UploadResponse
                         #          and useState type annotation
  components/
    DataPanel.tsx        # MODIFY — add recovery option buttons to warning block
```

**No new files required for this story.**

**Read-only reference files (do NOT modify):**
```
utils/large_data.py              # detect_large_data(), apply_uniform_stride() — already correct
tests/test_large_data.py         # existing test suite — must remain passing
_bmad-output/planning-artifacts/architecture.md  # process patterns, naming conventions
_bmad-output/planning-artifacts/ux-design-specification.md  # LargeDataAlert design spec
```

**Story 9.2 scope boundary:** The `apply_uniform_stride()` function from `utils/large_data.py` and the actual downsample API endpoint are Story 9.2. Story 9.1 only exposes the button in the UI (disabled) and implements the detection + correct response format.

[Source: architecture.md#Module-Structure, epics.md#Epic-9]

### References

- **Epic 9 overview:** [Source: _bmad-output/planning-artifacts/epics.md#Epic-9]
- **Story 9.1 ACs:** [Source: _bmad-output/planning-artifacts/epics.md#Story-9.1]
- **Story 9.2 scope:** [Source: _bmad-output/planning-artifacts/epics.md#Story-9.2]
- **Architecture process patterns (large data check):** [Source: _bmad-output/planning-artifacts/architecture.md] (~line 563)
- **Architecture API contract (/api/upload):** [Source: _bmad-output/planning-artifacts/architecture.md] (~line 257)
- **Architecture frontend state (largeDataMessage):** [Source: _bmad-output/planning-artifacts/architecture.md] (~line 186)
- **Architecture enforcement guidelines:** [Source: _bmad-output/planning-artifacts/architecture.md] (~line 596)
- **UX LargeDataAlert component spec:** [Source: _bmad-output/planning-artifacts/ux-design-specification.md] (~line 630)
- **UX anti-patterns (no modals):** [Source: _bmad-output/planning-artifacts/ux-design-specification.md] (~line 198)
- **utils/large_data.py (current):** [Source: utils/large_data.py]
- **tests/test_large_data.py (existing):** [Source: tests/test_large_data.py]
- **services/api.py upload handler (current):** [Source: services/api.py:143-264]
- **useFileUpload hook (current):** [Source: src/hooks/useFileUpload.ts]
- **DataPanel.tsx warning block (current):** [Source: src/components/DataPanel.tsx:109-115]
- **Story 8.2 learnings (test environment):** [Source: _bmad-output/implementation-artifacts/8-2-implement-report-display-component.md] — backend test suite has 415 passing tests; 15 pre-existing failures in `test_chat_api.py`, `test_execute_endpoint.py`, `test_langsmith_integration.py` — do not count as regressions

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Implemented 2026-03-28
- `test_no_warning_just_below_row_threshold` uses 99,999 rows; generates a ~4MB CSV in memory — fast enough (<5s per test, well within NFR5's 100ms upload detection requirement since detection happens post-parse not pre-parse)
- TypeScript: 0 errors in `src/`; pre-existing test framework errors in `tests/components/` unchanged (not introduced by this story)
- ESLint: 0 errors, 0 warnings on all modified frontend files
- Full backend suite: 425 passed, 15 pre-existing failures (same 15 as Story 8.2 — `test_chat_api`, `test_execute_endpoint`, `test_langsmith_integration`)

### Completion Notes List

**Story Status:** ✅ COMPLETE — READY FOR REVIEW

**Implemented:** 2026-03-28

**Summary:** Fixed the `/api/upload` large data detection to use `detect_large_data()` from `utils/large_data.py` (not inline constants), combined stats across all uploaded files, corrected the response shape, and updated the frontend warning UI to show recovery options.

**All 6 Acceptance Criteria SATISFIED:**

1. ✅ AC #1: `detect_large_data(combined_rows, total_size_mb)` called after all files parsed — `combined_rows = sum(len(df) for df in session["uploaded_dfs"].values())`
2. ✅ AC #2: Dual threshold enforced via `detect_large_data()` which internally uses `LARGE_DATA_ROW_THRESHOLD = 100_000` and `LARGE_DATA_SIZE_THRESHOLD_MB = 20.0` from `utils/large_data.py`
3. ✅ AC #3: Response shape `{ detected: True, row_count, size_mb, message }` — verified by 8 new API tests
4. ✅ AC #4: `DataPanel.tsx` now shows warning with "Auto-downsample to 10,000 points" (disabled) button and "Filter data in table" suggestion inline (no modal)
5. ✅ AC #5: Detection is immediate — runs synchronously in the upload handler after CSV parsing; no extra I/O or network calls added
6. ✅ AC #6: `large_data_warning` only added when `detect_large_data()` returns `True` — `test_no_warning_for_small_dataset` and `test_no_warning_just_below_row_threshold` confirm absence

**Tests added:** 10 new tests in `tests/test_upload_large_data_warning.py` covering warning shape, absence, combined detection

**Backend:** 425 passing, 15 pre-existing failures (unchanged)

### File List

**Files Modified:**
- `services/api.py` — Added `from utils.large_data import detect_large_data` import; replaced per-file inline threshold check with combined `detect_large_data(combined_rows, total_size_mb)` after file loop; removed `large_data_detected`/`large_data_files` variables; fixed `large_data_warning` response shape to `{ detected, row_count, size_mb, message }`
- `src/hooks/useFileUpload.ts` — Updated `UploadResponse.large_data_warning` type to `{ detected: boolean; row_count: number; size_mb: number; message: string }`; updated `largeDataWarning` useState type annotation from `any | null` to typed shape
- `src/components/DataPanel.tsx` — Replaced single-line warning `<p>` with structured block containing disabled "Auto-downsample to 10,000 points" button and "Filter data in table" suggestion text

**Files Created:**
- `tests/test_upload_large_data_warning.py` — 10 API integration tests covering AC #1, #3, #6 and combined detection
