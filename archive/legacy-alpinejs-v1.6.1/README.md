# Alpine.js Legacy Archive (v1.6.1)

**Archived:** 2026-01-31
**Reason:** Migrated to Vue 3 SPA (ADR-024)
**Git Tag:** `v1.6.1-alpine-final`

---

## What's Here

This archive contains the original GESTIMA frontend built with:
- **Alpine.js** - Reactive UI framework
- **HTMX** - HTML over the wire
- **Jinja2** - Server-side templating

### Directory Structure

```
legacy-alpinejs-v1.6.1/
├── js/                          # Alpine.js modules (4,133 LOC)
│   ├── gestima.js               # Main application entry
│   ├── crud_components.js       # Reusable CRUD components
│   ├── core/
│   │   ├── workspace-controller.js  # DIY SPA router (800 LOC)
│   │   ├── link-manager.js          # Module linking system
│   │   ├── module-interface.js      # Base module interface
│   │   └── module-registry.js       # Module discovery
│   ├── modules/
│   │   ├── parts-list.js        # Parts listing module
│   │   ├── part-operations.js   # Manufacturing operations
│   │   ├── part-material.js     # Material management
│   │   ├── part-pricing.js      # Pricing calculator
│   │   └── batch-sets.js        # Batch pricing sets
│   └── vendor/
│       ├── alpine.min.js        # Alpine.js v3.x
│       └── htmx.min.js          # HTMX v1.x
│
└── templates/                   # Jinja2 templates (12,682 LOC)
    ├── base.html                # Base layout
    ├── index.html               # Dashboard
    ├── workspace.html           # Main workspace view
    ├── parts_list.html          # Parts listing
    ├── parts/
    │   ├── new.html             # Create part form
    │   ├── edit.html            # Edit part form
    │   └── pricing.html         # Part pricing view
    ├── pricing/
    │   ├── batch_sets.html      # Batch sets listing
    │   └── batch_set_detail.html
    ├── admin/
    │   ├── master_data.html     # Admin console
    │   └── material_catalog.html
    ├── auth/
    │   └── login.html           # Login page
    └── ... (19 files total)
```

---

## Why Archived (ADR-024)

### Problems with Alpine.js Stack

1. **800 LOC DIY SPA router** - Custom workspace-controller.js instead of framework
2. **6 anti-patterns** requiring workarounds (L-013 to L-021)
3. **No type safety** - Runtime errors in production
4. **Page flickering** - Full page reloads on navigation
5. **Hiring impossible** - Alpine.js developers don't exist
6. **Not MES-ready** - Can't support v4.0 real-time features

### Benefits of Vue 3 SPA

1. **Professional SPA** - Vue Router, no DIY solutions
2. **TypeScript** - Compile-time type checking
3. **41ms transitions** - 2x faster than Alpine (80ms)
4. **Zero flickering** - Full SPA experience
5. **Pinia stores** - Proper state management
6. **Future-proof** - Ready for v4.0 MES

---

## Historical Reference

### Key Files

| File | Purpose | Vue 3 Equivalent |
|------|---------|------------------|
| `js/core/workspace-controller.js` | SPA routing | `frontend/src/router/` |
| `js/core/link-manager.js` | Module linking | `frontend/src/stores/windows.ts` |
| `js/modules/parts-list.js` | Parts listing | `frontend/src/components/modules/parts/` |
| `js/modules/part-operations.js` | Operations | `frontend/src/components/modules/operations/` |
| `templates/workspace.html` | Main layout | `frontend/src/views/windows/WindowsView.vue` |

### Design Patterns Worth Preserving

1. **Module Interface** (`js/core/module-interface.js`)
   - `init()`, `refresh()`, `destroy()` lifecycle
   - Implemented as Vue composables

2. **Link Manager** (`js/core/link-manager.js`)
   - Multi-window context linking
   - Implemented in Pinia with `linkingGroup` pattern

3. **CRUD Components** (`js/crud_components.js`)
   - Reusable form patterns
   - Now in `frontend/src/components/ui/`

---

## Do NOT Use

This code is **archived for reference only**. Do not:
- Import these files into the active codebase
- Copy-paste without understanding Vue 3 equivalents
- Try to run alongside Vue 3 SPA

---

## Related Documentation

- [ADR-024: Vue SPA Migration](../../docs/ADR/024-vue-spa-migration.md)
- [Vue Migration Guide](../../docs/archive/VUE-MIGRATION.md)
- [CHANGELOG v1.6.1](../../CHANGELOG.md#161---alpine-final)

---

**Total Archived:** 16,815 LOC
**Replaced By:** Vue 3 SPA (~8,000 LOC)
**LOC Reduction:** 52% improvement
