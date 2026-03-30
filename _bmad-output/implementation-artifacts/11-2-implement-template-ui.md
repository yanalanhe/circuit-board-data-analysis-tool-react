# Story 11.2: Implement Template UI & Template Application

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an engineer,
I want to view all my saved templates and quickly apply them to new datasets,
So that I can reuse my best analysis patterns without retyping them.

## Acceptance Criteria

1. **Given** the Template tab, **when** I click it, **then** it displays a list of all previously saved templates, each with a name and optional preview (plan summary or code snippet).

2. **Given** I select a saved template from the list, **when** I click "Apply" (or double-click the template), **then** the template's plan is loaded into the Plan tab and the template's code is loaded into the Code tab editor.

3. **Given** a template is applied, **when** the content loads, **then** React state is updated but no API call is re-triggered (the plan and code are already in the template).

4. **Given** I apply a template, **when** the Plan tab shows the plan, **then** an "Execute" button is visible to run the templated analysis on the current (new) dataset.

5. **Given** the app loads, **when** React initializes, **then** the Template tab is automatically populated with saved templates (via GET `/api/templates` on app load — already implemented in Story 11.1).

6. **Given** a template is deleted (if delete functionality is added), **when** the user confirms deletion, **then** the template is removed from `templates.json` and the list is refreshed. **[DEFERRED — implement as stretch goal only if time allows]**

## Tasks / Subtasks

- [x] Task 1: Make `plan` and `intent` states mutable in `AppLayout.tsx` (AC: #2, #4)
  - [x] 1.1: Change `const [plan] = useState<string[] | null>(null)` → `const [plan, setPlan] = useState<string[] | null>(null)`
  - [x] 1.2: Change `const [intent] = useState<'report' | 'qa' | 'chat'>('chat')` → `const [intent, setIntent] = useState<'report' | 'qa' | 'chat'>('chat')`

- [x] Task 2: Add `handleApplyTemplate` in `AppLayout.tsx` (AC: #2, #3, #4)
  - [x] 2.1: Add `handleApplyTemplate` callback: sets `plan` to `template.plan`, sets `currentCode` to `template.code`, sets `intent` to `'report'`, switches `activeTab` to `'plan'` — zero API calls
  - [x] 2.2: Pass `savedTemplates` and `onApplyTemplate={handleApplyTemplate}` as new props to `<PlanCodePanel />`

- [x] Task 3: Add new props to `PlanCodePanelProps` (AC: #1, #2)
  - [x] 3.1: Add `savedTemplates: TemplateItem[]` and `onApplyTemplate: (template: TemplateItem) => void` to `PlanCodePanelProps` interface
  - [x] 3.2: Destructure and forward both props; kept `savedTemplateCount` as optional for backward compat (Option A from Dev Notes); renamed destructured to `_savedTemplateCount` to suppress unused-var error

- [x] Task 4: Implement Template tab content in `PlanCodePanel.tsx` (AC: #1, #2)
  - [x] 4.1: Replaced placeholder Template tab block with full list UI — empty-state when no templates, scrollable card list when templates exist
  - [x] 4.2: Each template card shows: `name` (bold, truncated), snippet preview (first plan step or first 80 chars of code, with ellipsis)
  - [x] 4.3: "Apply" button calls `onApplyTemplate?.(template)`; double-click on card also triggers `onApplyTemplate?.(template)`

- [ ] Task 5: Add tests in `tests/test_template_apply.tsx` (or `.test.tsx`) (AC: #1–#4)
  - [ ] 5.1: Template tab renders "No templates saved yet" when `savedTemplates` is empty
  - [ ] 5.2: Template tab renders one card per template when `savedTemplates` has items
  - [ ] 5.3: Clicking "Apply" calls `onApplyTemplate` with the correct `TemplateItem`
  - [ ] 5.4: In `AppLayout`, calling `handleApplyTemplate` sets `plan`, `currentCode`, `intent`, and `activeTab` correctly (use React Testing Library)
  **[SKIPPED — no Jest/@testing-library installed; install deps if frontend tests are needed later]**

- [x] Task 6: Manual verification (AC: #1–#5)
  - [x] 6.1: Start app; click Template tab with no templates → see empty-state message
  - [x] 6.2: Run an analysis, save as template; click Template tab → see template card with name and snippet
  - [x] 6.3: Click "Apply" → Plan tab becomes active, shows plan; Code tab shows template code
  - [x] 6.4: Click "Execute" → pipeline runs on current dataset using templated plan/code
  - [x] 6.5: Refresh page → Template tab still populated (templates loaded from backend via `GET /api/templates` on mount)

## Dev Notes

### What Exists vs. What to Build

| File / Symbol | Status | Change |
|---|---|---|
| `services/api.py` `GET /api/templates` | ✅ Fully implemented (Story 11.1) | No change |
| `services/api.py` `POST /api/templates` | ✅ Fully implemented (Story 11.1) | No change |
| `utils/templates.py` | ✅ Fully implemented | No change |
| `src/types/api.ts` `TemplateItem` | ✅ Defined in Story 11.1 | No change |
| `src/types/api.ts` `TemplatesData` | ✅ Defined in Story 11.1 | No change |
| `AppLayout.tsx` `savedTemplates` state | ✅ Exists, loaded on mount (Story 11.1) | Add `handleApplyTemplate`, pass `savedTemplates` down |
| `AppLayout.tsx` `plan` state | ⚠️ `useState` has NO setter exposed (`const [plan] = ...`) | Add setter: `const [plan, setPlan] = useState...` |
| `AppLayout.tsx` `intent` state | ⚠️ `useState` has NO setter exposed (`const [intent] = ...`) | Add setter: `const [intent, setIntent] = useState...` |
| `PlanCodePanel.tsx` Template tab | ⚠️ PLACEHOLDER only | Implement full template list UI |
| `PlanCodePanel.tsx` `savedTemplateCount` prop | ⚠️ Count-only, insufficient for UI | Add `savedTemplates: TemplateItem[]` and `onApplyTemplate` props |

### Critical: `plan` and `intent` State Setters Missing

In `AppLayout.tsx` (lines 15–16):
```tsx
// CURRENT (Story 11.1 left these as read-only because plan was never populated there):
const [plan] = useState<string[] | null>(null)
const [intent] = useState<'report' | 'qa' | 'chat'>('chat')

// CHANGE TO (destructure setter):
const [plan, setPlan] = useState<string[] | null>(null)
const [intent, setIntent] = useState<'report' | 'qa' | 'chat'>('chat')
```

The Story 11.1 dev note flagged this: *"plan is initialized but never updated — Story 11.2 can improve this."* Template application is the trigger.

### `handleApplyTemplate` Implementation

```tsx
const handleApplyTemplate = useCallback((template: TemplateItem) => {
  setPlan(template.plan)
  setCurrentCode(template.code)
  setIntent('report')   // templates always come from successful report analyses
  setActiveTab('plan')  // switch to plan tab so user sees the loaded plan
  // ⚠️ NO API CALLS — all data is already client-side in the template object (AC #3)
}, [])
```

Key behavior:
- **No API call** — template plan and code are already in React state from the `GET /api/templates` call on mount (Story 11.1)
- **Tab switch to plan** — user should immediately see the plan ready to execute (AC #4)
- **Execute button** — `PlanPanel.tsx` already renders the Execute button when `plan` is non-null and `intent === 'report'` (confirmed in Story 10.x work)

### Props Threading

Add to `<PlanCodePanel />` JSX in `AppLayout.tsx`:
```tsx
<PlanCodePanel
  {/* ... existing props ... */}
  savedTemplates={savedTemplates}           // NEW: full template objects, not just count
  onApplyTemplate={handleApplyTemplate}     // NEW
  savedTemplateCount={savedTemplates.length} // KEEP: still used for Plan tab badge (Story 11.1)
/>
```

### Template Tab Component (in `PlanCodePanel.tsx`)

Replace lines 106–117 (the placeholder block):

```tsx
{/* Template Tab */}
{activeTab === 'template' && (
  <div className="flex-1 overflow-y-auto p-4">
    {savedTemplates.length === 0 ? (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400 text-sm text-center italic">
          No templates saved yet.<br />
          Save a successful analysis using the &quot;Save as Template&quot; button in the Plan tab.
        </p>
      </div>
    ) : (
      <ul className="space-y-3">
        {savedTemplates.map((template, idx) => (
          <li
            key={idx}
            className="border border-gray-200 rounded-md p-3 hover:border-blue-300 cursor-pointer transition-colors"
            onDoubleClick={() => onApplyTemplate(template)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm text-gray-900 truncate">
                  {template.name}
                </p>
                <p className="text-xs text-gray-500 mt-1 truncate">
                  {template.plan[0]
                    ? template.plan[0].slice(0, 80) + (template.plan[0].length > 80 ? '…' : '')
                    : template.code.slice(0, 80) + (template.code.length > 80 ? '…' : '')}
                </p>
              </div>
              <button
                onClick={() => onApplyTemplate(template)}
                className="flex-shrink-0 px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700 transition-colors"
              >
                Apply
              </button>
            </div>
          </li>
        ))}
      </ul>
    )}
  </div>
)}
```

**Style rationale:**
- Scrollable list in the same panel container — consistent with Plan tab layout
- Double-click on card OR click "Apply" button both trigger application (AC #2)
- Empty state message guides user to the save flow (no dead ends — UX principle)
- `truncate` on preview snippet — keeps cards compact, same height

### Handling `savedTemplateCount` prop

`savedTemplateCount` was added in Story 11.1 to show a badge in the template tab. Since we're now passing full `savedTemplates`, you can derive the count. Two options:
- **Option A (preferred):** Keep `savedTemplateCount` as-is (already wired), add the new `savedTemplates` and `onApplyTemplate` props separately — avoids any prop removal risk
- **Option B:** Remove `savedTemplateCount` and derive it as `savedTemplates.length` inside `PlanCodePanel` — cleaner but breaking change to prop interface

**Use Option A** to minimize diff and risk of regressions.

### Architecture Compliance

From Architecture doc:
- **`activeTemplate` state** (Architecture session schema line 184): The arch doc defines `activeTemplate: { name; plan; code } | null`. This story does NOT need to add this state explicitly — applying a template directly sets `plan`, `code`, and `intent` in existing state vars. `activeTemplate` tracking would be a UX enhancement (e.g., showing which template is "active") — defer to post-MVP unless needed for the Execute flow.
- **Tab state preservation** (Architecture cross-cutting concern #4): Tab switches must NOT re-trigger API calls. Template application only mutates React state — compliant.
- **No new API endpoints** — all data flows are client-side after initial `GET /api/templates` on mount.
- **No new Python dependencies**
- **No new npm packages**

### File Structure Impact

```
src/
  components/
    AppLayout.tsx          # MODIFY: add setPlan/setIntent setters, handleApplyTemplate, pass new props
    PlanCodePanel.tsx      # MODIFY: add savedTemplates/onApplyTemplate props, replace template tab placeholder
```

No new files required.

### UX Design Alignment

From UX spec:
- *"Switching between Plan / Code / Template tabs — one click; state preserved; no re-generation"* ✅
- *"'Save as Template' management UI in Template tab"* — Phase 3 (post-MVP); delete functionality deferred ✅
- *"No dead ends — Error messages use plain language, state what happened, and offer one clear next action"* → empty-state message guides to Plan tab "Save as Template" button ✅

### Previous Story Intelligence (from Story 11.1)

1. **`plan` state was never set** — story 11.1 noted: *"plan is initialized but never updated. Story 11.2 can improve this."* The fix is exposing the `setPlan` setter (Task 1.1 above).
2. **`window.prompt` for save name** — established pattern in 11.1; no change needed here.
3. **`apiCall` dependency in `useEffect`** — story 11.1 used `[apiCall]` as dep array for mount-time template load. Follow the same pattern.
4. **Naming alias for `save_template`** — backend only; no frontend impact for 11.2.
5. **15 backend tests pass, `next build` exits 0** — regression baseline to maintain.

### Testing Pattern

Follow `src/components/__tests__/` pattern if it exists, or create `tests/` alongside components. Use React Testing Library:

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import PlanCodePanel from '@/components/PlanCodePanel'
import { TemplateItem } from '@/types/api'

const mockTemplate: TemplateItem = {
  name: 'Failure Rate Analysis',
  plan: ['Load CSV', 'Compute failure rates by batch', 'Plot bar chart'],
  code: 'import pandas as pd\ndf = pd.read_csv(...)',
}

it('renders empty state when no templates', () => {
  render(
    <PlanCodePanel
      activeTab="template"
      onTabChange={() => {}}
      savedTemplates={[]}
      onApplyTemplate={() => {}}
      // ... other required props
    />
  )
  expect(screen.getByText(/No templates saved yet/i)).toBeInTheDocument()
})

it('renders template card and calls onApplyTemplate on Apply click', () => {
  const handleApply = jest.fn()
  render(
    <PlanCodePanel
      activeTab="template"
      onTabChange={() => {}}
      savedTemplates={[mockTemplate]}
      onApplyTemplate={handleApply}
      // ... other required props
    />
  )
  expect(screen.getByText('Failure Rate Analysis')).toBeInTheDocument()
  fireEvent.click(screen.getByText('Apply'))
  expect(handleApply).toHaveBeenCalledWith(mockTemplate)
})
```

### References

- `AppLayout.tsx` line 15: `const [plan] = useState` — change to expose setter [Source: src/components/AppLayout.tsx#L15]
- `AppLayout.tsx` line 16: `const [intent] = useState` — change to expose setter [Source: src/components/AppLayout.tsx#L16]
- `AppLayout.tsx` lines 62–83: `handleSaveTemplate` — follow same `useCallback` pattern for `handleApplyTemplate` [Source: src/components/AppLayout.tsx#L62-L83]
- `AppLayout.tsx` lines 125–140: `<PlanCodePanel />` JSX — add `savedTemplates` and `onApplyTemplate` props here [Source: src/components/AppLayout.tsx#L125-L140]
- `PlanCodePanel.tsx` lines 7–22: `PlanCodePanelProps` — add new props [Source: src/components/PlanCodePanel.tsx#L7-L22]
- `PlanCodePanel.tsx` lines 106–117: Template tab placeholder — replace with full list UI [Source: src/components/PlanCodePanel.tsx#L106-L117]
- `src/types/api.ts` lines 49–57: `TemplateItem`, `TemplatesData` — import in AppLayout for `handleApplyTemplate` typing [Source: src/types/api.ts#L49-L57]
- Architecture: Session state schema — `activeTemplate` field (arch doc) is optional for this story [Source: _bmad-output/planning-artifacts/architecture.md#L184]
- Architecture: Tab state preservation (cross-cutting concern #4) — no API calls on tab switch [Source: _bmad-output/planning-artifacts/architecture.md#L80]
- Story 11.1 dev notes — `plan` state setter gap explicitly flagged [Source: _bmad-output/implementation-artifacts/11-1-implement-template-persistence-api.md#L274]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- TypeScript build error: `savedTemplateCount` declared but never read after template tab placeholder replaced with full UI. Fixed by renaming destructured binding to `_savedTemplateCount = 0` — keeps the prop interface backward-compatible (Option A from Dev Notes) while satisfying the `noUnusedLocals` TS rule.

### Completion Notes List

- Exposed `setPlan` and `setIntent` setters in `AppLayout.tsx` (previously read-only `const [plan] = useState...`). This was flagged as a gap in Story 11.1 dev notes.
- Added `handleApplyTemplate` callback in `AppLayout.tsx`: pure state mutation — sets `plan`, `currentCode`, `intent='report'`, `activeTab='plan'`. Zero API calls (AC #3 compliance).
- Passed `savedTemplates` (full `TemplateItem[]`) and `onApplyTemplate` as new props to `<PlanCodePanel />` alongside existing `savedTemplateCount` (kept for backward compat).
- Added `TemplateItem` import to `PlanCodePanel.tsx`; added `savedTemplates?: TemplateItem[]` and `onApplyTemplate?: (template: TemplateItem) => void` to `PlanCodePanelProps`.
- Replaced placeholder Template tab with full list UI: empty-state message with actionable hint when no templates; scrollable card list with name, snippet preview (first plan step or first 80 chars of code), and Apply button; double-click on card also triggers apply.
- `next build` exits 0. ESLint clean on both modified files. 0 TypeScript errors.
- Task 5 (automated frontend tests) blocked: no Jest / @testing-library/react installed in project. Awaiting user decision on adding test dependencies.

### File List

- src/components/AppLayout.tsx (modified — exposed setPlan/setIntent setters; added handleApplyTemplate callback; passed savedTemplates and onApplyTemplate to PlanCodePanel)
- src/components/PlanCodePanel.tsx (modified — added TemplateItem import; added savedTemplates/onApplyTemplate props; replaced template tab placeholder with full card list UI)

## Change Log

- 2026-03-29: Implemented Story 11.2 — Template UI & Template Application. Exposed setPlan/setIntent state setters in AppLayout.tsx. Added handleApplyTemplate (pure client-side state mutation, zero API calls). Added savedTemplates and onApplyTemplate props through PlanCodePanel. Replaced template tab placeholder with full list UI: empty-state message, scrollable card list with name/snippet/Apply button and double-click support. next build ✓, ESLint clean, 0 TS errors. Task 5 (frontend unit tests) deferred — no Jest/@testing-library installed.
