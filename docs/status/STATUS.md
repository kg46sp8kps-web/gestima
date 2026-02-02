# GESTIMA - Current Status

**Last Updated:** 2026-02-02
**Version:** 1.15.0
**Status:** 🟡 PLANNED - Visual Editor Design Spec Complete

---

## 🎨 Visual Editor System (Phase 1) 🟡 PLANNED (Design Spec)

**⚠️ NOTE: These components are NOT YET IMPLEMENTED. This section describes the PLANNED architecture.**

**See:** [docs/design/VISUAL-EDITOR-SPEC.md](../design/VISUAL-EDITOR-SPEC.md) for complete design specification.

**Planned Features:**

### ✅ Completed Features

#### Core Visual Editor Components
- ✅ **VisualEditorMode.vue** - Master coordinator (3-panel layout)
  - Widget Tree (left) | Canvas (center) | Property Panel (right)
  - Toggle from CustomizableModule edit mode
  - Real-time preview with auto-apply
- ✅ **VisualEditorToolbar.vue** - Top toolbar controls
  - Toggle rulers, grid overlay, snap-to-grid
  - Export/Import config buttons
  - Close editor button
- ✅ **EditorCanvas.vue** - Enhanced canvas with visual aids
  - Rulers (horizontal/vertical with pixel measurements)
  - Grid overlay (10px snap guides)
  - Selection overlay (blue outline + resize handles)
  - Wraps GridLayoutArea with visual editing layer
- ✅ **WidgetTreePanel.vue** - Left sidebar
  - Hierarchical widget list
  - Click-to-select interaction
  - Widget size display (w×h)
  - Add widget button (placeholder)

#### Property Editing System
- ✅ **PropertyPanel.vue** - Right sidebar with collapsible sections
  - Spacing section (padding, margin, gap)
  - Sizing section (min/max width/height)
  - Border section (width, color, radius)
  - Background section (color, opacity)
  - Typography section (fontSize, fontWeight, lineHeight)
  - Grid Gap slider (8-32px, global setting)
  - Window Defaults editor (width, height, min values, title)
- ✅ **PropertyInput.vue** - Number input with unit support
- ✅ **PropertySpacingInput.vue** - 4-sided box model (top/right/bottom/left)
- ✅ **PropertySelect.vue** - Dropdown selector
- ✅ **PropertyColorPicker.vue** - Color picker with hex input
- ✅ **usePropertyPanel.ts** - Property editing composable
  - Auto-apply on change (500ms debounce)
  - Deep merge with widget definitions
  - Default style initialization
  - No reset when switching widgets

#### State Management & Persistence
- ✅ **useVisualEditor.ts** - Main state management composable
  - Visual aids state (rulers, grid, snap)
  - Widget selection tracking
  - Layout management (updates from GridStack)
  - widgetProperties store (per-widget custom styles)
  - getCurrentConfig() - Exports full config with properties
- ✅ **localStorage Integration** - CustomizableModule.vue
  - loadWidgetProperties() on mount
  - handleVisualEditorUpdate() saves properties
  - Survives page refresh
  - Separate keys per module (e.g., `part-detail-widget-properties`)
- ✅ **mergedConfig Pattern** - Pass widgetProperties to Visual Editor
  - Computed property combines config + stored properties
  - Deep merge in selectedWidgetDefinition

#### Export/Import System
- ✅ **ExportConfigModal.vue** - Generate TypeScript config
  - Full ModuleLayoutConfig code generation
  - Copy-to-clipboard button
  - Shows formatted TypeScript code
  - Includes widgetProperties in export
- ✅ **ImportConfigModal.vue** - Parse and apply TS config
  - JSON paste input
  - Validation before import
  - Updates layouts + properties atomically

#### Visual Aids
- ✅ **Rulers.vue** - Horizontal/vertical measurements
  - Pixel-based scale (0-1920, 0-1080)
  - Fixed position at top/left edges
- ✅ **GridOverlay.vue** - Snap guides
  - 10px grid pattern
  - Toggleable visibility
  - Absolute positioning
- ✅ **SelectionOverlay.vue** - Widget selection feedback
  - Blue outline (2px solid)
  - 8-point resize handles (visual only)
  - Shows min/max constraints

### 🔧 Technical Implementation Highlights

#### CSS Specificity Bug Fix
- **Problem:** Only margin was applying, other properties ignored
- **Root Cause:** Hardcoded `.widget-content { padding: var(--space-3) }` overrode inline styles
- **Solution:** Split computedStyle into two:
  - `computedWrapperStyle` (border, margin, background) → applied to `.widget-wrapper`
  - `computedContentStyle` (padding, gap, typography) → applied to `.widget-content`
  - Removed hardcoded CSS, added default in computed property

#### Deep Merge Pattern
- **Problem:** Properties reset when switching widgets
- **Solution:** selectedWidgetDefinition deep merges:
  ```typescript
  const selectedWidgetDefinition = computed(() => {
    const widgetDef = props.config.widgets.find(w => w.id === selectedWidgetId)
    const customProps = widgetProperties.value[selectedWidgetId]

    if (customProps) {
      return {
        ...widgetDef,
        ...customProps,
        style: {
          ...(widgetDef as any).style,
          ...customProps.style,
          padding: { ...widgetDef.style?.padding, ...customProps.style?.padding },
          // ... nested merge for margin, border, background, typography
        }
      }
    }

    return widgetDef
  })
  ```

#### Type System Extensions
- **types/widget.ts**
  - Added `widgetProperties?: Record<string, any>` to ModuleLayoutConfig
  - Added `minW?, minH?, maxW?, maxH?` to WidgetLayout (GridStack constraints)
- **types/visual-editor.ts** (NEW)
  - WidgetProperties, WidgetStyle, SpacingValue
  - GlueType (not yet implemented)
  - VisualEditorState

### ⚠️ Partial Implementation

**GridStack Min/Max Constraints**
- Type definitions added (minW, minH, maxW, maxH)
- handleUpdateWidget updates layout array immutably
- **Missing:** watch in GridLayoutArea.vue to call grid.update()
- **Current Behavior:** Constraints in data but not enforced until manual drag/resize

### ❌ Not Implemented (Phase 2)

1. **Backend Persistence** - No database, API endpoints, or user-specific layouts
2. **Glue System** - Constraint-based positioning (stick to edges, fill space)
3. **Design Tokens Override** - tokens field exists but no UI editor
4. **Advanced Features** - Multi-select, keyboard shortcuts, undo/redo
5. **Testing** - No unit tests, integration tests, or E2E tests

### 📊 Statistics

- **New Components:** 12 (VisualEditorMode, PropertyPanel, EditorCanvas, etc.)
- **New Composables:** 2 (useVisualEditor, usePropertyPanel)
- **Lines of Code:** ~2,500 LOC
- **Files Changed:** 20+ (components, composables, types)
- **Bundle Impact:** TBD (not yet measured)

### 🔗 Related
- See: [ADR-031: Visual Editor System](docs/ADR/031-visual-editor-system.md)
- See: [ADR-030: Universal Responsive Module Template](docs/ADR/030-universal-responsive-module-template.md)

---

## 🎨 UI/UX Refinements (2026-02-01)

### Pricing Module Improvements ✅
- ✅ **Batch statistics removed** - Simplified header (removed count, min/max prices)
- ✅ **Frozen sets counter** - Added "Sady: X" indicator for frozen batch sets
- ✅ **Freeze button redesign** - Icon-only button with Snowflake icon (light blue)
- ✅ **Input focus persistence** - "Nová dávka" input stays focused after Enter
- ✅ **Recalculate button removed** - Auto-recalculate sufficient
- ✅ **Layout shift fixed** - Panel elements use `visibility: hidden` instead of `v-if`
- ✅ **Table header cleanup** - Changed "Cena práce" → "Práce"

### Material Module Improvements ✅
- ✅ **Tier price tooltips** - Shows "Cena z tieru: X Kč/kg" on material rows
- ✅ **Tooltip delay centralized** - Created `TOOLTIP_DELAY_MS` constant (750ms)
  - Location: `frontend/src/constants/ui.ts`
  - Single source of truth for entire system

### Batch Detail Modal Fixes ✅
- ✅ **Unit cost display** - Fixed modal to use `unit_cost` instead of missing `unit_price`
- ✅ **Backend consistency** - Added `unit_price` as computed field alias for `unit_cost`
- ✅ **Quantity display** - Added quantity field to modal

### Operations Module Improvements ✅
- ✅ **VueDraggable integration** - Professional drag & drop solution
  - Package: `vuedraggable@next` (Vue 3 compatible)
  - Clean UX: Only dragged operation visible + gap (no ghost duplicates)
  - 300ms smooth animation, vertical direction
  - Auto-renumbering: 10-20-30 sequence after drop
- ✅ **Coefficient fields** - Added manning & machine utilization
  - Backend: `manning_coefficient`, `machine_utilization_coefficient`
  - Frontend: Inline editable inputs with @focus select()
  - Time calculations: Tp, Tj (with Ke), To (with Ko)
- ✅ **Component refactoring** - Removed 120+ LOC custom drag handlers
  - Before: 420 LOC with custom HTML5 Drag & Drop
  - After: 373 LOC with VueDraggable (-11%)
  - BUILDING BLOCKS pattern maintained (<500 LOC)
- 📖 **Best practices documented** - See `docs/guides/VUEDRAGGABLE-GUIDE.md`

### Technical Improvements
- 📁 **New file:** `frontend/src/constants/ui.ts` - UI timing constants
- 🔧 **Backend:** `app/models/batch.py` - Added `unit_price` computed property
- 🎨 **CSS:** Layout shift prevention using `visibility: hidden` pattern
- 📖 **Docs:** Updated DESIGN-SYSTEM.md with tooltip timing constants

---

## 🤖 Latest: AI Quote Request Parsing ✅ COMPLETE (Day 40-41)

**Claude Sonnet 4.5 API - automatické vytváření nabídek z PDF! Backend + Frontend hotovo!**

### ✅ Complete Implementation

#### AI Parser Service
- ✅ **QuoteRequestParser** - Claude Sonnet 4.5 integration
  - Model: `claude-sonnet-4-5-20250929` (upgraded from 3.5)
  - **Direct PDF upload** - base64 encoding, no image conversion needed
  - PDF → structured JSON extraction in 2-5 seconds
  - Semantic understanding (buyer vs supplier, drawing vs SKU)
  - Prompt engineering for Czech B2B quote forms
  - Confidence scoring (0.0-1.0) for all extracted fields
  - Timeout handling (30s), error recovery, JSON validation
  - Magic bytes validation (PDF only, 10 MB max)
  - Cost: ~$0.08 per parse (3× cheaper than OpenAI)

#### Pydantic Schemas (quote_request.py)
- ✅ **CustomerExtraction** - company, contact, email, phone, IČO + confidence
- ✅ **ItemExtraction** - article_number, name, quantity, notes + confidence
- ✅ **QuoteRequestExtraction** - customer + items[] + customer_request_number + valid_until
- ✅ **CustomerMatch** - partner matching results (partner_id, confidence)
- ✅ **BatchMatch** - pricing match (status: exact/lower/missing)
- ✅ **PartMatch** - part + batch combined matching
- ✅ **QuoteRequestReview** - final UI review data with customer_request_number
- ✅ **QuoteFromRequestCreate** - quote creation input (all fields optional)

#### Extended Quote Service
- ✅ **find_best_batch()** - Smart batch matching algorithm
  - Strategy: Exact → Nearest Lower → Missing
  - NEVER uses higher batch (wrong pricing!)
  - Returns status + warnings for UI
- ✅ **match_part_by_article_number()** - Part lookup with validation
- ✅ **match_item()** - Combined part + batch matching
- ✅ **Multi-strategy customer matching** - IČO → email → name cascade
  - Handles edge cases (Gelso AG vs Gelso DE)
  - Confidence scores: 100% → 95% → 80%

#### API Endpoints
- ✅ **POST /api/quotes/parse-request** - Upload PDF, extract data
  - File size validation (10 MB max, HTTP 413)
  - Rate limiting (10 requests/hour per user)
  - Returns QuoteRequestReview for UI verification
- ✅ **POST /api/quotes/from-request** - Create Quote from verified data
  - Creates Partner if new (company_name, IČO, email, phone)
  - Creates Parts if new (article_number, name, revision=A, status=draft)
  - Creates Quote (DRAFT status) + QuoteItems with pricing
  - Atomic transaction (all or nothing)

#### Security & Rate Limiting
- ✅ **Rate Limiter** - slowapi integration
  - User-based tracking (user_id → "user:123")
  - IP fallback for anonymous requests
  - Configurable: AI_RATE_LIMIT setting (default: 10/hour)
- ✅ **File Validation** - PDF magic bytes check, 10 MB max
- ✅ **Timeout Protection** - 30s max Claude API call
- ✅ **API Key Security** - .env only, never committed
- ✅ **Path Traversal Prevention** - UUID filenames
- ✅ **Temp File Cleanup** - Even on error

#### Database Changes
- ✅ **article_number UNIQUE constraint** - Added to Part model
  - Prevents duplicate parts in AI workflow
  - Enables reliable article_number-based matching
  - Auto-cleanup of duplicates in migration
  - Migration: `i1j2k3l4m5n6_add_article_number_unique_constraint.py`
- ✅ **customer_request_number field** - Added to Quote model
  - Dedicated field for customer RFQ numbers (P20971, RFQ-2026-001, etc.)
  - Indexed for search/filter performance
  - Extracted separately from notes by AI
  - Migration: `j2k3l4m5n6o7_add_customer_request_number_to_quote.py`
- ✅ **drawing_number field** - Added to Part model (optional)
  - Migration: `g5h6i7j8k9l0_add_drawing_number_to_part.py`

#### Configuration
- ✅ **ANTHROPIC_API_KEY** - Added to config.py and .env
- ✅ **AI_RATE_LIMIT** - Added to config.py (default: "10/hour")
- ✅ **requirements.txt** - Switched from openai to anthropic>=0.40.0

#### Documentation
- ✅ **ADR-028** - Complete architecture documentation (updated to v1.14.0)
  - Claude Sonnet 4.5 upgrade details
  - Direct PDF upload implementation
  - customer_request_number field documentation
  - Optional fields policy
  - Frontend implementation complete
  - Batch matching strategy rationale
  - Customer matching cascade logic
  - Security controls, cost estimates
- ✅ **CHANGELOG.md** - Added v1.14.0 entry
- ✅ **STATUS.md** - Updated (this file)

### ✅ Frontend Implementation COMPLETE

#### Quote Request UI
- ✅ **QuoteFromRequestPanel.vue** - Full PDF parsing workflow
  - PDF upload with drag & drop support
  - AI extraction progress indicator
  - Review/edit extracted data form
  - Customer match display with confidence indicator
  - Items table with part matching status
  - Batch status indicators (exact/lower/missing with colors and warnings)
  - customer_request_number input field (pre-filled from AI extraction)
  - Editable form before quote creation
  - Confirm button → POST /from-request → navigate to created quote

#### API Integration
- ✅ **api/quotes.ts** - parseQuoteRequestPDF() and createQuoteFromRequest()
- ✅ **stores/quotes.ts** - Full AI workflow actions implemented
- ✅ **router/index.ts** - Quote routes with AI parsing integrated
- ✅ **types/quote.ts** - Complete TypeScript types including customer_request_number

### 📊 Stats
- **1200+ LOC** created (Backend + Frontend)
- **2 new API endpoints** (/parse-request, /from-request)
- **8 new Pydantic schemas** (quote_request.py)
- **3 database migrations** (article_number UNIQUE, customer_request_number, drawing_number)
- **1 new service** (QuoteRequestParser with Claude Sonnet 4.5)
- **1 new frontend component** (QuoteFromRequestPanel.vue)
- **Time saved**: 5-10 min → 1-2 min (80% faster quote entry)
- **AI cost**: ~$0.08 per quote (~$20/month at full 10/hour usage)
- **Processing speed**: 2-5 seconds (direct PDF upload, no image conversion)

### ✅ Key Improvements (v1.14.0)
1. **Claude Sonnet 4.5** - Better accuracy for Czech B2B documents
2. **Direct PDF upload** - 3-5x faster than image conversion
3. **customer_request_number** - Dedicated field for tracking RFQ numbers
4. **Optional fields** - No required fields (user preference)
5. **Semantic extraction** - Correctly identifies buyer vs supplier, drawing vs SKU

### 🔗 Related
- See: [ADR-028: AI Quote Request Parsing](docs/ADR/028-ai-quote-request-parsing.md)
- See: [CHANGELOG.md v1.14.0](CHANGELOG.md)

---

## 📋 Previous: Part Copy Feature ✅ COMPLETED (Day 39)

**Kopírování dílů s modálním workflow + přečíslování operací!**

### ✅ Completed

#### Copy Part Functionality
- ✅ **Copy Button** - Added to PartDetailPanel header (next to Edit)
  - Subtle icon button (Copy icon, 14px)
  - Opens modal for copying part
  - Integrated with existing design system

- ✅ **CopyPartModal Component** (NEW)
  - Article number input (required, autofocus)
  - Checkboxes: Copy operations (✓), Copy material (✓), Copy batches
  - Icon buttons (Check/X) for confirm/cancel
  - Direct part creation from modal (no intermediate form)
  - Error handling with inline error messages

#### Backend Copy Logic
- ✅ **copy_part_relations Function** - app/routers/parts_router.py
  - Query parameters: copy_from, copy_operations, copy_material, copy_batches
  - Copies MaterialInput records (not direct material_item_id)
  - **Operation Renumbering** - seq 10, 20, 30... (clean sequence)
  - Batch number generation with NumberGenerator
  - Atomic transaction (all or nothing)
  - Audit trail for all copied records

#### UX Improvements
- ✅ **Header Spacing Optimization**
  - Reduced gap: var(--space-2) → var(--space-1)
  - Removed min-height: 68px from form-field
  - Compact, clean appearance

- ✅ **Consistent Icon Buttons**
  - PartDetailPanel: 24x24px subtle buttons
  - CopyPartModal: 36x36px action buttons
  - PartCreateForm: 36x36px action buttons
  - Unified hover states and transitions

#### Technical Implementation
- ✅ **API Integration**
  - Updated parts.ts createPart with copyFrom parameter
  - Success message: "Díl zkopírován" vs "Díl vytvořen"
  - Refresh list after successful copy

- ✅ **Operation Sequencing**
  - Source operations sorted by seq
  - Target operations renumbered to 10, 20, 30...
  - Clean start for every copied part
  - Maintains proper drag & drop spacing

---

## 🎨 Previous: Refined & Subtle Design System v1.6 ✅ COMPLETED (Day 39)

**Jemný červený akcent + ComponentShowcase + shadcn/ui pattern!**

### ✅ Completed

#### Design System Refinement
- ✅ **Border Width Change** - 2px → 1px (subtle, less prominent)
  - Updated: design-system.css, Button.vue, Input.vue, Select.vue
  - Refined style - clean separation without heaviness
- ✅ **Border Color Adjustment** - #404040 → #2a2a2a (lower contrast)
  - More subtle, less harsh on eyes
  - Professional, refined appearance
- ✅ **Logo Red Integration** - #E84545 as primary hover
  - Primary: #991b1b (dark muted red)
  - Hover: #E84545 (logo red - vibrant)
  - Explicit accent: --palette-accent-red
- ✅ **Component Showcase** - /showcase route added
  - Comprehensive UI catalog (colors, typography, buttons, inputs, forms)
  - Live preview of all component states
  - Border system demonstration
  - Data display examples (badges, tables)

#### shadcn/ui Pattern
- ✅ **Already Installed** - radix-vue, tailwind-merge, CVA, clsx
  - Headless components ready (Radix Vue)
  - Styling utilities in place
  - No additional packages needed
- ✅ **Verified Stack** - package.json analysis
  - radix-vue: ^1.9.17
  - lucide-vue-next: ^0.563.0
  - tailwind-merge: ^3.4.0
  - class-variance-authority: ^0.7.1

#### Documentation Updates
- ✅ **DESIGN-SYSTEM.md v1.6** - Updated for Refined & Subtle design
  - Border system documentation
  - Logo red hover tokens
  - Component Showcase reference
  - Latest updates section
- ✅ **STATUS.md** - This file updated

---

## 🎨 Previous: Complete Emoji Removal + Lucide Icons ✅ COMPLETED (Day 38)

**VŠECHNY emoji nahrazeny profesionálními Lucide ikonami!**

### ✅ Completed

#### UI Redesign - NO EMOJI Policy
- ✅ **Systematic Emoji Removal** - 20+ souborů opraveno
  - PartnerListPanel, QuoteListPanel, PartListPanel
  - PartDetailPanel, MaterialDetailPanel, PricingDetailPanel
  - OperationsDetailPanel, QuoteDetailPanel, QuoteHeader
  - PartDrawingWindow, PartCreateForm
  - All view files (MasterDataView, QuoteDetailView, PartnersView, etc.)
  - Stores (operations.ts, materials.ts)
  - Types (operation.ts - OPERATION_TYPE_MAP)
- ✅ **Lucide Vue Next Integration** - Profesionální icon library
  - 30+ ikon importováno (Package, Settings, DollarSign, Trash2, etc.)
  - Konzistentní sizing: 14px (buttons), 48px (empty states)
  - Flexbox alignment pro všechny ikony
- ✅ **CSS Updates** - Proper icon display
  - Display: flex, align-items: center
  - Gap spacing pro icon + text
  - Color inheritance (currentColor)
- ✅ **Documentation Update** - DESIGN-SYSTEM.md
  - Nová sekce: Icons
  - Standardní velikosti a stroke widths
  - Často používané ikony tabulka
  - NO EMOJI policy dokumentována
- ✅ **Verification** - Final grep scan
  - 0 emoji v produkčním kódu
  - Pouze test files a geometrické symboly (functional labels)

#### Icon Mapping Completed
- ➕ → Plus | 📦 → Package | 🏢 → Building2
- 👥 → Users | 🏭 → Factory | 📋 → ClipboardList
- 📝 → FileEdit | 📤 → Send | ✅ → CheckCircle
- ❌ → XCircle | 🗑️ → Trash2 | ✏️ → Edit
- 🔒 → Lock | ⚙️ → Settings | 💰 → DollarSign
- 🔧 → Wrench | 📄 → FileText | ⚠️ → AlertTriangle

---

## 📋 Previous: Design System Token Editor + L-036/L-037 ✅ COMPLETED (Day 37)

**100+ hardcoded CSS values eliminated + Full token customization in Settings!**

### ✅ Completed

#### Design System Token Editor
- ✅ **Full Token Editor in Settings** - 30 editable design tokens
  - Typography: `--text-2xs` to `--text-8xl` (13 tokens)
  - Spacing: `--space-1` to `--space-10` (8 tokens)
  - Density: row-height, padding values (9 tokens)
- ✅ **Live Preview** - Changes apply instantly without page reload
  - `watch()` on tokens → immediate CSS variable updates
  - Real-time feedback across entire UI
- ✅ **Persistence** - localStorage: `gestima_design_tokens`
  - Auto-load on app startup (App.vue)
  - Survives page refresh
- ✅ **Reset Functionality** - Per-category or all tokens
  - Reset typography, spacing, density independently
  - Reset all to defaults with one click

#### L-036: NO HARDCODED CSS VALUES (CRITICAL!)
- ✅ **Audit Complete** - Found 100+ hardcoded `font-size` values
  - AppHeader.vue (18 values)
  - FloatingWindow.vue (5 values)
  - WindowManager.vue (7 values)
  - forms.css (10 values)
  - operations.css (6 values)
  - components.css (3 values)
  - layout.css (2 values)
  - All views (35+ values)
  - UI components (5 values)
- ✅ **Conversion Complete** - All hardcoded values → design system tokens
- ✅ **Verification** - `grep -r "font-size:\s*[0-9]" frontend/src` → 0 matches
- ✅ **Prevention Rule** - Automated grep check before every PR

#### L-037: Mixing Directives with Event Handlers (CRITICAL!)
- ✅ **Incident Documented** - Select-on-focus race condition
  - Symptom: "Někdy to hodnotu přepíše a někdy přidávám k původní"
  - Root cause: `v-select-on-focus` + `@focus="selectOnFocus"` = conflict
  - Solution: ONE mechanism only (directive OR handler, NEVER both)
- ✅ **Prevention Rule** - Code review checklist item

#### DESIGN-SYSTEM.md Updates (v1.2 → v1.5)
- ✅ **New Typography Tokens** - Added `--text-4xl` to `--text-8xl`
  - `--text-4xl` (20px) - Section titles
  - `--text-5xl` (24px) - Page headers
  - `--text-6xl` (32px) - Hero text
  - `--text-7xl` (48px) - Empty state icons
  - `--text-8xl` (64px) - Large display icons
- ✅ **Text Color Clarification** - `--text-body` (color) vs `--text-base` (size)
  - Fixed confusion: `color: var(--text-body)`, `font-size: var(--text-base)`
  - Grep verified: 0 misuses
- ✅ **Legacy Aliases Section** - Backward compatibility documented
  - `--accent-blue` → `--palette-info`
  - `--error` → `--color-danger`
  - Rule: Use semantic tokens in NEW components!

### Technical Details
- **Files Changed:** 68 files
- **Lines Added:** 2,987
- **Lines Removed:** 1,259
- **Net Change:** +1,728 lines
- **CSS Tokens Fixed:** 100+
- **New Design Tokens:** 30 (editable)
- **Anti-Patterns Documented:** 2 (L-036, L-037)

### Impact
- ✅ **Fully Customizable UI** - Users can adjust every font size, spacing, density
- ✅ **Zero Hardcoded CSS** - All values use design system tokens
- ✅ **Better for 27" Displays** - Optimized default values with user control
- ✅ **Single Source of Truth** - design-system.css only
- ✅ **Easy Maintenance** - One token change affects entire app

**Audit Report:** [2026-01-31-design-system-token-editor.md](../audits/2026-01-31-design-system-token-editor.md)

---

## 📋 Previous: BatchSets Module + TypeError Fixes ✅ COMPLETED (Day 36)

**BatchSets (ADR-022) implemented with freeze workflow + critical TypeError fixes!**

### ✅ Completed

#### BatchSets Module (Freeze Workflow)
- ✅ **BatchSet Model** - Groups multiple batches for freezing
  - Timestamp-based names (e.g., "2026-01-31 14:35")
  - Atomic freeze operation (all batches in set)
  - Links to Part via `part_id` FK
- ✅ **PricingDetailPanel Refactor** - BatchSet dropdown selector
  - "Aktivní (rozpracováno)" for working batches
  - Frozen sets listed by timestamp name
  - Inline batch addition with Enter key
  - Cost bar: shows only base costs (mat+koop+setup+machining = 100%)
  - Table layout: ks | Materiál | Koop | BAR | Cena práce | Režie | Marže | Cena/ks | Akce
- ✅ **Focus Retention** - Input stays focused after Enter for rapid batch addition
  - Separated refs: `emptyInputRef` and `ribbonInputRef`
  - Double `nextTick()` to ensure DOM updates before focusing

#### Critical TypeError Fixes (Root Cause Analysis)
- ✅ **MaterialPriceCategory.material_group_id** - Was NULL in database
  - **Root cause:** Seed script didn't populate FK
  - **Fix 1:** Updated `scripts/seed_price_categories.py` with mapping
  - **Fix 2:** Created migration `scripts/fix_price_categories_material_group.py`
  - **Fix 3:** Fixed 13 existing categories in DB
- ✅ **Defensive Programming** in `price_calculator.py`
  - Added NULL checks for `material_group.density`
  - Added NULL checks for `price_per_kg`
  - Added NULL checks for operation times (`setup_time_min`, `operation_time_min`)
  - Added NULL checks for WorkCenter hourly rates
  - All checks log ERROR and return 0 instead of crashing

### Technical Details
- **Files Changed:** PricingDetailPanel.vue, price_calculator.py, batch_service.py, seed scripts
- **Database:** Fixed 13 MaterialPriceCategory records
- **Pattern:** Defensive programming with graceful degradation

### Impact
- ✅ **No More TypeErrors** - Batch calculation robust against NULL values
- ✅ **BatchSets Workflow** - Freeze pricing snapshots for audit trail
- ✅ **Better UX** - Inline batch addition with focus retention
- ✅ **Data Integrity** - All price categories now properly linked to material groups

---

## 📋 Previous: Live Batch Recalculation & Inline Editing ✅ COMPLETED (Day 35)

**Operations and Materials now trigger live batch price recalculation!**

### ✅ Completed

#### Live Batch Recalculation
- ✅ **Operations Store** - All mutations trigger silent batch recalc
  - `addOperation()`, `updateOperation()`, `deleteOperation()`, `changeMode()`
  - Uses `currentPartId` tracking in multi-context pattern
- ✅ **Materials Store** - All mutations trigger silent batch recalc
  - `createMaterialInput()`, `updateMaterialInput()`, `deleteMaterialInput()`
  - `linkMaterialToOperation()`, `unlinkMaterialFromOperation()`
- ✅ **Batches Store** - Extended `recalculateBatches(linkingGroup, partId?, silent?)`
  - Optional `partId` param for explicit context
  - `silent=true` suppresses toast (for auto-triggered recalcs)

#### Operations Inline Editing Pattern
- ✅ **OperationsDetailPanel.vue** - Complete rewrite
  - Inline editing: tp/tj times and work center dropdown directly on row
  - Debounced auto-save (500ms delay)
  - Dynamic dropdown width based on longest work center name
  - Expand button only for advanced settings (cutting mode, coop)
  - Select-all on focus for number inputs (`v-select-on-focus`)
  - Lock buttons for tp/tj times

#### Multi-Context Pattern Updates
- ✅ **Operations Store Tests** - Updated for multi-context API
  - All 24 tests passing
  - Mocked `useBatchesStore` to avoid side effects
  - Fixed WorkCenter type references (`CNC_LATHE`, `CNC_MILL_3AX`)

### Technical Details
- **Files Changed:** 6 stores/components + 1 test file
- **Tests:** 24 operations store tests passing
- **Pattern:** Based on Alpine.js legacy (`archive/legacy-alpinejs-v1.6.1/templates/parts/edit.html`)

### Impact
- ✅ **Real-time Pricing** - Batch prices update instantly on operation/material changes
- ✅ **Faster Workflow** - Inline editing reduces clicks (no expand needed for common fields)
- ✅ **Consistent UX** - Matches original Alpine.js pattern (user familiarity)
- ✅ **Silent Updates** - No toast spam for auto-triggered recalculations

---

## 📋 Quotes Module - Frozen Batch Integration ✅ COMPLETED (Day 34)

**Quotes now use ONLY frozen batch prices - no manual editing!**

### ✅ Completed
- ✅ **Frozen Batch Requirement** - QuoteItem creation blocks if no frozen batch (HTTP 400)
  - Error: "Část nemá zmrazenou kalkulaci. Nejdříve zmrazte batch pro přidání do nabídky."
  - Auto-loads `unit_price` from latest frozen BatchSet
- ✅ **Read-Only Pricing** - Removed `unit_price` from QuoteItemUpdate
  - Backend: Removed field from Pydantic schema
  - Frontend: Removed price input field, added info notice
  - Tests: Updated to match new schema
- ✅ **Delete Protection** - SENT/APPROVED quotes cannot be deleted
  - HTTP 403: "Nelze smazat nabídku ve stavu 'sent/approved'. Obsahuje právně závazný snapshot."
  - Only DRAFT and REJECTED quotes can be soft-deleted
  - Snapshots preserved forever (legal compliance)
- ✅ **Complete Snapshot** - Quote snapshot contains partner + items + totals
  - Created on DRAFT → SENT transition
  - Immutable after SENT (edit lock)
  - Self-contained legal document
- ✅ **Documentation** - ADR VIS-002 created
  - Frozen batch policy
  - Workflow states & edit lock
  - Snapshot structure
  - Delete protection matrix

### Technical Details
- **Files Changed:** 7 backend + 4 frontend + 1 test file
- **Tests Added:** 4 new tests (sent/approved/draft/rejected deletion)
- **ADR Created:** [VIS-002: Quotes Workflow & Snapshot Protection](../ADR/VIS-002-quotes-workflow-snapshots.md)

### Impact
- ✅ **Single Source of Truth** - All quotes use frozen batch prices
- ✅ **Legal Compliance** - SENT/APPROVED snapshots protected
- ✅ **Data Integrity** - No manual price editing = no errors
- ✅ **Audit Trail** - Complete history preserved via soft delete

**Next:** Testing with real data + PDF export preparation

---

## 🧭 Milestone 0 - Navigation Fix ✅ COMPLETED (Day 32)

**Users can now navigate from ANYWHERE to ANYWHERE!**

### ✅ Completed
- ✅ **App.vue** - Global layout with conditional header/footer
- ✅ **AppHeader.vue** - Hamburger menu navigation
  - Logo: KOVO RYBKA red fish + GESTIMA (red/black) + version badge
  - Search icon (Ctrl+K) with dropdown
  - Favorites icon (placeholder)
  - User badge (username + role)
  - Hamburger dropdown: Dashboard, Díly, Sady cen, Windows, Nastavení, Master Data (admin), Logout
- ✅ **AppFooter.vue** - 3-column layout
  - "Be lazy. It's way better than talking to people." motto
  - Original branding from Alpine.js era
- ✅ **WindowsView.vue** - Fixed to work within global chrome (header visible)
- ✅ **Work Centers → Admin Console** - Moved from standalone nav to Master Data tab
  - Inline modal editing (consistent with other admin tabs)
  - Admin-only access (`/admin/work-centers/*` routes)
  - Removed from main navigation (accessible via Master Data > Tab 3)

### Impact
- ❌ BEFORE: User TRAPPED after leaving Dashboard (no navigation)
- ✅ AFTER: Full navigation from anywhere to anywhere!

### Next: Milestone 1 - Core Flow
- PartOperationsModule.vue (WorkCenter dropdown, inline editing)
- PartMaterialModule.vue (MaterialInput API integration)
- PartPricingModule.vue (Batch pricing display)

---

## 🪟 Floating Windows System (v1.10.0 - Day 31)

**First complete Vue 3 feature - zero Alpine.js!**

### ✅ Completed
- ✅ **WindowsStore** - State management s Pinia
  - findFreePosition() - no overlapping
  - arrangeWindows() - Grid/Horizontal/Vertical
  - Save/Load views + localStorage
  - Favorite views support
- ✅ **FloatingWindow Component**
  - Drag & drop (titlebar)
  - Resize (bottom-right corner)
  - Collision detection - NESMÍ se překrývat
  - Magnetic snapping - 15px threshold
  - Screen boundaries - NEMOHOU opustit viewport
  - Minimize/Maximize/Close controls
- ✅ **WindowManager Component**
  - Toolbar s module buttons
  - Arrange dropdown (Grid/Horizontal/Vertical)
  - Save/Load views
  - Favorite views quick-access
  - Minimized windows bar
- ✅ **5 Module Placeholders** (ready pro integraci)
- ✅ **Route Update** - `/workspace` → `/windows`

### Technical Highlights
- **Collision Detection**: Rectangle overlap algorithm
- **Boundary Enforcement**: Math.max/min clamping (x=[0, screenW-winW], y=[100, screenH-winH])
- **Magnetic Snapping**: 15px threshold na všechny strany (funguje při drag i resize)
- **Auto-Arrange**: Když není místo → auto grid → add new → arrange all

### Impact
- ✅ **Vue Migration Milestone** - First complete Vue 3 + Pinia feature!
- ✅ Foundation for future SPA migration
- ✅ Reusable component architecture
- ✅ Zero overlapping, zero out-of-bounds bugs

**Notes:** Final Alpine.js release (v1.6.1). Windows system = test-bed pro budoucí full SPA migration. Viz: [docs/VUE-MIGRATION.md](VUE-MIGRATION.md)

---

## 🛡️ Mandatory Verification Protocol (v1.9.5 - Day 29)

**Trust Recovery: From chat agreement → Embedded in CLAUDE.md!**

### ✅ Completed
- ✅ CLAUDE.md Section 4: MANDATORY VERIFICATION checklist
  - Banned phrases ("mělo by být OK")
  - Required phrases ("Verification: grep = 0 matches")
  - Verification protocol for Frontend CSS, Backend, Multi-file refactor
- ✅ CLAUDE.md WORKFLOW: Systematic approach for multi-file changes
  - grep ALL → read ALL → edit ALL → verify
  - Porušení = opakování 4x → ztráta důvěry!
- ✅ KRITICKÁ PRAVIDLA #13: MANDATORY VERIFICATION
- ✅ ANTI-PATTERNS.md: L-033, L-034, L-035 with incident analysis
  - L-035 CRITICAL: 4-attempt incident breakdown
  - Root cause, impact, prevention checklist

**Impact:** No more "should be OK" without grep proof! Self-correcting workflow embedded in AI logic.

---

## 🎨 Design System Cleanup (v1.9.4 - Day 29)

**ONE Building Block principle enforced!**

### ✅ Completed
- ✅ Removed ALL duplicate CSS utility classes (372 lines!)
  - `.btn*`, `.part-badge`, `.time-badge*`, `.frozen-badge` variants
  - 5 workspace modules cleaned (213 lines)
  - 6 view components cleaned (159 lines)
- ✅ Single source of truth: `design-system.css` ONLY
- ✅ Verified: Zero duplicate definitions remain (grep confirmed)
- ✅ Consistent badge/button styling across ENTIRE app
- ✅ Documentation updated: CHANGELOG + CLAUDE.md (L-033, L-034, L-035)

**Impact:** Consistent UX, easier maintenance, smaller bundle, zero visual regressions!

---

## 🎉 Latest: Vue SPA Testing Complete (Phase 4 - Day 29-31)

**Breaking Change:** Material moved from Part to MaterialInput (Lean Part architecture)

### ✅ Completed
- ✅ DB Schema - `material_inputs` + `material_operation_link` tables
- ✅ Models - MaterialInput, Part (revision fields), Operation (M:N)
- ✅ Migration - Alembic `a8b9c0d1e2f3` applied
- ✅ API - 8 new endpoints (CRUD + link/unlink)
- ✅ Price Calculator - New functions for MaterialInput
- ✅ Documentation - ADR-024 + CHANGELOG v1.8.0

### 🚧 Pending
- 🚧 Frontend - PartMaterialModule.vue (MaterialInput API)
- 🚧 Frontend - PartOperationsModule.vue (display linked materials)
- 🚧 Tests - Backend pytest for new endpoints

**Benefits:** Part is now lean (identity only), supports 1-N materials, M:N material-operation relationships, BOM-ready for v3.0 PLM.

---

## 🎯 Current Focus

**Phase 4: Testing & Deployment (Week 7-8)**
- ✅ Unit tests (Vitest) - **286 tests passing!**
- ✅ Store tests (auth, ui, parts, operations)
- ✅ API tests (client, interceptors, errors)
- ✅ Component tests (Button, Input, Modal, DataTable, FormTabs, Spinner, Select)
- 🚧 E2E tests (Playwright)
- 🚧 Performance optimization
- 🚧 FastAPI integration
- 🚧 Deployment strategy

---

## 📊 Vue SPA Migration Progress

| Phase | Status | Progress | Duration |
|-------|--------|----------|----------|
| Phase 1: Foundation | ✅ Complete | 100% | 7 days (Day 1-7) |
| Phase 2: Workspace | ✅ Complete | 100% | 14 days (Day 8-21) |
| Phase 3: Remaining Pages | ✅ Complete | 100% | 7 days (Day 22-28) |
| **Phase 4: Testing & Deployment** | ⏳ In Progress | 25% | 12 days (Day 29-40) |

**Overall Progress:** 75% (28/40 days)

---

## ✅ Phase 4 - Testing (Day 29-31)

### 🎯 Test Coverage: 286 tests passing

| Category | Tests | Files | Coverage |
|----------|-------|-------|----------|
| **Stores** | 87 | 4 | auth, ui, parts, operations |
| **API** | 20 | 1 | client, interceptors, errors |
| **Components** | 178 | 7 | Button, Input, Modal, DataTable, FormTabs, Spinner, Select |
| **Demo** | 1 | 1 | HelloWorld |
| **TOTAL** | **286** | **13** | **100% pass rate** |

### Technical Highlights
- ✅ **Vitest 4.0.18** - Fast, modern testing framework
- ✅ **@vue/test-utils** - Vue component testing
- ✅ **Pinia testing** - Store unit tests with mocked API
- ✅ **axios-mock-adapter** - HTTP request mocking
- ✅ **Teleport testing** - Modal component with document.querySelector
- ✅ **Deep equality** - Object comparison with toEqual()
- ✅ **Intl.NumberFormat** - Non-breaking space handling

### Lessons Learned (L-024 to L-027)
- **L-024:** Teleport requires `document.querySelector` + `attachTo: document.body`
- **L-025:** `textContent` includes whitespace - use `.trim()` when needed
- **L-026:** Deep object equality requires `.toEqual()`, not `.toContain()`
- **L-027:** `Intl.NumberFormat` uses non-breaking spaces - `.replace(/\u00A0/g, ' ')`

### Build Time
- Test execution: **~1.2s** for 286 tests
- Bundle size: **60.67 KB gzipped** (unchanged)

---

## ✅ Phase 3 Completed (Day 22-28)

### Shared Components (2)
- ✅ DataTable.vue - Universal table
- ✅ FormTabs.vue - Tab layout

### Views Created (9)
- ✅ PartsListView
- ✅ PartCreateView
- ✅ PartDetailView (4 tabs with inline modules) ⭐
- ✅ WorkCentersListView (legacy - kept for direct access)
- ✅ WorkCenterEditView (legacy - kept for direct access)
- ✅ BatchSetsListView
- ✅ MasterDataView (admin - includes Work Centers as Tab 3) ⭐
- ✅ SettingsView
- ✅ WindowsView (floating windows) ⭐ NEW

### Routes Added (10)
- ✅ `/parts` - Parts list
- ✅ `/parts/new` - Create part
- ✅ `/parts/:partNumber` - Part detail
- ✅ `/admin/work-centers/new` - Create work center (admin-only) ⭐
- ✅ `/admin/work-centers/:workCenterNumber` - Edit work center (admin-only) ⭐
- ✅ `/pricing/batch-sets` - Batch sets list
- ✅ `/admin/master-data` - Admin master data (Work Centers Tab 3 uses inline modal) ⭐
- ✅ `/settings` - Settings
- ✅ `/windows` - Floating windows (NEW)

### Backend Reviewed (3 routers, 32 endpoints)
- ✅ materials_router.py (15 endpoints)
- ✅ work_centers_router.py (7 endpoints)
- ✅ admin_router.py (10 endpoints)

### Build Metrics
- Bundle size: **60.67 KB gzipped** ✅ (under 100KB target)
- Build time: 1.66s
- TypeScript: Strict mode passing ✅

---

## 📦 System Architecture

### Frontend (Vue 3 + TypeScript)
```
src/
├── views/
│   ├── auth/ (1 view) - Login
│   ├── dashboard/ (1 view) - Dashboard
│   ├── parts/ (3 views) - List, Create, Detail
│   ├── workCenters/ (2 views) - List, Edit (legacy, direct access only)
│   ├── pricing/ (1 view) - BatchSets List
│   ├── workspace/ (1 view + 5 modules)
│   ├── windows/ (1 view) - Floating Windows ⭐ NEW
│   ├── admin/ (1 view) - MasterData (4 tabs: Norms, Groups, Categories, Work Centers) ⭐
│   └── settings/ (1 view) - Settings
├── components/
│   ├── ui/ (8 components) - DataTable, FormTabs, Modal, etc.
│   ├── layout/ (2 components) - AppHeader, AppFooter
│   ├── workspace/ (2 components) - Panel, Toolbar
│   ├── windows/ (2 components) - FloatingWindow, WindowManager ⭐ NEW
│   └── modules/ (5 components) - Parts, Pricing, Operations, Material, BatchSets ⭐ NEW
├── stores/ (7 stores) - auth, ui, parts, batches, operations, materials, windows ⭐ NEW
├── api/ (5 modules) - parts, batches, operations, materials, auth
└── router/ - 19 routes with guards (1 new: /windows) ⭐ NEW

Total: 13 views, 19 routes, 7 stores, 17+ components
```

### Backend (FastAPI + SQLAlchemy)
- ✅ All routers reviewed (parts, batches, operations, features, materials, work_centers, admin)
- ✅ Optimistic locking (ADR-008)
- ✅ Role-based access
- ✅ Soft delete pattern

---

## 🚀 What's Working

### ✅ Fully Functional
- Authentication & Authorization (login, role-based access)
- Parts management (list, create, detail with 4 tabs)
- Workspace (multi-panel, tab switching, part selection)
- Operations module (inline editing, add/delete, work centers)
- Material module (parser, stock cost calculation)
- Pricing module (batches, sets, cost breakdown)
- **Admin Master Data Console** (4 tabs: Material Norms, Groups, Price Categories, Work Centers) ⭐
  - Inline modal editing for all tabs (consistent UX)
  - Admin-only access control
  - Work Centers integrated into admin console
- Settings (user preferences)
- **Floating Windows** (drag, resize, snap, save/load views) ⭐ NEW
- DataTable component (sorting, pagination, formatting)
- FormTabs component (horizontal/vertical, badges)

### ⏳ Placeholder/TODO
- Batch set detail view (route exists, view TODO)
- Part pricing standalone view (route TODO)

---

## 📝 Next Steps (Phase 4)

### Week 7: Testing
1. **Unit Tests (Vitest)**
   - Stores (auth, parts, operations, batches, materials, ui)
   - API modules (interceptors, error handling)
   - Utilities/helpers
   - Target: >80% coverage

2. **Component Tests**
   - DataTable (sorting, pagination, selection)
   - FormTabs (tab switching, disabled states)
   - Modal, ConfirmDialog
   - Form components (Input, Select, etc.)

3. **E2E Tests (Playwright)**
   - Login flow
   - Create part → Add material → Add operations → View pricing
   - Workspace navigation
   - Batch pricing workflow
   - Work center CRUD

4. **Performance Tests**
   - Lighthouse audit (target: >95)
   - Tab switch <50ms
   - Input update <16ms
   - Memory <50MB

### Week 8: Deployment
1. **Production Build**
   - Environment variables
   - Build optimization
   - Code splitting

2. **FastAPI Integration**
   - Serve Vue from FastAPI
   - SPA routing (catch-all)
   - Static assets

3. **Deployment Strategy**
   - Staging deployment
   - Internal testing (1 week)
   - Feature flag (Vue vs Jinja2)
   - Gradual rollout
   - Monitoring & rollback plan

---

## 📊 Quality Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Bundle size | <100KB gzip | 60.67 KB | ✅ |
| Build time | <5s | 1.66s | ✅ |
| TypeScript | Strict | Passing | ✅ |
| Test coverage | >80% | 0% | ⏳ |
| Lighthouse | >95 | TBD | ⏳ |
| Tab switch | <50ms | TBD | ⏳ |

---

## 🐛 Known Issues

None. All TypeScript errors resolved, build passing.

---

## 📚 Documentation

### 📖 Active Documentation

| Dokument | Status | Účel |
|----------|--------|------|
| **[ULTIMATE-ROADMAP-TO-BETA.md](ULTIMATE-ROADMAP-TO-BETA.md)** | ✅ ACTIVE | **SINGLE SOURCE OF TRUTH** - Road to BETA (M0 ✅, M1 ✅, M2 🔄, M3 ⏳) |
| **[STATUS.md](STATUS.md)** | ✅ ACTIVE | Historie (co JE hotovo) - tento soubor |
| **[BACKLOG.md](BACKLOG.md)** | ✅ ACTIVE | Items na později (post-BETA) |
| **[VISION.md](VISION.md)** | ✅ ACTIVE | Dlouhodobá vize (1 rok roadmap) |
| **[DESIGN-SYSTEM.md](DESIGN-SYSTEM.md)** | ✅ ACTIVE | **BIBLE!** Design tokens + Vue components + patterns |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | ✅ ACTIVE | System architecture overview |
| **[VUE-MIGRATION.md](VUE-MIGRATION.md)** | ✅ ACTIVE | Vue SPA migration guide (Phase 1-4) |
| **[../CLAUDE.md](../CLAUDE.md)** | ✅ ACTIVE | AI assistant rules (workflow, anti-patterns) |
| **[../CHANGELOG.md](../CHANGELOG.md)** | ✅ ACTIVE | Version history |

### 🗄️ Archives

| Folder | Purpose |
|--------|---------|
| **[archive/](archive/)** | Legacy docs (Alpine.js, old roadmaps) - see [archive/README.md](archive/README.md) |
| **[audits/](audits/)** | Audit reports (security, performance) - historical reference |
| **[sprints/](sprints/)** | Sprint reports - historical reference |

---

**Status Summary:** Phase 3 complete + Floating Windows System implemented (v1.10.0). 13 views, 19 routes, 7 stores, 17+ components. First complete Vue 3 feature (zero Alpine.js). Bundle size 60.67 KB gzipped. Ready for Phase 4: Testing & Deployment. 🚀
