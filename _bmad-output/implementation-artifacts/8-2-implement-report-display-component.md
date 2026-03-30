# Story 8.2: Implement Report Display Component & Chart Rendering

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an engineer,
I want to see rendered charts and trend analysis in the Report panel after execution completes,
So that I can immediately see the results and act on the insights.

## Acceptance Criteria

1. **Given** pipeline execution completes successfully
   **When** the report is ready
   **Then** the frontend calls `GET /api/report` and receives the charts and text

2. **Given** the Report panel
   **When** a report is available
   **Then** base64-encoded PNG images from `report_charts` are decoded and displayed as `<img>` elements

3. **Given** chart display
   **When** I view the charts
   **Then** they are sized appropriately (not too large, not too small), with clear labels, axis titles, and readable annotations (labels/titles come from the generated matplotlib code — the component just renders what it receives)

4. **Given** the trend analysis text
   **When** it is displayed
   **Then** it appears below the charts in a readable format (plain text or markdown if the LLM outputs it)

5. **Given** multiple charts in a report
   **When** I view the Report panel
   **Then** they are displayed in a clear list or grid format, not overlapping

6. **Given** the Report panel initially
   **When** no analysis has run yet
   **Then** it shows a placeholder: "Run an analysis to see results here"

## Tasks / Subtasks

- [x] Add `ReportData` type to `src/types/api.ts` (AC: #1)
  - [x] Add `ReportData` interface: `{ charts: string[], text: string, code: string }`
  - [x] Export from `api.ts`
- [x] Update `AppLayout.tsx` to fetch and store report data after execution (AC: #1)
  - [x] Add `reportCharts: string[]` state (default `[]`)
  - [x] Add `reportText: string | null` state (default `null`)
  - [x] Add `useApi` destructured `apiCall` to existing `useApi()` call
  - [x] After `executeAnalysis()` resolves, call `GET /api/report` via `apiCall<ReportData>`
  - [x] On success response, update `reportCharts` and `reportText` state
  - [x] Pass `reportCharts`, `reportText`, and `isExecuting` as props to `<ReportPanel>`
- [x] Implement `ReportPanel.tsx` with chart + text rendering (AC: #2, #3, #4, #5, #6)
  - [x] Add props interface: `reportCharts: string[]`, `reportText: string | null`, `isLoading: boolean`
  - [x] Update component signature to accept the new props
  - [x] Render placeholder ("Run an analysis to see results here") when `reportCharts.length === 0` and `!isLoading` and `!reportText` (AC: #6)
  - [x] Render loading state (e.g., "Generating report…") while `isLoading` is true
  - [x] Render each chart as `<img src={`data:image/png;base64,${chart}`} />` with `max-w-full h-auto` (AC: #2)
  - [x] Display multiple charts in a vertical list with `gap-4` — no overlapping (AC: #5)
  - [x] Display `reportText` below charts using `whitespace-pre-wrap` for readable formatting (AC: #4)
- [x] Create `src/hooks/usePolling.ts` hook as architecture-compliant stub (AC: #1, future async support)
  - [x] Create the hook with `startPolling` / `stopPolling` pattern polling `/api/status` every 500ms
  - [x] Note: not wired into `handleExecute` yet because backend is currently synchronous
- [x] Manual verification (AC: #1–#6)
  - [x] TypeScript compilation: all new/modified source files compile cleanly (0 errors in src/)
  - [x] ESLint: all new/modified source files pass with 0 errors, 0 warnings
  - [x] Confirm placeholder shows before any execution (logic: `!hasReport && !isLoading`)
  - [x] Charts render via base64 data URI pattern; text renders with whitespace-pre-wrap

## Dev Notes

### Critical Architecture Note — Synchronous Backend

**The current `/api/execute` backend endpoint is SYNCHRONOUS.** It calls `run_pipeline()` directly and blocks until the pipeline completes before returning. This affects the frontend execution flow:

- `executeAnalysis()` in `useApi.ts` makes a POST to `/api/execute` that **waits for the full pipeline to complete** before the Promise resolves
- When `executeAnalysis()` resolves, the pipeline is **already done** — no polling loop is needed
- Immediately call `GET /api/report` after `executeAnalysis()` resolves to get the results

**AC #1 says "polls /api/report"** — with the sync backend, a single GET call after execute completes satisfies this AC. The `usePolling.ts` hook is created per the architecture spec but is not wired into `handleExecute` until the backend becomes truly async.

**Practical implementation in `AppLayout.handleExecute`:**
```typescript
const handleExecute = useCallback(async () => {
  if (!executeAnalysis) return
  setIsExecuting(true)
  try {
    await executeAnalysis()                                          // waits for full pipeline
    const response = await apiCall<ReportData>('/api/report', 'GET')
    if (response.status === 'success' && response.data) {
      setReportCharts(response.data.charts)
      setReportText(response.data.text || null)
    }
  } catch (error) {
    console.error('Execute failed:', error)
  } finally {
    setIsExecuting(false)
  }
}, [executeAnalysis, apiCall])
```

[Source: services/api.py:639-706 (sync execute), architecture.md#Frontend-Architecture]

### Backend API Contract — `/api/report`

**Endpoint:** `GET /api/report`
**Header:** `X-Session-ID: {sessionId}` (injected automatically by `apiCall()` in SessionContext)
**Success Response:**
```json
{
  "status": "success",
  "data": {
    "charts": ["<base64_string>", "..."],
    "text": "<trend analysis text or empty string>",
    "code": "<generated Python code>"
  }
}
```
**Error response when no pipeline has run:**
```json
{ "status": "error", "error": { "message": "No execution results available yet.", "code": "NOT_FOUND" } }
```

**Bytes → base64 serialization:** `pipeline_state["report_charts"]` is `list[bytes]` (raw PNG binary). FastAPI's `jsonable_encoder` auto-converts `bytes` → base64 strings in JSON. The frontend receives base64 strings — use `data:image/png;base64,{chart}` as the `<img src>`.

[Source: services/api.py:739-772, pipeline/state.py (report_charts: list[bytes])]

### Backend API Contract — `/api/status`

**Endpoint:** `GET /api/status`
**Header:** `X-Session-ID: {sessionId}`
**Response:**
```json
{
  "status": "success",
  "data": { "running": false, "step": null, "progress": null }
}
```
`running: true` while pipeline is executing. Currently toggled synchronously, so polling would see it flip between requests. Used by `usePolling.ts`.

[Source: services/api.py:709-732]

### ReportPanel Props & Rendering

Current `ReportPanel.tsx` is a zero-prop placeholder. Update to accept:
```typescript
interface ReportPanelProps {
  reportCharts: string[]     // base64 PNG strings from /api/report → data.charts
  reportText: string | null  // trend analysis text from /api/report → data.text
  isLoading: boolean         // true while executeAnalysis() is running
}
```

**Chart img element pattern:**
```tsx
<img
  key={index}
  src={`data:image/png;base64,${chart}`}
  alt={`Chart ${index + 1}`}
  className="max-w-full h-auto rounded border border-gray-200"
/>
```

**Text display pattern:** The LLM sometimes outputs markdown (with `**bold**` or `# headers`). Use `whitespace-pre-wrap` as a safe default that preserves line breaks without a full markdown parser:
```tsx
<p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
  {reportText}
</p>
```

**Multiple charts layout:** Vertical list avoids overlap and works well at any panel width:
```tsx
<div className="flex flex-col gap-4">
  {reportCharts.map((chart, index) => ( ... ))}
</div>
```

[Source: src/components/ReportPanel.tsx, architecture.md#Frontend-State, epics.md#Story-8.2]

### AppLayout State Additions

Add to `AppLayout.tsx` alongside existing state:
```typescript
const [reportCharts, setReportCharts] = useState<string[]>([])
const [reportText, setReportText] = useState<string | null>(null)
```

Update `useApi()` destructure to include `apiCall`:
```typescript
const { executeAnalysis, apiCall } = useApi()
```

Pass to `<ReportPanel>`:
```tsx
<ReportPanel
  reportCharts={reportCharts}
  reportText={reportText}
  isLoading={isExecuting}
/>
```

[Source: src/components/AppLayout.tsx:14-17, 62-65]

### `usePolling.ts` Hook — Architecture Stub

Architecture expects `src/hooks/usePolling.ts` per the module structure spec. Create now for completeness:
```typescript
'use client'

import { useCallback, useRef } from 'react'
import { useApi } from '@/hooks/useApi'

export function usePolling(onComplete: () => void) {
  const { apiCall } = useApi()
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startPolling = useCallback(() => {
    intervalRef.current = setInterval(async () => {
      const response = await apiCall('/api/status', 'GET')
      if (response.status === 'success' && !response.data?.running) {
        stopPolling()
        onComplete()
      }
    }, 500)
  }, [apiCall, onComplete])

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  return { startPolling, stopPolling }
}
```
Note: `startPolling` is NOT called in `handleExecute` yet — backend is synchronous so `executeAnalysis()` blocks until done. Wire it in when the backend `/api/execute` is converted to a background task.

[Source: architecture.md#Frontend-Architecture (usePolling.ts reference)]

### `ReportData` Type Addition to `api.ts`

Add after `UseApiReturn`:
```typescript
export interface ReportData {
  charts: string[]   // base64-encoded PNG strings
  text: string       // trend analysis text (may be empty string)
  code: string       // generated Python code
}
```
[Source: services/api.py:765-771, architecture.md#API-contracts]

### Project Structure Notes

**Files to modify:**
```
src/
  components/
    ReportPanel.tsx    # MODIFY — add props interface, implement chart+text rendering, loading state
    AppLayout.tsx      # MODIFY — add reportCharts/reportText state, fetch /api/report post-execute, pass props
  types/
    api.ts             # MODIFY — add ReportData interface

src/
  hooks/
    usePolling.ts      # CREATE — polling hook stub per architecture spec
```

**No modifications to backend files in this story.**

**Read-only reference files:**
```
src/lib/SessionContext.tsx       # apiCall() pattern — already handles X-Session-ID header injection
src/hooks/useApi.ts              # executeAnalysis, apiCall — patterns to follow
services/api.py:709-772          # /api/status + /api/report implementation
pipeline/state.py                # report_charts: list[bytes], report_text: str
```

### Previous Story Intelligence — Story 8.1

Story 8.1 confirmed:
- `pipeline/nodes/reporter.py` runs as the final pipeline node; stores results in `PipelineState`
- `report_charts: list[bytes]` (PNG binary, decoded from `CHART:<base64>` stdout lines)
- `report_text: str` (non-CHART stdout lines joined)
- `recovery_applied` triggers a "Downsampled to 10,000 points using uniform stride" suffix on `report_text`
- Backend test suite has 415 passing tests; 15 pre-existing failures in `test_chat_api.py`, `test_execute_endpoint.py`, `test_langsmith_integration.py` — do not count these as regressions

[Source: _bmad-output/implementation-artifacts/8-1-implement-report-rendering-node.md]

### References

- **Epic 8 spec:** [Source: _bmad-output/planning-artifacts/epics.md#Epic-8]
- **Story 8.2 ACs:** [Source: _bmad-output/planning-artifacts/epics.md#Story-8.2]
- **Architecture frontend state:** [Source: _bmad-output/planning-artifacts/architecture.md] (lines ~169–182)
- **Architecture module structure:** [Source: _bmad-output/planning-artifacts/architecture.md] (lines ~405–460)
- **Architecture execution flow:** [Source: _bmad-output/planning-artifacts/architecture.md] (lines ~764–768)
- **Backend /api/report:** [Source: services/api.py:739-772]
- **Backend /api/status:** [Source: services/api.py:709-732]
- **Backend /api/execute (synchronous):** [Source: services/api.py:639-706]
- **ReportPanel placeholder:** [Source: src/components/ReportPanel.tsx]
- **AppLayout current state:** [Source: src/components/AppLayout.tsx]
- **useApi hook:** [Source: src/hooks/useApi.ts]
- **SessionContext apiCall:** [Source: src/lib/SessionContext.tsx]
- **Story 8.1 learnings:** [Source: _bmad-output/implementation-artifacts/8-1-implement-report-rendering-node.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Implemented 2026-03-28
- TypeScript: `noUnusedLocals: true` flagged pre-existing unused `setPlan`/`setIntent` setters in AppLayout.tsx — fixed by using `const [plan] =` destructure (setters to be re-added when ChatPanel wires up plan/intent state updates in a future story)
- ESLint: `@next/next/no-img-element` warning on `<img>` in ReportPanel — suppressed with eslint-disable comment; `next/image` does not support `data:` base64 URIs, so native `<img>` is correct
- ESLint disable comment required `React.Fragment` wrapper to be valid JSX — refactored map accordingly
- Pre-existing TypeScript errors in `tests/components/DataGrid.test.tsx` and `tests/components/PlanPanel.test.tsx`: missing `@testing-library/react` and jest type definitions — not introduced by this story
- All 4 new/modified src files pass tsc (0 errors in src/) and ESLint (0 errors, 0 warnings)

### Completion Notes List

**Story Status:** ✅ COMPLETE — READY FOR REVIEW

**Implemented:** 2026-03-28

**Summary:** ReportPanel upgraded from a static placeholder to a fully functional chart+text display component. AppLayout wires the execute→fetch-report data flow.

**All 6 Acceptance Criteria SATISFIED:**

1. ✅ AC #1: `handleExecute` in `AppLayout.tsx` calls `apiCall<ReportData>('/api/report', 'GET')` immediately after `executeAnalysis()` resolves (sync backend pattern — single GET satisfies the "polls" requirement)
2. ✅ AC #2: Each base64 string from `response.data.charts` rendered as `<img src="data:image/png;base64,{chart}" />` — Fragment wrapper used for eslint-disable placement
3. ✅ AC #3: `max-w-full h-auto` constrains chart size appropriately; labels/annotations are in the PNG itself from matplotlib
4. ✅ AC #4: `reportText` displayed in `<p className="whitespace-pre-wrap leading-relaxed">` below charts
5. ✅ AC #5: Charts in `flex flex-col gap-4` vertical list — no overlap at any panel width
6. ✅ AC #6: Placeholder "Run an analysis to see results here" shown when `!hasReport && !isLoading`

**Loading state:** "Generating report…" with animated pulse shown while `isExecuting === true`

**TypeScript:** All src files compile cleanly. Pre-existing test framework errors in `tests/` are not regressions.

**ESLint:** 0 errors, 0 warnings on all modified/created files.

### File List

**Files Modified:**
- `src/types/api.ts` — Added `ReportData` interface
- `src/components/AppLayout.tsx` — Added `reportCharts`/`reportText` state, `apiCall` from `useApi`, post-execute `/api/report` fetch, props passed to `<ReportPanel>`
- `src/components/ReportPanel.tsx` — Full implementation: props interface, loading state, placeholder, chart rendering, text rendering

**Files Created:**
- `src/hooks/usePolling.ts` — Architecture-compliant polling hook stub (not yet wired into execute flow — backend is synchronous)
