---
epic: 2
story: 2
status: review
story_key: 2-2-implement-four-panel-layout
created: 2026-03-26
last_updated: 2026-03-26
---

# Story 2.2: Implement Four-Panel Layout Component

**Status:** review

**Epic:** 2 - Frontend Application Shell & Navigation

**Dependencies:** Story 2.1 (Next.js frontend initialized with TypeScript and Tailwind CSS)

**Blocks:** Story 3.1 (CSV Upload), Story 4.1 (Chat Interface), Story 5.1 (Plan Display), Story 8.1 (Report Panel)

## Story Statement

As an engineer,
I want to see a four-panel layout on the app with distinct regions for chat, plan/code, data table, and report,
So that I can see all relevant information at once without scrolling.

## Acceptance Criteria

**Given** the app loads at localhost:3000
**When** I view it on a 1280px+ wide screen
**Then** I see four panels: chat (top-left 25%), plan/code tabs (top-right 25%), data table (bottom-left 50% width), report (bottom-right 50% width) — no horizontal scrolling

**Given** the layout at desktop resolution
**When** I measure the panels
**Then** they are visually balanced with clear borders or spacing between them

**Given** each panel
**When** I view it
**Then** it has a title/header identifying its purpose (Chat, Plan/Code/Template, Data, Report)

**Given** the four-panel layout component
**When** I inspect `src/components/AppLayout.tsx`
**Then** it uses flexbox or CSS grid to manage the layout, with responsive behavior (stacked on narrow screens is fine)

**Given** the app at startup
**When** no data or results exist yet
**Then** the data and report panels show placeholder text: "Upload data to get started" and "Run an analysis to see results"

---

## Technical Requirements & Architecture Compliance

### Layout Specification

**Grid Structure:**
- Desktop layout (1280px+): 2x2 grid with unequal cells
  - Top-left: Chat panel (25% width, flexible height)
  - Top-right: Plan/Code/Template tabs panel (25% width, flexible height)
  - Bottom-left: Data table panel (50% width, flexible height)
  - Bottom-right: Report panel (50% width, flexible height)
- Total height: Full viewport height minus header
- Responsive: Panels stack vertically on screens <1280px (mobile-first not required for MVP)

**Grid Implementation:**
- Use CSS Grid or Flexbox (Tailwind Grid is recommended for clean syntax)
- No external grid library; Tailwind CSS Grid utilities provide sufficient control
- Borders: 1px solid border between panels (e.g., `border-gray-200`) for visual separation
- Spacing: 0 padding between panel borders; internal padding within each panel component

**CSS Grid Template (recommended):**
```css
display: grid;
grid-template-columns: 1fr 1fr;     /* Two equal columns */
grid-template-rows: auto auto;       /* Two equal rows */
gap: 0;                              /* No gap between panels */
height: 100vh;                       /* Full viewport height */
```

### Component Structure

**Root Component (`src/app/page.tsx`):**
- Already a client component (`"use client"` directive from Story 2.1)
- Should render `<AppLayout />` instead of placeholder content
- Pass any session/global state as props if needed

**Layout Component (`src/components/AppLayout.tsx`):**
- Main container component that manages the 2x2 grid
- Renders four child panel components:
  - `<ChatPanel />` — top-left
  - `<PlanCodePanel />` — top-right (with tabs for Plan, Code, Template)
  - `<DataPanel />` — bottom-left
  - `<ReportPanel />` — bottom-right
- Manages active tab state (which tab is visible in the Plan/Code panel)
- No business logic; purely layout management

**Panel Components (placeholder stubs for Story 2.2):**
- `src/components/ChatPanel.tsx` — chat input area and message history (placeholder for Story 4.1)
- `src/components/PlanCodePanel.tsx` — tabbed interface for Plan/Code/Template views (placeholder for Stories 5.1, 10.1, 11.1)
- `src/components/DataPanel.tsx` — CSV upload area and data table (placeholder for Story 3.1-3.2)
- `src/components/ReportPanel.tsx` — chart and trend analysis display (placeholder for Story 8.1)

### Panel Headers & Styling

**Header Requirements:**
- Each panel has a fixed header (approx 40-50px height) with:
  - Panel title (bold, 14-16px font)
  - Optional sub-title or status indicator (optional for future stories)
- Headers use a background color distinct from panel body (e.g., `bg-gray-50` or `bg-blue-50`)
- Border between header and content

**Example Header Style:**
```jsx
<div className="border-b border-gray-200 bg-gray-50 p-3">
  <h2 className="font-bold text-sm">Chat</h2>
</div>
```

**Panel Body:**
- Background: white (`bg-white`)
- Padding: 16px default (can be adjusted per panel)
- Borders: 1px solid `border-gray-200` between panels (managed by grid gap or explicit borders)

### Placeholder Content

**Chat Panel Placeholder:**
- Text: "Chat interface - coming in Story 4.1"
- Icon or visual indicator (optional)
- Input area disabled or greyed out

**Plan/Code Panel Placeholder:**
- Tab selector for "Plan", "Code", "Template" (non-functional tabs)
- Active tab shows placeholder: "[Plan will be displayed here]" or similar
- All tabs are present but content is placeholder text

**Data Panel Placeholder:**
- Text: "Upload data to get started"
- Drag-and-drop zone (visual hint, non-functional for Story 2.2)
- Optional: "CSV files will appear here after upload"

**Report Panel Placeholder:**
- Text: "Run an analysis to see results"
- Optional: "Charts and trend analysis will display here"

### State Management (Story 2.2 Scope)

**Local State in AppLayout:**
- `activeTab: "plan" | "code" | "template"` — track which tab is active in Plan/Code panel
- Updated via callback when user clicks tab buttons

**Not in scope for Story 2.2:**
- Session state (added in Story 2.3)
- Chat history (added in Story 4.1)
- Actual data or report content (added in Stories 3.x, 8.1, etc.)
- API calls (added in Story 2.3)

### Responsive Design Notes

**Minimum Width:** 1280px (no mobile optimization required for MVP)
- On 1280px: All panels fully visible, minimal scrolling within panels
- On < 1280px: Acceptable to stack panels vertically (no optimization required)

**Panel Scrolling:**
- Each panel should have `overflow-y: auto` to allow internal scrolling
- No horizontal scroll (layout must fit within viewport width)
- Parent grid should not overflow

**Borders & Spacing:**
- Use Tailwind `border` utilities: `border-gray-200`, `border-r`, `border-b` to define panel boundaries
- No margin between panels; gaps managed by CSS Grid `gap` property or explicit borders

### Styling & Color Scheme

**Color Palette (from Tailwind):**
- Panel backgrounds: white (`#ffffff`)
- Panel headers: light gray (`bg-gray-50`)
- Borders: medium gray (`border-gray-200`)
- Text: dark gray (`text-gray-900`)
- Accent (optional for tab selection): blue (`bg-blue-100` or `border-blue-500`)

**Font Sizes:**
- Panel headers: 14px (font-sm)
- Body text: 14px (font-base)
- No fancy typography; keep it minimal

**No External Styling:**
- Use only Tailwind CSS utilities
- No CSS Modules or styled-components
- No custom CSS files (except global `src/app/globals.css`)

### Reference to Architecture

- [Source: Architecture.md - Frontend Architecture (Next.js/React)]
  - Section: "Four-panel layout: Chat (top-left, fixed input + scrollable history), Plan/Code/Template tabs (top-right), CSV uploader + editable data table (bottom-left), Report panel (bottom-right)"
  - Constraint: "Desktop-first, 1280px minimum width; no mobile breakpoints required for MVP"
  - State pattern: "React state management for UI-layer data: `sessionId`, `uploadedFiles`, `chatHistory`, `activeTab`, ..."

- [Source: epics.md - Story 2.2 Requirements]
  - Four-panel layout specification with explicit percentages
  - Placeholder content requirements
  - Component file paths and structure

---

## Tasks / Subtasks

### Task Group 1: Layout Foundation & Grid Setup

- [x] Create AppLayout component with CSS Grid
  - [x] Create `src/components/AppLayout.tsx`
  - [x] Define 2x2 CSS Grid layout (grid-template-columns, grid-template-rows)
  - [x] Set full viewport height (`height: 100vh`)
  - [x] Apply border styling between panels using `border` utilities or grid gap
  - [x] Test layout responsive behavior at 1280px and below

- [x] Implement grid template with correct panel proportions
  - [x] Top row: each column gets equal width (1fr, 1fr)
  - [x] Bottom row: left column 50%, right column 50%
  - [x] Verify no horizontal scrolling at 1280px+
  - [x] Verify visual balance and spacing

### Task Group 2: Root Layout Integration

- [x] Update root page component to use AppLayout
  - [x] Edit `src/app/page.tsx`
  - [x] Replace placeholder content with `<AppLayout />`
  - [x] Remove or clean up old placeholder text and styling
  - [x] Test: `npm run dev` and verify AppLayout renders

### Task Group 3: Panel Component Stubs

- [x] Create ChatPanel stub component
  - [x] Create `src/components/ChatPanel.tsx`
  - [x] Export default React component
  - [x] Render panel header: "Chat"
  - [x] Render placeholder content: "Chat interface - coming in Story 4.1"
  - [x] Apply white background and internal padding

- [x] Create PlanCodePanel stub with tabs
  - [x] Create `src/components/PlanCodePanel.tsx`
  - [x] Render header: "Plan / Code / Template"
  - [x] Create three tab buttons: "Plan", "Code", "Template"
  - [x] Implement tab toggle state (useState)
  - [x] Render placeholder content based on active tab
  - [x] Style inactive tabs as unselected, active tab as selected (use Tailwind for styling)

- [x] Create DataPanel stub component
  - [x] Create `src/components/DataPanel.tsx`
  - [x] Render header: "Data"
  - [x] Render placeholder: "Upload data to get started"
  - [x] Optional: Add visual drag-and-drop zone (visual only, non-functional)

- [x] Create ReportPanel stub component
  - [x] Create `src/components/ReportPanel.tsx`
  - [x] Render header: "Report"
  - [x] Render placeholder: "Run an analysis to see results"
  - [x] Optional: Add icon or visual indicator

### Task Group 4: Styling & Polish

- [x] Apply Tailwind CSS styling to panels
  - [x] Panel headers: `bg-gray-50`, `border-b border-gray-200`, `p-3`
  - [x] Panel bodies: `bg-white`, `p-4`, `overflow-y-auto`
  - [x] Borders between panels: `border-gray-200` applied correctly
  - [x] Font sizes and colors: use Tailwind defaults (no custom overrides)

- [x] Test visual appearance
  - [x] All panels visible and balanced at 1280px+
  - [x] No horizontal scrolling
  - [x] Clear visual separation between panels
  - [x] Headers and placeholder text readable
  - [x] Borders are subtle but visible

### Task Group 5: Responsive & Accessibility

- [x] Test responsive behavior
  - [x] At 1280px: all panels fully visible
  - [x] At 1024px: acceptable stacking or overflow (no hard requirement)
  - [x] Scrollbars appear only within panels, not page-wide

- [x] Accessibility checks (optional for Story 2.2)
  - [x] Tab buttons are keyboard-accessible (tab key navigation)
  - [x] Panel headers use semantic HTML (h2 or h3 tags)
  - [x] No color-only differentiation for tab selection (use text + background)

### Task Group 6: Verification & Documentation

- [x] Verify component file structure
  - [x] All components created in `src/components/` directory
  - [x] All components export default React.FC or function
  - [x] TypeScript strict mode passes (no `any` types without justification)

- [x] Test dev server and build
  - [x] Run `npm run dev` and manually verify layout at localhost:3000
  - [x] Run `npm run build` and verify no TypeScript or build errors
  - [x] Verify HMR works (edit component, browser auto-refreshes)

- [x] Acceptance criteria validation
  - [x] AC1: Four panels visible at 1280px+, no horizontal scroll
  - [x] AC2: Panels visually balanced with borders/spacing
  - [x] AC3: Each panel has header with purpose label
  - [x] AC4: AppLayout.tsx uses grid layout (verified in code)
  - [x] AC5: Placeholder text displays correctly ("Upload data..." and "Run an analysis...")

---

## Dev Notes

### Key Implementation Points

1. **CSS Grid is simpler than Flexbox for this layout.** Use Tailwind's `grid` utilities:
   ```jsx
   <div className="grid grid-cols-2 grid-rows-2 h-screen gap-0 border border-gray-200">
     {/* panels */}
   </div>
   ```

2. **Tab switching uses local React state.** No API calls needed for Tab switching in Story 2.2:
   ```jsx
   const [activeTab, setActiveTab] = useState<"plan" | "code" | "template">("plan");
   ```

3. **Panel overflow:** Each panel should have `overflow-y-auto` so internal content scrolls, not the page:
   ```jsx
   <div className="overflow-y-auto p-4">
   ```

4. **Borders between panels:** Use `border` and `border-r` / `border-b` utilities, OR let CSS Grid spacing manage it. Explicit borders are clearer:
   ```jsx
   <div className="border-r border-b border-gray-200">
   ```

5. **Placeholder content should be visually distinct.** Use `text-gray-500` or `italic` to show it's not real content.

6. **Don't over-engineer.** Story 2.2 is layout-only. Actual panel content (chat input, data table, etc.) comes in later stories. Keep panel components as simple stubs.

### Common Mistakes to Avoid

1. **Using Flexbox instead of Grid for 2x2 layout.** Grid is cleaner. Flexbox requires nested containers.

2. **Adding height: 100% without height: 100vh on parent.** The root element needs explicit height to fill the screen.

3. **Horizontal scrolling due to wide content.** Always ensure panels have `overflow-y-auto` and don't add extra width to their children.

4. **Forgetting gap: 0.** CSS Grid's default gap can add unwanted spacing. Set `gap-0` explicitly.

5. **Styling panels without borders.** Without borders, panels visually blend together. Use `border-gray-200` to separate them clearly.

6. **Adding padding to panels that shouldn't have it.** Panel headers should have `p-3` (compact), panel bodies should have `p-4` (readable).

### Architecture Compliance

**From Architecture Doc:**
- "Four-panel layout: Chat (top-left, fixed input + scrollable history), Plan/Code/Template tabs (top-right), CSV uploader + editable data table (bottom-left), Report panel (bottom-right)"
- "Desktop-first, 1280px minimum width; no mobile breakpoints required for MVP"
- "React state management for UI-layer data: `sessionId`, `uploadedFiles`, `chatHistory`, `activeTab`, `pipelineRunning`, `planApproved`, `currentPlan`, `currentCode`, `reportCharts`, `reportText`, `savedTemplates`, `errorMessage`, `largeDataMessage`"

**This story addresses:**
- Layout structure and proportions
- `activeTab` state management
- Panel component organization

**Later stories will address:**
- Session state (`sessionId`, `uploadedFiles`, `chatHistory`, etc.) in Story 2.3
- Chat input and history in Story 4.1
- Data table in Story 3.2
- Report display in Story 8.1

### Testing Standards Summary

**Not required for Story 2.2:**
- Unit tests for layout (CSS Grid rendering is DOM-verified manually)
- Accessibility compliance (WCAG testing deferred to later stories)

**Manual verification is sufficient:**
- Visual inspection at 1280px+
- Responsive behavior at smaller widths
- No console errors in dev server

**Build verification:**
- `npm run build` completes without errors
- TypeScript `npx tsc --noEmit` passes
- ESLint `npm run lint` has no errors

### Project Structure Alignment

**Frontend Root:**
- `./src/components/AppLayout.tsx` — main layout container
- `./src/components/ChatPanel.tsx` — chat panel stub
- `./src/components/PlanCodePanel.tsx` — plan/code/template tabs stub
- `./src/components/DataPanel.tsx` — data table panel stub
- `./src/components/ReportPanel.tsx` — report panel stub
- `./src/app/page.tsx` — updated to render AppLayout instead of placeholder

**No conflicts expected:**
- Backend and data/config directories are unchanged
- Next.js App Router structure already in place from Story 2.1
- Tailwind CSS already configured

**File additions:**
- 4 new panel component files
- 1 updated root page file

---

## Developer Context & Implementation Strategy

### High-Level Implementation Approach

**Phase 1: Create AppLayout Component (Grid Foundation)**
1. Create `src/components/AppLayout.tsx` with CSS Grid layout
2. Define 2x2 grid with correct proportions (25%/25% top, 50%/50% bottom)
3. Add border styling and spacing
4. Verify layout visually at 1280px+

**Phase 2: Create Panel Stub Components**
1. Create `ChatPanel.tsx` with header and placeholder
2. Create `PlanCodePanel.tsx` with tabs and state management
3. Create `DataPanel.tsx` with placeholder
4. Create `ReportPanel.tsx` with placeholder
5. Import all panels into AppLayout

**Phase 3: Integrate into Root Page**
1. Update `src/app/page.tsx` to render `<AppLayout />`
2. Test: `npm run dev` and verify layout displays correctly

**Phase 4: Polish & Verification**
1. Apply Tailwind styling to panel headers and borders
2. Test responsive behavior at various widths
3. Verify build process: `npm run build`
4. Validate TypeScript compilation: `npx tsc --noEmit`

### Previous Story Intelligence (Story 2.1 - Initialize Next.js Frontend)

**Key Learnings from Story 2.1:**
- Next.js 14 + React 18 + TypeScript strict mode now in place
- Tailwind CSS properly configured with proper content paths
- Path aliases (@/*) enable clean imports
- Global styles in `src/app/globals.css` provide Tailwind directives
- Dev server runs on localhost:3000 with HMR enabled
- Build process completed successfully with no TypeScript errors

**Project State After Story 2.1:**
- Root layout.tsx exists (wraps all pages)
- Root page.tsx exists (currently placeholder content)
- `src/components/` directory created but empty (ready for Story 2.2 panels)
- Tailwind is fully functional

**What Story 2.2 Builds On:**
- Use the existing `src/components/` directory for all panel components
- Use Tailwind CSS utilities (already configured) for grid and styling
- Keep TypeScript strict mode (no `any` types)
- Continue using path aliases for imports

### Git Intelligence (Recent Commits)

**From Story 2.1 implementation:**
- Created package.json with Next.js 14, React 18, TypeScript 5.3, Tailwind 3.4
- Created tsconfig.json with strict mode and path aliases
- Created next.config.js, tailwind.config.js, postcss.config.js
- Created src/app/layout.tsx, src/app/page.tsx, src/app/globals.css
- Created .eslintrc.json, .prettierrc, .nvmrc
- Updated .gitignore for Node.js and Next.js artifacts
- 18 files created, 1 file modified (gitignore)

**Patterns Established:**
- Use functional React components with TypeScript
- Use Tailwind CSS utilities (no CSS files needed for components)
- Use React hooks for state management
- Keep components simple and focused

### Source References

- [Source: epics.md - Epic 2, Story 2.2 - Implement Four-Panel Layout Component](../planning-artifacts/epics.md#story-22-implement-four-panel-layout-component)
- [Source: epics.md - Additional Requirements - Frontend Architecture (Next.js/React)](../planning-artifacts/epics.md#additional-requirements)
- [Source: architecture.md - Data Architecture - Frontend State](../planning-artifacts/architecture.md#data-architecture)
- [Source: architecture.md - Architectural Decisions - Frontend Framework](../planning-artifacts/architecture.md#architectural-decisions-established-by-stack)
- [Source: Story 2.1 - Project Structure & Dependencies](2-1-initialize-nextjs-frontend.md)

---

## Dev Agent Record

### Implementation Notes

**Story 2.2 - IMPLEMENTATION COMPLETE (2026-03-26)**

**Summary:**
Successfully implemented four-panel layout component with CSS Grid, tab switching, and placeholder content. All 6 task groups completed with all acceptance criteria satisfied.

**Implementation Approach:**
- Created AppLayout.tsx with CSS Grid (2x2: grid-cols-2, equal columns, full viewport height)
- Implemented responsive panel borders using Tailwind `border-r` and `border-b` utilities
- Created 4 panel stub components (ChatPanel, PlanCodePanel, DataPanel, ReportPanel)
- Implemented tab switching state in PlanCodePanel with functional tab buttons
- Applied Tailwind styling: gray-50 headers, gray-200 borders, white panel bodies
- Updated src/app/page.tsx to render AppLayout instead of placeholder
- Fixed next.config.js warning by removing invalid 'ssr' key
- Verified TypeScript strict mode passes (npx tsc --noEmit)
- Verified npm run build completes without errors
- Verified layout renders correctly at localhost:3000 with all components visible

**Components Created:**
- src/components/AppLayout.tsx — 2x2 grid container with panel management
- src/components/ChatPanel.tsx — placeholder panel with "Chat interface - coming in Story 4.1"
- src/components/PlanCodePanel.tsx — tabbed panel (Plan/Code/Template) with working tab switching
- src/components/DataPanel.tsx — data input placeholder with "Upload data to get started"
- src/components/ReportPanel.tsx — report placeholder with "Run an analysis to see results"

**Files Modified:**
- src/app/page.tsx — replaced placeholder with AppLayout component
- next.config.js — removed invalid 'ssr' key

**Completion Checklist:**
- [x] AppLayout component created with CSS Grid layout (2x2 with correct proportions)
- [x] Layout renders correctly at 1280px+ with no horizontal scrolling
- [x] Four panels visible with visual separation (gray-200 borders)
- [x] Each panel has header with purpose label (Chat, Plan/Code/Template, Data, Report)
- [x] Panel stub components created (ChatPanel, PlanCodePanel, DataPanel, ReportPanel)
- [x] PlanCodePanel has functional tabs (Plan, Code, Template) with active state
- [x] Tab switching managed by React state (useState)
- [x] Placeholder content displays correctly in all panels
- [x] src/app/page.tsx updated to render AppLayout
- [x] npm run dev shows correct layout at localhost:3000
- [x] npm run build completes without errors
- [x] TypeScript strict mode passes (npx tsc --noEmit)
- [x] All 6 task groups completed with 20+ subtasks
- [x] All 5 acceptance criteria satisfied

**Ready for:** Code review (bmad-bmm-code-review)

### File List

**New Files Created:**
- `src/components/AppLayout.tsx` — Main 2x2 grid layout component (98 lines)
- `src/components/ChatPanel.tsx` — Chat panel stub with placeholder (28 lines)
- `src/components/PlanCodePanel.tsx` — Plan/Code/Template tabbed panel (72 lines)
- `src/components/DataPanel.tsx` — Data panel stub with upload placeholder (34 lines)
- `src/components/ReportPanel.tsx` — Report panel stub with analysis placeholder (28 lines)

**Modified Files:**
- `src/app/page.tsx` — Replaced placeholder content with AppLayout component
- `next.config.js` — Removed invalid 'ssr' key to fix build warning

### Change Log

**2026-03-26 - Four-Panel Layout Implementation**
- Created AppLayout component with CSS Grid (2x2 layout, 25%-25%-50%-50% proportions)
- Implemented 4 panel components: Chat, Plan/Code/Template tabs, Data, Report
- Added tab switching state management (Plan/Code/Template tabs)
- Applied Tailwind CSS styling: gray-50 headers, gray-200 borders, white backgrounds
- Updated root page to render layout instead of placeholder
- Fixed next.config.js configuration warning
- All acceptance criteria verified; TypeScript and build validation passed

---

## Completion Criteria

✅ When this story is DONE:
- AppLayout component created with CSS Grid layout
- Layout renders correctly at 1280px+ with no horizontal scrolling
- Four panels visible with visual separation (borders/spacing)
- Each panel has header with purpose label
- Panel stub components created (ChatPanel, PlanCodePanel, DataPanel, ReportPanel)
- PlanCodePanel has functional tabs (Plan, Code, Template) with tab-switch state
- Placeholder content displays: "Upload data to get started" (Data panel), "Run an analysis to see results" (Report panel)
- root page.tsx updated to render AppLayout instead of placeholder
- npm run dev shows correct layout at localhost:3000
- npm run build completes without errors
- TypeScript strict mode passes (npx tsc --noEmit)
- Ready for Story 2.3 (API Client Hook & Session Management)

---

**Previous Story:** Story 2.1 - Initialize Next.js Frontend ✅ COMPLETE

**Next Story:** Story 2.3 - Create API Client Hook & Session Management

**Critical Path:** Four-panel layout unblocks all subsequent frontend stories (chat, data table, report display). Essential UI foundation.
