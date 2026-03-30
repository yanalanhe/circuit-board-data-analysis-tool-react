# Story 11.1: Implement Template Persistence & API Endpoints

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want to save successful analyses as templates in `templates.json` and serve them via API,
So that users can reuse their best analysis patterns across sessions.

## Acceptance Criteria

1. **Given** a successful analysis completes, **when** the user clicks "Save as Template" in the Plan tab, **then** a dialog or input prompts for a template name.

2. **Given** I enter a template name and confirm, **when** the save action is triggered, **then** the frontend sends a POST request to `/api/templates` with `session_id`, `name`, `plan`, and `code`.

3. **Given** the backend receives the template save request, **when** it processes the POST `/api/templates`, **then** it calls `utils/templates.py`'s `save_template()` function.

4. **Given** `save_template()` is called, **when** it executes, **then** the template (`name`, `plan`, `code`) is written to `templates.json` in the backend root directory, formatted as JSON.

5. **Given** the backend starts, **when** it initializes, **then** `load_templates()` from `utils/templates.py` is called and existing templates are loaded into memory.

6. **Given** a GET request to `/api/templates`, **when** the backend receives it, **then** all saved templates are returned as `{status: "success", data: {templates: [...]}}`.

7. **Given** the subprocess sandbox, **when** it runs user code, **then** it cannot write to `templates.json` or any path outside its temp directory — template writes only occur from the backend API layer.

## Tasks / Subtasks

- [x] Task 1: Add in-memory template cache and startup loading in `services/api.py` (AC: #5)
  - [x] 1.1: Import `load_templates` from `utils.templates` at top of `services/api.py`
  - [x] 1.2: Add module-level `_templates: list[dict] = []` variable immediately after imports
  - [x] 1.3: In `startup_event()`, call `_templates.extend(load_templates())` after the `validate_startup_config()` call to populate in-memory cache on startup

- [x] Task 2: Implement `GET /api/templates` endpoint (AC: #6)
  - [x] 2.1: Replace the stub body in `list_templates()` (currently returns `{"data": {"templates": []}}`) with `return {"status": "success", "data": {"templates": _templates}}`

- [x] Task 3: Implement `POST /api/templates` endpoint (AC: #2, #3, #4)
  - [x] 3.1: Import `save_template` from `utils.templates` at top of `services/api.py` (alongside `load_templates`)
  - [x] 3.2: In `save_template_endpoint()` (the POST handler), after session validation, validate that `request.name.strip()` is non-empty — return error `{"message": "Template name cannot be empty", "code": "VALIDATION_ERROR"}` if blank
  - [x] 3.3: Call `save_template(request.name.strip(), request.plan, request.code)` wrapped in a try/except — on `OSError`, return `{"message": "Failed to save template. Check disk permissions.", "code": "SAVE_ERROR"}`
  - [x] 3.4: Append `{"name": request.name.strip(), "plan": request.plan, "code": request.code}` to `_templates` cache (after file write succeeds)
  - [x] 3.5: Return `{"status": "success", "data": {"saved": True, "name": request.name.strip()}}`

- [x] Task 4: Add `TemplateItem` and `TemplatesData` types to `src/types/api.ts` (AC: #2, #6)
  - [x] 4.1: Add `export interface TemplateItem { name: string; plan: string[]; code: string }` to `src/types/api.ts`
  - [x] 4.2: Add `export interface TemplatesData { templates: TemplateItem[] }` to `src/types/api.ts`

- [x] Task 5: Add "Save as Template" button to `PlanPanel.tsx` (AC: #1, #2)
  - [x] 5.1: Add props `onSaveTemplate?: (name: string) => void` and `canSaveTemplate?: boolean` to `PlanPanelProps`
  - [x] 5.2: Add a "Save as Template" button below the Execute button, rendered only when `canSaveTemplate` is true and `intent === 'report'`
  - [x] 5.3: On button click, use `const name = window.prompt('Enter a name for this template:')` — if user enters a non-empty string, call `onSaveTemplate?.(name.trim())`
  - [x] 5.4: Disable the button while saving (add `isSaving` prop `boolean`, default `false`); show "Saving…" label when saving

- [x] Task 6: Thread new props through `PlanCodePanel.tsx` (AC: pass-through)
  - [x] 6.1: Add `onSaveTemplate?: (name: string) => void`, `canSaveTemplate?: boolean`, `isSaving?: boolean`, `savedTemplateCount?: number` to `PlanCodePanelProps`
  - [x] 6.2: Pass all four down to `<PlanPanel />` / template tab

- [x] Task 7: Wire save-template orchestration in `AppLayout.tsx` (AC: #2, #3, #4, #6)
  - [x] 7.1: Add `const [savedTemplates, setSavedTemplates] = useState<TemplateItem[]>([])` and `const [isSavingTemplate, setIsSavingTemplate] = useState(false)` to state declarations
  - [x] 7.2: On app load (in a `useEffect` with empty dep array), call `GET /api/templates` and set `savedTemplates` from response
  - [x] 7.3: Add `canSaveTemplate` computed value: `currentCode !== null && reportCharts.length > 0` (true after a successful analysis)
  - [x] 7.4: Implement `handleSaveTemplate(name: string)`: set `isSavingTemplate(true)`, call `POST /api/templates` with `{ session_id, name, plan: plan ?? [], code: currentCode ?? '' }`, on success append to `savedTemplates`, always `setIsSavingTemplate(false)` in finally block
  - [x] 7.5: Pass `onSaveTemplate={handleSaveTemplate}`, `canSaveTemplate={canSaveTemplate}`, `isSaving={isSavingTemplate}`, `savedTemplateCount={savedTemplates.length}` to `<PlanCodePanel />`

- [x] Task 8: Verify sandbox security (AC: #7 — already enforced, confirm via test)
  - [x] 8.1: Confirm `open` is in `BLOCKED_CALLS` in `pipeline/nodes/validator.py` (line 38) — no code change needed
  - [x] 8.2: Add one test assertion in `tests/test_template_api.py` confirming that a sandboxed code attempt to call `open('templates.json', 'w')` fails AST validation with `BLOCKED_CALLS` error

- [x] Task 9: Create `tests/test_template_api.py` (AC: #2, #3, #4, #5, #6)
  - [x] 9.1: Tests for `GET /api/templates` — returns `{status: "success", data: {templates: []}}` when no templates exist; returns templates list after saving
  - [x] 9.2: Tests for `POST /api/templates` — success case: valid session + name/plan/code → writes file, returns `{saved: True, name: ...}`
  - [x] 9.3: Test POST — invalid session → `INVALID_SESSION` error
  - [x] 9.4: Test POST — empty name → `VALIDATION_ERROR` error
  - [x] 9.5: Test POST — in-memory cache updated after save (subsequent GET includes new template)
  - [x] 9.6: Test startup loads templates from file (mock `load_templates` and verify it is called during `startup_event`)
  - [x] 9.7: Test AC #7 sandbox security — verify `open('templates.json', 'w')` in code string fails `validate_code()` with a blocked-call error

- [x] Task 10: Manual verification (AC: #1–#7)
  - [x] 10.1: Start backend, confirm no startup errors; `GET /api/templates` returns `{templates: []}` (no file yet)
  - [x] 10.2: Run a full analysis; confirm "Save as Template" button appears in Plan tab
  - [x] 10.3: Click "Save as Template", enter name "Test Analysis", confirm POST is sent and `templates.json` is created in project root
  - [x] 10.4: Refresh backend (restart); confirm `GET /api/templates` returns the saved template (startup load working)
  - [x] 10.5: Confirm saving a template with a blank name shows an error (doesn't save)

## Dev Notes

### What Exists vs. What to Implement

| File / Symbol | Status | Change |
|---|---|---|
| `utils/templates.py` `load_templates()` | ✅ Fully implemented | No change — read file, returns list |
| `utils/templates.py` `save_template()` | ✅ Fully implemented | No change — appends to file |
| `services/models.py` `TemplateObject` | ✅ Fully defined | No change |
| `services/models.py` `TemplatesResponse` | ✅ Fully defined | No change |
| `services/models.py` `SaveTemplateRequest` | ✅ Fully defined (session_id, name, plan, code) | No change |
| `services/api.py` `GET /api/templates` | ⚠️ STUB — returns `{"templates": []}` hardcoded | Replace with `_templates` cache return |
| `services/api.py` `POST /api/templates` | ⚠️ STUB — validates session, returns `{}`, doesn't save | Implement `save_template()` call |
| `services/api.py` `startup_event()` | ⚠️ Partial — only calls `validate_startup_config()` | Add `_templates.extend(load_templates())` |
| `src/components/PlanPanel.tsx` | ⚠️ No "Save as Template" button | Add button + `window.prompt()` |
| `src/components/PlanCodePanel.tsx` | ⚠️ No template save props | Add 3 pass-through props |
| `src/components/AppLayout.tsx` | ⚠️ No template save state/handler | Add state + `handleSaveTemplate` |
| `src/types/api.ts` | ⚠️ No Template types | Add `TemplateItem`, `TemplatesData` |
| `pipeline/nodes/validator.py` `BLOCKED_CALLS` | ✅ Already blocks `open()` (line 38) | No change — sandbox security confirmed |
| `tests/test_template_save_reuse.py` | ✅ Covers `utils/templates.py` functions | No change — regression guards in place |

### Backend Implementation Detail — `services/api.py`

**Module-level cache pattern (follow this pattern at top of file):**
```python
from utils.templates import load_templates, save_template

# In-memory templates cache — populated at startup, updated on save
_templates: list[dict] = []
```

**Updated `startup_event`:**
```python
@app.on_event("startup")
async def startup_event():
    """Run validations and setup on application startup."""
    global _templates
    try:
        validate_startup_config()
    except ValueError as e:
        print(f"❌ Startup validation failed: {e}")
        raise
    _templates.extend(load_templates())
```

**Implemented `GET /api/templates`:**
```python
@app.get("/api/templates", response_model=dict)
async def list_templates() -> dict:
    return {
        "status": "success",
        "data": {"templates": _templates}
    }
```

**Implemented `POST /api/templates`:**
```python
@app.post("/api/templates", response_model=dict)
async def save_template_endpoint(request: SaveTemplateRequest) -> dict:
    global _templates
    session = require_session(request.session_id)
    if "error" in session:
        return session

    name = request.name.strip() if request.name else ""
    if not name:
        return {
            "status": "error",
            "error": {
                "message": "Template name cannot be empty",
                "code": "VALIDATION_ERROR"
            }
        }

    try:
        save_template(name, request.plan, request.code)
    except OSError as e:
        return {
            "status": "error",
            "error": {
                "message": "Failed to save template. Check disk permissions.",
                "code": "SAVE_ERROR"
            }
        }

    _templates.append({"name": name, "plan": request.plan, "code": request.code})

    return {
        "status": "success",
        "data": {"saved": True, "name": name}
    }
```

> ⚠️ **Naming conflict**: The existing function name `save_template` in `api.py` collides with `save_template` from `utils.templates`. Use aliased import: `from utils.templates import save_template as _write_template` and call `_write_template(name, request.plan, request.code)`. The FastAPI handler function should be renamed `save_template_endpoint` (matching the existing stub name convention) or kept as `save_template` with the import alias.

> ⚠️ **Current stub name**: The existing stub endpoint function at `services/api.py` line 959 is already named `save_template` — this conflicts with `from utils.templates import save_template`. Use the aliased import approach above.

### Frontend Implementation Detail

**`src/types/api.ts` additions:**
```typescript
export interface TemplateItem {
  name: string
  plan: string[]
  code: string
}

export interface TemplatesData {
  templates: TemplateItem[]
}
```

**`PlanPanel.tsx` additions (AC #1):**
```tsx
interface PlanPanelProps {
  plan: string[] | null
  intent: 'report' | 'qa' | 'chat'
  isExecuting: boolean
  onExecute: () => void
  onSaveTemplate?: (name: string) => void
  canSaveTemplate?: boolean
  isSaving?: boolean
}

// In the footer section, below the Execute button:
{canSaveTemplate && (
  <button
    onClick={() => {
      const name = window.prompt('Enter a name for this template:')
      if (name && name.trim()) {
        onSaveTemplate?.(name.trim())
      }
    }}
    disabled={isSaving}
    className="w-full mt-2 py-2 px-4 rounded-md font-medium text-blue-600 border border-blue-600 bg-white hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
  >
    {isSaving ? 'Saving…' : 'Save as Template'}
  </button>
)}
```

**`AppLayout.tsx` additions:**
```tsx
import { TemplateItem, TemplatesData } from '@/types/api'

// New state:
const [savedTemplates, setSavedTemplates] = useState<TemplateItem[]>([])
const [isSavingTemplate, setIsSavingTemplate] = useState(false)

// Load templates on mount:
useEffect(() => {
  apiCall<TemplatesData>('/api/templates', 'GET').then((response) => {
    if (response.status === 'success' && response.data) {
      setSavedTemplates(response.data.templates)
    }
  })
}, [apiCall])

// canSaveTemplate — true after successful execution:
const canSaveTemplate = currentCode !== null && reportCharts.length > 0

// Handler:
const handleSaveTemplate = useCallback(async (name: string) => {
  setIsSavingTemplate(true)
  try {
    const response = await apiCall('/api/templates', 'POST', {
      session_id,
      name,
      plan: plan ?? [],
      code: currentCode ?? '',
    })
    if (response.status === 'success') {
      setSavedTemplates((prev) => [...prev, { name, plan: plan ?? [], code: currentCode ?? '' }])
    }
  } catch (error) {
    console.error('Save template failed:', error)
  } finally {
    setIsSavingTemplate(false)
  }
}, [apiCall, session_id, plan, currentCode])

// In JSX, add to <PlanCodePanel>:
// onSaveTemplate={handleSaveTemplate}
// canSaveTemplate={canSaveTemplate}
// isSaving={isSavingTemplate}
```

> ⚠️ **`plan` state in AppLayout**: Currently `const [plan] = useState<string[] | null>(null)` — `plan` is initialized but never updated (hardcoded null from story 2.2 stub). Story 11.1 needs plan to be populated from the chat response. The `handleSaveTemplate` sends `plan ?? []`. If plan is null at save time, templates will have empty plan arrays. This is acceptable for story 11.1 — story 11.2 can improve this if needed. However, the dev agent may want to check if `plan` is populated in `session["pipeline_state"]` from prior stories (it should be — chat stores it). The save action will pull from the AppLayout `plan` state.

### Sandbox Security — Already Enforced (AC #7)

`pipeline/nodes/validator.py` line 38:
```python
BLOCKED_CALLS = frozenset({"eval", "exec", "__import__", "open"})
```

`open()` is explicitly blocked. Any generated code that attempts `open('templates.json', 'w')` will fail the AST validation step before reaching the subprocess. No code change needed — only a test to confirm.

### Test Pattern (follow existing `test_put_code_endpoint.py`)

```python
# tests/test_template_api.py
import pytest
import json
from unittest.mock import patch, MagicMock
import uuid

@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from services.api import app
    return TestClient(app)

@pytest.fixture
def mock_session_id():
    """Register a real session and return its ID."""
    from services.session import create_session
    session = create_session()
    return session["session_id"]

def test_list_templates_empty(test_client, monkeypatch):
    """GET /api/templates returns success with empty list when no templates."""
    import services.api as api_module
    monkeypatch.setattr(api_module, "_templates", [])
    response = test_client.get("/api/templates")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["templates"] == []

def test_save_template_success(test_client, mock_session_id, tmp_path, monkeypatch):
    """POST /api/templates saves and returns confirmation."""
    import services.api as api_module
    monkeypatch.setattr(api_module, "_templates", [])
    monkeypatch.setattr("utils.templates.TEMPLATES_FILE", str(tmp_path / "templates.json"))

    response = test_client.post("/api/templates", json={
        "session_id": mock_session_id,
        "name": "My Analysis",
        "plan": ["step 1", "step 2"],
        "code": "import pandas as pd"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["saved"] is True
    assert body["data"]["name"] == "My Analysis"
```

### Project Structure Notes

- **Files changed (backend):** `services/api.py` only — add import, module cache, startup load, implement 2 stubs
- **Files changed (frontend):** `src/types/api.ts`, `src/components/PlanPanel.tsx`, `src/components/PlanCodePanel.tsx`, `src/components/AppLayout.tsx`
- **New test file:** `tests/test_template_api.py`
- **No new backend files** — `utils/templates.py` and `services/models.py` are fully implemented
- **`templates.json` location**: backend root dir (`c:\...\circuit-board-data-analysis-tool-react\templates.json`), created on first save
- **No new Python dependencies**
- **No new npm packages**

### References

- `utils/templates.py` lines 1–36: `load_templates()` and `save_template()` — fully implemented [Source: utils/templates.py]
- `services/api.py` lines 85–91: `startup_event` — add `_templates.extend(load_templates())` here [Source: services/api.py#L85-L91]
- `services/api.py` lines 944–956: `GET /api/templates` stub — replace body [Source: services/api.py#L944-L956]
- `services/api.py` lines 959–980: `POST /api/templates` stub — replace body [Source: services/api.py#L959-L980]
- `services/models.py` lines 149–166: `TemplateObject`, `TemplatesResponse`, `SaveTemplateRequest` — use these models, no change [Source: services/models.py#L149-L166]
- `pipeline/nodes/validator.py` line 38: `BLOCKED_CALLS` blocks `open()` — sandbox security already enforced [Source: pipeline/nodes/validator.py#L38]
- `src/components/PlanPanel.tsx` lines 55–71: footer section where "Save as Template" button goes [Source: src/components/PlanPanel.tsx#L55-L71]
- `src/components/PlanCodePanel.tsx` lines 7–18: Props interface to extend with 3 template props [Source: src/components/PlanCodePanel.tsx#L7-L18]
- `src/components/AppLayout.tsx` lines 11–23: State declarations; lines 49–77: `handleRerun` pattern to follow [Source: src/components/AppLayout.tsx#L11-L77]
- `src/types/api.ts`: Add `TemplateItem` and `TemplatesData` interfaces [Source: src/types/api.ts]
- Architecture: Template Persistence section — `templates.json` is scoped exception to no-persistence rule [Source: _bmad-output/planning-artifacts/architecture.md#L225-L230]
- Architecture: Project Structure — `templates.json` in backend root [Source: _bmad-output/planning-artifacts/architecture.md#L624-L628]
- `tests/test_template_save_reuse.py`: Existing `utils/templates.py` tests — monkeypatch pattern to follow for new API tests [Source: tests/test_template_save_reuse.py]
- `tests/test_put_code_endpoint.py` lines 18–60: Test fixture pattern with `TestClient` and session mock [Source: tests/test_put_code_endpoint.py#L18-L60]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Startup test failures (2): `monkeypatch.setattr("utils.templates.load_templates", ...)` does not affect the already-bound name in `services.api` (imported via `from utils.templates import load_templates`). Fixed by patching `services.api.load_templates` directly and using `.clear()` + `.extend()` on the module-level list in-place.

### Completion Notes List

- Implemented `GET /api/templates`: replaces stub — returns `_templates` in-memory cache; no session required (global templates).
- Implemented `POST /api/templates`: replaces stub — validates name (non-empty), calls `_write_template()` (aliased from `utils.templates.save_template` to avoid function name collision with endpoint), appends to `_templates` cache, returns `{saved: True, name}`.
- Added startup loading: `startup_event()` now calls `_templates.extend(load_templates())` after config validation — templates.json contents available from first request.
- Import alias used: `from utils.templates import save_template as _write_template` — avoids collision with the FastAPI handler function also named `save_template`.
- Added `TemplateItem` and `TemplatesData` TypeScript interfaces to `src/types/api.ts`.
- Added "Save as Template" button to `PlanPanel.tsx`: appears only when `canSaveTemplate=true` (set after successful analysis), uses `window.prompt()` for name, disabled while saving.
- Threaded `onSaveTemplate`, `canSaveTemplate`, `isSaving`, `savedTemplateCount` through `PlanCodePanel.tsx`.
- Added `AppLayout.tsx` template state: `savedTemplates` (loaded on mount from `GET /api/templates`), `isSavingTemplate`, `handleSaveTemplate` callback, `canSaveTemplate` computed from `currentCode !== null && reportCharts.length > 0`.
- Template tab placeholder in `PlanCodePanel` now shows template count when templates exist.
- Removed now-unused `getPlaceholderText()` function from `PlanCodePanel`.
- AC #7 sandbox security confirmed: `open` is in `BLOCKED_CALLS` in `pipeline/nodes/validator.py` — no code change needed.
- 15 new backend tests all pass. `next build` exits 0. 0 TypeScript errors in `src/`. 15 pre-existing failures in `test_chat_api.py`, `test_execute_endpoint.py`, `test_langsmith_integration.py` — unchanged.

### File List

- services/api.py (modified — added import alias, `_templates` cache, startup loading, implemented GET + POST `/api/templates`)
- src/types/api.ts (modified — added `TemplateItem`, `TemplatesData` interfaces)
- src/components/PlanPanel.tsx (modified — added `onSaveTemplate`, `canSaveTemplate`, `isSaving` props + "Save as Template" button)
- src/components/PlanCodePanel.tsx (modified — added `onSaveTemplate`, `canSaveTemplate`, `isSaving`, `savedTemplateCount` props; removed unused `getPlaceholderText`; updated template tab placeholder)
- src/components/AppLayout.tsx (modified — added `useEffect` import, `TemplateItem`/`TemplatesData` imports, `savedTemplates`/`isSavingTemplate` state, `canSaveTemplate` computed, `handleSaveTemplate` handler, `savedTemplateCount` prop to `PlanCodePanel`)
- tests/test_template_api.py (created — 15 tests covering GET/POST endpoints, cache consistency, startup loading, sandbox security)

## Change Log

- 2026-03-29: Implemented Story 11.1 — Template Persistence & API Endpoints. Replaced GET/POST `/api/templates` stubs with full implementations. Added in-memory `_templates` cache populated at startup. Added "Save as Template" button to Plan tab (window.prompt for name, disabled while saving). Threaded template props through component tree. 15 new backend tests pass. Build clean (0 TS errors, next build ✓).
