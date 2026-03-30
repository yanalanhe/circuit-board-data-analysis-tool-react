# Story 10.1: Implement Code Viewer Component with Monaco/CodeMirror

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an engineer,
I want to view the Python code generated for any analysis in the Code tab,
So that I can verify the system understood my request correctly and trust the output.

## Acceptance Criteria

1. **Given** a completed analysis, **when** I click the Code tab, **then** the generated Python code is displayed in a syntax-highlighted code viewer component (Monaco or CodeMirror).
2. **Given** the code viewer, **when** I view it, **then** Python syntax highlighting is applied, making the code readable.
3. **Given** code that produces charts, **when** I view it, **then** I can clearly see `plt.xlabel()`, `plt.ylabel()`, `plt.title()` calls with descriptive labels.
4. **Given** the Code tab, **when** I switch to it from the Plan tab and return to Plan, **then** the code content is preserved without re-generating — it reads from React state, not triggering a fresh LLM call.
5. **Given** no analysis has been run yet, **when** I click the Code tab, **then** the editor shows a placeholder: `"Run an analysis to see the generated code here"`.
6. **Given** the code viewer, **when** viewed at 1280px+ screen width, **then** the editor is fully visible without horizontal scrolling and text is readable.

## Tasks / Subtasks

- [x] Task 1: Wire `code` field from API through AppLayout to PlanCodePanel (AC: #1, #4)
  - [x] 1.1: Add `currentCode: string | null` state to `AppLayout.tsx`
  - [x] 1.2: In `handleExecute`, extract `response.data.code` and call `setCurrentCode(response.data.code || null)` alongside existing `setReportCharts` / `setReportText`
  - [x] 1.3: Pass `currentCode` as new prop `code` to `<PlanCodePanel />` in `AppLayout`
  - [x] 1.4: Add `code: string | null` to `PlanCodePanelProps` interface

- [x] Task 2: Install and configure a code editor/viewer library (AC: #1, #2)
  - [x] 2.1: Install `@monaco-editor/react` (`npm install @monaco-editor/react`) — preferred per architecture spec
  - [x] 2.2: Alternative if Monaco has SSR issues in Next.js 14: use `react-syntax-highlighter` (`npm install react-syntax-highlighter @types/react-syntax-highlighter`) as a simpler read-only fallback
  - [x] 2.3: Verify the chosen library builds without errors under Next.js 14 (`next build`)

- [x] Task 3: Create `CodeViewerPanel` component (AC: #1, #2, #3, #5, #6)
  - [x] 3.1: Create file `src/components/CodeViewerPanel.tsx`
  - [x] 3.2: Component receives `code: string | null` prop
  - [x] 3.3: If `code` is null/empty, render placeholder: `"Run an analysis to see the generated code here"` — centered, gray italic (match existing PlanPanel placeholder style)
  - [x] 3.4: If `code` is populated, render the editor with:
    - Language: `"python"`
    - Theme: `"vs"` (light) or equivalent
    - `readOnly: true` (this story is view-only; editing is Story 10.2)
    - `wordWrap: "off"` (horizontal scroll via editor, not viewport)
    - `minimap: { enabled: false }` (save space)
    - `fontSize: 13`, `lineHeight: 1.4` (per UX spec)
    - `fontFamily`: use `JetBrains Mono, Menlo, Monaco, Consolas, monospace`
  - [x] 3.5: Ensure the editor fills the available height of the Code tab panel (use `height="100%"` or `className="h-full"`)

- [x] Task 4: Replace placeholder in `PlanCodePanel.tsx` Code tab (AC: #1, #5)
  - [x] 4.1: Import `CodeViewerPanel` in `PlanCodePanel.tsx`
  - [x] 4.2: Replace the Code tab placeholder block (lines 87–96) with `<CodeViewerPanel code={code} />`
  - [x] 4.3: The existing tab-switching logic already preserves state in React — no changes needed for AC #4

- [x] Task 5: Manual verification (AC: #1–#6)
  - [x] 5.1: Run an analysis; confirm Code tab shows highlighted Python code
  - [x] 5.2: Switch between Plan ↔ Code tabs; confirm code stays without reloading
  - [x] 5.3: Load fresh session (no analysis); confirm placeholder text appears in Code tab
  - [x] 5.4: Confirm no horizontal viewport scroll at 1280px+ width

## Dev Notes

### What Exists and What to Change

| File | Status | Change Needed |
|------|--------|---------------|
| `src/components/AppLayout.tsx` | ✅ exists | Add `currentCode` state; extract `code` from `/api/report` response; pass as prop to `PlanCodePanel` |
| `src/components/PlanCodePanel.tsx` | ✅ exists | Add `code` prop; replace Code tab placeholder (lines 87–96) with `<CodeViewerPanel code={code} />` |
| `src/components/CodeViewerPanel.tsx` | ❌ create | New component wrapping Monaco/CodeMirror or react-syntax-highlighter |
| `package.json` | ✅ exists | Add chosen library (`@monaco-editor/react` or `react-syntax-highlighter`) |
| `services/api.py` `/api/report` | ✅ already returns `code` | **No change needed** — already returns `pipeline_state.get("generated_code", "")` at line 818 |
| `src/types/api.ts` `ReportData` | ✅ already has `code: string` field | **No change needed** |

### AppLayout Current Gap (Lines 32–35)

```tsx
// Current — code field ignored:
const response = await apiCall<ReportData>('/api/report', 'GET')
if (response.status === 'success' && response.data) {
  setReportCharts(response.data.charts)
  setReportText(response.data.text || null)
  // ← response.data.code exists but is never stored or passed to UI
}
```

**Fix:** Add `setCurrentCode(response.data.code || null)` after `setReportText`.

### PlanCodePanel Code Tab Replacement (Lines 87–96)

```tsx
// BEFORE (current placeholder):
{activeTab === 'code' && (
  <div className="flex-1 overflow-y-auto p-4 flex items-center justify-center">
    <div className="text-center">
      <p className="text-gray-500 text-sm italic">
        {getPlaceholderText()}
      </p>
    </div>
  </div>
)}

// AFTER (with CodeViewerPanel):
{activeTab === 'code' && (
  <div className="flex-1 overflow-hidden flex flex-col">
    <CodeViewerPanel code={code} />
  </div>
)}
```

### Monaco Editor in Next.js 14 — Known SSR Issue

`@monaco-editor/react` uses dynamic imports internally, but you may need to wrap it in `dynamic(() => import('./MonacoEditor'), { ssr: false })` if you encounter hydration errors. Alternatively, wrap the import at the component level:

```tsx
// If SSR errors occur:
const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false })
```

If Monaco causes excessive bundle size or SSR issues, the lightweight alternative is `react-syntax-highlighter` with the `Prism` highlighter and `prism` theme for read-only display. It has no SSR concerns and zero-config Python support.

### State Preservation (AC #4 — Already Handled)

`activeTab` is managed in `AppLayout`, not inside `PlanCodePanel`. React does NOT unmount `PlanCodePanel` when the tab changes — it just conditionally renders different child content. The `code` prop comes from `currentCode` state in `AppLayout`, which persists across renders. **No special memoization is needed.**

### Placeholder Copy

Exact string required by AC #5:
```
"Run an analysis to see the generated code here"
```
Do not use the existing `getPlaceholderText()` helper which currently returns `"[Generated code will be displayed here]"`. Replace with the correct copy or update the helper.

### Project Structure Notes

- New file location: `src/components/CodeViewerPanel.tsx` — follows the flat component pattern (all other panels are in `src/components/`)
- No new API endpoints, hooks, or context changes are needed for this story
- `src/types/api.ts` already defines `ReportData.code: string` — no type changes needed

### References

- `AppLayout.tsx` lines 32–36: gap where `response.data.code` is available but unused [Source: src/components/AppLayout.tsx#L32-L36]
- `PlanCodePanel.tsx` lines 87–96: Code tab placeholder to replace [Source: src/components/PlanCodePanel.tsx#L87-L96]
- `src/types/api.ts` lines 40–44: `ReportData` with `code: string` field already defined [Source: src/types/api.ts#L40-L44]
- `services/api.py` lines 787–820: `/api/report` already returns `generated_code` from pipeline state [Source: services/api.py#L787-L820]
- Architecture: Code viewer uses `PlanCodeTabs.tsx` equivalent (`PlanCodePanel.tsx` in implementation) — [Source: _bmad-output/planning-artifacts/architecture.md]
- UX spec: monospace font 13px, line height 1.4×, Python syntax highlighting [Source: _bmad-output/planning-artifacts/architecture.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — implementation was straightforward with no blocking issues.

### Completion Notes List

- Installed `@monaco-editor/react` (7 packages added); Monaco chosen over `react-syntax-highlighter` per architecture preference.
- SSR issue preempted by wrapping Monaco in `next/dynamic` with `ssr: false` at the component level (`CodeViewerPanel.tsx`), as documented in Dev Notes.
- `AppLayout.tsx`: added `currentCode` state and `setCurrentCode(response.data.code || null)` in `handleExecute`; `ReportData.code` was already typed and returned by the backend — no API changes needed.
- `PlanCodePanel.tsx`: added `code: string | null` prop (Task 1.4), imported `CodeViewerPanel`, replaced Code-tab placeholder block.
- `CodeViewerPanel.tsx` created with all Monaco options per UX spec: Python language, `vs` theme, `readOnly`, `wordWrap: off`, minimap disabled, `fontSize: 13`, `lineHeight: 1.4`, monospace font stack.
- Placeholder text matches AC #5 exactly: `"Run an analysis to see the generated code here"`.
- State preservation (AC #4) required zero additional work — `currentCode` lives in `AppLayout` and is not reset on tab switches.
- `next build` passed cleanly: 0 type errors, 0 lint errors. (exit code 0)

### File List

- src/components/AppLayout.tsx (modified)
- src/components/PlanCodePanel.tsx (modified)
- src/components/CodeViewerPanel.tsx (created)
- package.json (modified — @monaco-editor/react added)
- package-lock.json (modified)

## Change Log

- 2026-03-29: Implemented Story 10.1 — Code Viewer Component. Added Monaco editor in read-only Python mode to the Code tab. Wired `response.data.code` from `/api/report` through `AppLayout` → `PlanCodePanel` → new `CodeViewerPanel` component. SSR handled via `next/dynamic`. Build passes cleanly.
