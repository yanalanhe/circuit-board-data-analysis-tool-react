# Story 10.2: Implement Editable Code & Manual Re-Execution

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an engineer,
I want to edit the generated Python code directly in the Code tab and re-run it,
So that I can refine the analysis without starting the workflow over.

## Acceptance Criteria

1. **Given** code is displayed in the Code tab editor, **when** I edit the code directly in the editor, **then** my changes are reflected in the editor buffer in real time.
2. **Given** I have edited the code, **when** I click a "Re-run" button in the Code tab, **then** the modified code is sent to the backend via `PUT /api/code` with the new code string.
3. **Given** the backend receives edited code, **when** it processes the PUT request, **then** it validates the code (same allowlist rules as generated code in `pipeline/nodes/validator.py`).
4. **Given** the code passes validation, **when** the backend executes it via the subprocess, **then** new charts and trend analysis are produced and returned.
5. **Given** the re-run succeeds, **when** execution completes, **then** new output replaces the previous report panel contents, and the Code tab remains showing the edited code.
6. **Given** the re-run fails validation, **when** the validator catches an unsafe operation or syntax error, **then** a plain-English error message appears inline in the Code tab (not a raw traceback).
7. **Given** the re-run fails in the subprocess, **when** the error is caught, **then** a translated error message appears in the report panel via the error translation layer.

## Tasks / Subtasks

- [x] Task 1: Implement PUT `/api/code` endpoint in `services/api.py` (AC: #2, #3, #4, #6, #7)
  - [x] 1.1: Add imports at top of endpoint function: `validate_code` from `pipeline.nodes.validator`, `execute_code` from `pipeline.nodes.executor`, `build_reexec_state` from `utils.reexec`, `AllowlistViolationError` from `utils.error_translation`
  - [x] 1.2: Guard against missing `pipeline_state` — return error `"No analysis to re-run. Please run an analysis first."` with code `NO_PIPELINE_STATE`
  - [x] 1.3: Call `validate_code(request.code)` → on failure, translate each error via `translate_error()` and return `{status: "error", error: {message: joined_errors, code: "VALIDATION_ERROR"}}`
  - [x] 1.4: Build reexec state with `build_reexec_state(pipeline_state, request.code)` and call `execute_code(reexec_state)`
  - [x] 1.5: On execution failure, return last message from `error_messages` with code `"EXECUTION_ERROR"`
  - [x] 1.6: On success, update `session["pipeline_state"]` keys: `generated_code`, `report_charts`, `report_text`, `execution_success`; return `{status: "success", data: {charts, text, code}}`

- [x] Task 2: Update `CodeViewerPanel.tsx` — enable editing and add Re-run button (AC: #1, #2, #5, #6)
  - [x] 2.1: Add props: `onRerun?: (code: string) => void`, `isRerunning?: boolean`, `codeError?: string | null`
  - [x] 2.2: Add local state: `const [editedCode, setEditedCode] = useState(code ?? '')`
  - [x] 2.3: Add `useEffect(() => { setEditedCode(code ?? '') }, [code])` to sync when new analysis result arrives
  - [x] 2.4: Remove `readOnly: true` from Monaco options; add `onChange={(value) => setEditedCode(value ?? '')}` and `value={editedCode}` to `<MonacoEditor>`
  - [x] 2.5: Add Re-run toolbar above editor: button labeled "Re-run" (disabled when `!editedCode || isRerunning`), loading spinner when `isRerunning`, calls `onRerun?.(editedCode)` on click
  - [x] 2.6: Below toolbar, render inline error when `codeError`: red-bordered div with plain-English message text

- [x] Task 3: Thread new props through `PlanCodePanel.tsx` (AC: pass-through)
  - [x] 3.1: Add `onRerun?: (code: string) => void`, `isRerunning?: boolean`, `codeError?: string | null` to `PlanCodePanelProps`
  - [x] 3.2: Accept them in the destructure and pass all three to `<CodeViewerPanel />`

- [x] Task 4: Wire re-run orchestration in `AppLayout.tsx` (AC: #2, #4, #5, #6, #7)
  - [x] 4.1: Destructure `session_id` from `useApi()` (already returns it)
  - [x] 4.2: Add state: `const [isRerunning, setIsRerunning] = useState(false)` and `const [codeError, setCodeError] = useState<string | null>(null)`
  - [x] 4.3: Implement `handleRerun(editedCode: string)`:
    - Set `isRerunning(true)`, clear `codeError`
    - Call `apiCall<ReportData>('/api/code', 'PUT', { session_id, code: editedCode })`
    - If `response.error?.code === 'VALIDATION_ERROR'`: set `codeError(response.error.message)`, do NOT update report
    - If `response.error?.code === 'EXECUTION_ERROR'`: set `reportText(response.error.message)`, clear `codeError`
    - If success: update `reportCharts`, `reportText`, `currentCode`, clear `codeError`
    - Always: `setIsRerunning(false)` in finally block
  - [x] 4.4: Pass `onRerun={handleRerun}`, `isRerunning={isRerunning}`, `codeError={codeError}` to `<PlanCodePanel />`

- [x] Task 5: Manual verification (AC: #1–#7)
  - [x] 5.1: Run analysis; click Code tab; confirm editor is now editable (cursor, typing)
  - [x] 5.2: Edit code and click Re-run; confirm new charts appear in Report panel
  - [x] 5.3: Enter invalid Python (e.g., `import os`) in editor; Re-run → inline red error in Code tab, report panel unchanged
  - [x] 5.4: Enter syntactically broken code (e.g., `def foo(`); Re-run → inline syntax error in Code tab
  - [x] 5.5: Enter code that will throw at runtime (e.g., `1/0`); Re-run → error message in report panel (not inline)
  - [x] 5.6: After successful Re-run, switch to Plan tab and back; confirm edited code still shows (not reset to original)

## Dev Notes

### What Exists and What to Change

| File | Status | Change Needed |
|------|--------|---------------|
| `services/api.py` `PUT /api/code` | ✅ stub exists (lines 827–846) | Replace stub body with validate + execute + return report data |
| `src/components/CodeViewerPanel.tsx` | ✅ exists (read-only) | Add edit capability + Re-run toolbar + inline error display |
| `src/components/PlanCodePanel.tsx` | ✅ exists | Add 3 new props + pass to CodeViewerPanel |
| `src/components/AppLayout.tsx` | ✅ exists | Add isRerunning/codeError state + handleRerun + pass props to PlanCodePanel |
| `services/api.py` `POST /api/rerun` | ✅ stub exists (lines 849–867) | **No change needed** — this story does NOT use /api/rerun; leave stub intact |
| `src/types/api.ts` `ReportData` | ✅ already has `{charts, text, code}` | **No change needed** — PUT /api/code success response matches this shape |
| `pipeline/nodes/validator.py` | ✅ fully implemented | **No change** — call `validate_code()` directly |
| `pipeline/nodes/executor.py` | ✅ fully implemented | **No change** — call `execute_code()` directly |
| `utils/reexec.py` | ✅ fully implemented | **No change** — call `build_reexec_state()` directly |

### Backend Implementation Detail — PUT `/api/code`

The stub (api.py lines 827–846) simply returns `{status: "success", data: {success: True}}`. Replace the entire body with:

```python
@app.put("/api/code", response_model=dict)
async def update_code(request: CodeRequest) -> dict:
    from pipeline.nodes.validator import validate_code
    from pipeline.nodes.executor import execute_code
    from utils.reexec import build_reexec_state
    from utils.error_translation import translate_error, AllowlistViolationError

    session = require_session(request.session_id)
    if "error" in session:
        return session

    pipeline_state = session.get("pipeline_state")
    if not pipeline_state:
        return {
            "status": "error",
            "error": {
                "message": "No analysis to re-run. Please run an analysis first.",
                "code": "NO_PIPELINE_STATE"
            }
        }

    # Layer 1: AST allowlist validation (same rules as generated code)
    is_valid, errors = validate_code(request.code)
    if not is_valid:
        translated = []
        for err in errors:
            if err.startswith("Syntax error:"):
                translated.append(translate_error(SyntaxError(err)))
            else:
                translated.append(translate_error(AllowlistViolationError(err)))
        return {
            "status": "error",
            "error": {
                "message": "\n".join(translated),
                "code": "VALIDATION_ERROR"
            }
        }

    # Layer 2: Subprocess execution
    reexec_state = build_reexec_state(pipeline_state, request.code)
    try:
        result = execute_code(reexec_state)
    except Exception as e:
        return {
            "status": "error",
            "error": {
                "message": translate_error(e),
                "code": "EXECUTION_ERROR"
            }
        }

    if not result.get("execution_success"):
        msgs = result.get("error_messages", [])
        return {
            "status": "error",
            "error": {
                "message": msgs[-1] if msgs else "Execution failed.",
                "code": "EXECUTION_ERROR"
            }
        }

    # Persist updated state into session
    pipeline_state["generated_code"] = request.code
    pipeline_state["report_charts"] = result.get("report_charts", [])
    pipeline_state["report_text"] = result.get("report_text", "")
    pipeline_state["execution_success"] = True
    session["pipeline_state"] = pipeline_state

    return {
        "status": "success",
        "data": {
            "charts": pipeline_state["report_charts"],
            "text": pipeline_state["report_text"],
            "code": request.code
        }
    }
```

**Key: FastAPI auto-serializes `list[bytes]` → base64 strings in JSON.** This matches how GET `/api/report` works. No special encoding needed.

### `build_reexec_state` — What It Preserves

`utils/reexec.py` `build_reexec_state(ps, edited_code)` preserves these keys from existing `pipeline_state`:
- `user_query`, `csv_temp_paths`, `data_row_count`, `intent`, `plan`, `large_data_detected`, `large_data_message`, `recovery_applied`

It resets: `validation_errors`, `retry_count`, `replan_triggered`, `execution_success`, `execution_output`, `error_messages`, `report_charts`, `report_text`.

It sets `generated_code = edited_code`.

This is safe to call when `pipeline_state` exists. The `csv_temp_paths` key is critical — it tells `execute_code` where to find the CSV files for the sandbox temp dir.

> ⚠️ **Note:** `session.py`'s `create_session()` uses key `"csv_temp_path"` (singular) while `executor.py` uses `state.get("csv_temp_paths")` (plural dict). The story 3.x implementation may have populated `csv_temp_paths` (plural) in `pipeline_state`. The `reexec.py` `_PRESERVED_KEYS` includes `"csv_temp_paths"` (plural) — so execution will find CSV data if it was populated during the original pipeline run.

### Frontend — CodeViewerPanel Changes

**Before (read-only viewer):** Single Monaco component, `readOnly: true`, no button, no state.

**After (editable + Re-run):**

```tsx
'use client'

import React, { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center">
      <p className="text-gray-400 text-sm">Loading editor…</p>
    </div>
  ),
})

interface CodeViewerPanelProps {
  code: string | null
  onRerun?: (code: string) => void
  isRerunning?: boolean
  codeError?: string | null
}

export default function CodeViewerPanel({
  code,
  onRerun,
  isRerunning = false,
  codeError = null,
}: CodeViewerPanelProps) {
  const [editedCode, setEditedCode] = useState(code ?? '')

  // Sync when a new analysis result arrives (code prop changes)
  useEffect(() => {
    setEditedCode(code ?? '')
  }, [code])

  if (!code && !editedCode) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-gray-500 text-sm italic">
          Run an analysis to see the generated code here
        </p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Re-run toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <button
          onClick={() => onRerun?.(editedCode)}
          disabled={!editedCode || isRerunning}
          className="px-3 py-1 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRerunning ? 'Running…' : 'Re-run'}
        </button>
        {isRerunning && (
          <span className="text-xs text-gray-500">Executing edited code…</span>
        )}
      </div>

      {/* Inline validation error */}
      {codeError && (
        <div className="px-3 py-2 bg-red-50 border-b border-red-200 flex-shrink-0">
          <p className="text-sm text-red-700 whitespace-pre-wrap">{codeError}</p>
        </div>
      )}

      {/* Editable Monaco editor */}
      <div className="flex-1 overflow-hidden">
        <MonacoEditor
          height="100%"
          language="python"
          theme="vs"
          value={editedCode}
          onChange={(value) => setEditedCode(value ?? '')}
          options={{
            readOnly: false,
            wordWrap: 'off',
            minimap: { enabled: false },
            fontSize: 13,
            lineHeight: 1.4,
            fontFamily: 'JetBrains Mono, Menlo, Monaco, Consolas, monospace',
            scrollBeyondLastLine: false,
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  )
}
```

### Frontend — AppLayout `handleRerun`

```tsx
// Add to state declarations:
const [isRerunning, setIsRerunning] = useState(false)
const [codeError, setCodeError] = useState<string | null>(null)

// Add session_id to useApi destructure:
const { executeAnalysis, apiCall, session_id } = useApi()

// Add handler:
const handleRerun = useCallback(async (editedCode: string) => {
  setIsRerunning(true)
  setCodeError(null)
  try {
    const response = await apiCall<ReportData>('/api/code', 'PUT', {
      session_id,
      code: editedCode,
    })
    if (response.status === 'error') {
      if (response.error?.code === 'VALIDATION_ERROR') {
        setCodeError(response.error.message)
      } else {
        // EXECUTION_ERROR → goes to report panel as translated text
        setReportText(response.error?.message || 'Execution failed.')
        setCodeError(null)
      }
    } else if (response.status === 'success' && response.data) {
      setReportCharts(response.data.charts)
      setReportText(response.data.text || null)
      setCurrentCode(response.data.code)
      setCodeError(null)
    }
  } catch (error) {
    console.error('Re-run failed:', error)
  } finally {
    setIsRerunning(false)
  }
}, [apiCall, session_id])
```

Pass to `<PlanCodePanel>`:
```tsx
<PlanCodePanel
  ...
  onRerun={handleRerun}
  isRerunning={isRerunning}
  codeError={codeError}
/>
```

### Placeholder Condition Fix

Story 10.1's `CodeViewerPanel` shows placeholder when `!code`. After story 10.2, with local `editedCode` state, the placeholder condition becomes `!code && !editedCode`. This prevents the placeholder from appearing while the user has typed code before running an analysis. However, on initial load `code` will be null and `editedCode` will be `''` (falsy), so the placeholder still shows correctly.

### `useApi()` Returns `session_id`

From `useApi.ts` line 46: `return { session_id: sessionId, apiCall: ..., executeAnalysis }`. AppLayout already imports `useApi` but currently only destructures `executeAnalysis` and `apiCall`. Add `session_id` to the destructure — no hook changes needed.

### Error Code Differentiation (Frontend)

The frontend `handleRerun` distinguishes errors by `response.error?.code`:
- `"VALIDATION_ERROR"` → show inline in Code tab (user's code has blocked imports or syntax errors)
- `"EXECUTION_ERROR"` → show in Report panel (code ran but threw a runtime error)
- `"NO_PIPELINE_STATE"` → treat same as EXECUTION_ERROR (edge case, show in report)

### Project Structure Notes

- No new files needed (all changes are modifications to existing files)
- Backend imports are lazy (inside function body) per existing pattern in `api.py` (see `/api/execute` at line 702)
- No new API endpoints, hooks, types, or library installs required

### References

- `services/api.py` lines 827–846: `PUT /api/code` stub to implement [Source: services/api.py#L827-L846]
- `services/api.py` lines 849–867: `POST /api/rerun` stub — leave unchanged [Source: services/api.py#L849-L867]
- `pipeline/nodes/validator.py` lines 59–138: `validate_code(code)` returns `(bool, list[str])` [Source: pipeline/nodes/validator.py#L59-L138]
- `pipeline/nodes/executor.py` lines 71–189: `execute_code(state)` sandboxed execution [Source: pipeline/nodes/executor.py#L71-L189]
- `utils/reexec.py` lines 23–54: `build_reexec_state(ps, edited_code)` preserves csv_temp_paths [Source: utils/reexec.py#L23-L54]
- `utils/error_translation.py`: `translate_error()`, `AllowlistViolationError` [Source: utils/error_translation.py]
- `src/components/CodeViewerPanel.tsx`: existing read-only component to transform [Source: src/components/CodeViewerPanel.tsx]
- `src/components/PlanCodePanel.tsx`: pass-through component for Code tab [Source: src/components/PlanCodePanel.tsx]
- `src/components/AppLayout.tsx` lines 21–44: existing state + `handleExecute` pattern to follow [Source: src/components/AppLayout.tsx#L21-L44]
- `src/hooks/useApi.ts` line 44: `session_id` already returned from hook [Source: src/hooks/useApi.ts#L44]
- `src/types/api.ts` lines 40–44: `ReportData` type — reused for PUT success response [Source: src/types/api.ts#L40-L44]
- Architecture: Code Transparency (FR23-25) — Monaco editor + Re-run button [Source: _bmad-output/planning-artifacts/architecture.md#L738]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation was straightforward. One test adjustment: `test_success_charts_are_base64_strings` was updated to `test_success_charts_are_strings` after discovering FastAPI serializes `bytes` via UTF-8 `.decode()` (not base64), consistent with `GET /api/report` behavior.

### Completion Notes List

- Implemented `PUT /api/code` endpoint replacing stub (services/api.py): validates via `validate_code()` (AST allowlist), executes via `execute_code()` (subprocess sandbox), updates session pipeline_state, returns `{charts, text, code}` on success.
- Error differentiation: `VALIDATION_ERROR` (inline Code tab) vs `EXECUTION_ERROR` (Report panel) — driven by `response.error?.code` in `handleRerun`.
- `CodeViewerPanel.tsx` transformed from read-only viewer to editable editor: added `editedCode` local state, `useEffect` for prop sync, Re-run toolbar, inline error display. `readOnly: false` enables Monaco editing.
- `PlanCodePanel.tsx`: 3 new optional props (`onRerun`, `isRerunning`, `codeError`) passed through to `CodeViewerPanel`.
- `AppLayout.tsx`: added `isRerunning`/`codeError` state, `handleRerun` async callback using `useApi().session_id`, props threaded to `PlanCodePanel`.
- All 17 new backend tests pass. `next build` exits 0. 0 TypeScript errors in `src/`. 15 pre-existing failures in unrelated test files (chat_api, execute_endpoint mock issue, langsmith) — unchanged from before this story.
- `POST /api/rerun` stub left intentionally unchanged per story spec.

### File List

- services/api.py (modified — PUT /api/code fully implemented)
- src/components/CodeViewerPanel.tsx (modified — editable + Re-run toolbar + inline error)
- src/components/PlanCodePanel.tsx (modified — 3 new pass-through props)
- src/components/AppLayout.tsx (modified — isRerunning/codeError state + handleRerun)
- tests/test_put_code_endpoint.py (created — 17 new tests for PUT /api/code)

## Change Log

- 2026-03-29: Implemented Story 10.2 — Editable Code & Manual Re-Execution. Replaced PUT /api/code stub with full validate+execute+return flow. Transformed CodeViewerPanel from read-only to editable with Re-run button and inline validation error display. Threaded isRerunning/codeError/onRerun through PlanCodePanel into AppLayout. Build passes cleanly (0 TS errors, next build ✓, 17/17 new tests pass).
