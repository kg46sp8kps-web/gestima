# ADR-013: localStorage for UI Preferences

**Status:** Accepted
**Date:** 2026-01-25
**Context:** Parts List column visibility persistence

---

## Context

When implementing the Parts List with column visibility selector (`/parts`), we needed to persist user preferences across sessions. The options were:

1. **DB sync** - Store preferences in database per user
2. **localStorage** - Store preferences in browser

## Decision

**Use localStorage for UI preferences.**

## Rationale

### Why localStorage wins:

| Factor | localStorage | DB Sync |
|--------|-------------|---------|
| **Latency** | 0ms (instant) | ~150ms (API round-trip) |
| **Complexity** | 10 LOC | 50+ LOC (API, model, migration) |
| **Race conditions** | None | Possible (multi-tab) |
| **Offline support** | Yes | No |
| **Multi-device sync** | No | Yes |

### Key insight:

Column visibility is a **device-specific** preference, not user data. Different devices may have different screen sizes warranting different visible columns.

### KISS principle:

The simpler solution (localStorage) handles 95%+ of use cases. The 5% edge case (multi-device sync) can be addressed later via Export/Import if metrics show demand.

## Implementation

```javascript
// Save preferences
localStorage.setItem('parts_columns', JSON.stringify(visibleColumns));

// Load preferences (with defaults)
const saved = localStorage.getItem('parts_columns');
const columns = saved ? JSON.parse(saved) : defaultColumns;
```

### Reset functionality:

A "Reset" button allows users to restore default column visibility, addressing the "I messed up my settings" scenario.

## Consequences

### Positive:
- Zero latency UI updates
- No API endpoints needed
- No database migration
- No race conditions
- Works offline

### Negative:
- Settings don't sync across devices
- Settings lost when browser data cleared

### Mitigations:
- Reset button for easy recovery
- Future: Export/Import config (v1.2+ if metrics warrant)

## Future Enhancement Path

If >20% of users need multi-device sync:

```
┌─────────────────────────────────────────────────┐
│  Export/Import Config (Simple)                   │
│  - Export button → JSON file download            │
│  - Import button → upload JSON file              │
│  - Effort: 2-3h                                  │
└─────────────────────────────────────────────────┘

vs.

┌─────────────────────────────────────────────────┐
│  Full DB Sync (Complex)                          │
│  - API endpoints for preferences                 │
│  - Conflict resolution (last-write-wins?)        │
│  - Migration for existing users                  │
│  - Effort: 8-12h                                 │
└─────────────────────────────────────────────────┘
```

## Affected Files

- `app/templates/parts/list.html` - Alpine.js localStorage read/write
- `app/static/css/layout.css` - Column visibility CSS

## References

- [NEXT-STEPS.md](../NEXT-STEPS.md) - Implementation details
- Similar pattern: VS Code settings, browser bookmarks

---

**Decision made by:** Architecture team
**Approved:** 2026-01-25
