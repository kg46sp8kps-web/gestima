# ADR-025: Workspace Layout System - Resizable Panels

**Status:** Accepted
**Date:** 2026-01-29
**Deciders:** Roy + User
**Related:** ADR-023 (Workspace Module Architecture), ADR-024 (Vue SPA Migration)

---

## Context

Potřebujeme flexibilní workspace systém pro práci s více moduly současně (Parts, Operations, Material, Pricing). Uživatelé chtějí:
- Vidět více modulů najednou (např. Parts list + Part detail)
- Měnit proporce panelů podle potřeby
- Uložit oblíbené layouty
- Rychle přepínat mezi layouty

### Evaluated Options

1. **Floating Windows** (inspiro: Windows 95)
   - ✅ Maximální flexibilita
   - ❌ Window management hell (překrývání,ztráta oken)
   - ❌ Složitější implementace (z-index, drag boundaries)
   - ❌ Mobile unfriendly

2. **Tiled Panels** (inspiro: tmux, i3wm)
   - ✅ Žádné překrývání
   - ✅ Jednodušší UX
   - ❌ Méně flexibility (fixed splits)

3. **Resizable Panels** (inspiro: VSCode, modern IDEs)
   - ✅ Balance flexibility vs simplicity
   - ✅ Mobile-friendly (auto-collapse)
   - ✅ Známé UX pattern

---

## Decision

**Implementovat Resizable Panels (Option 3) s 6 preset layouts.**

### Architektura

```typescript
// Preset layouts
- Single (1 panel, 100%)
- Dual-H (2 panels horizontal, 50/50 resizable)
- Dual-V (2 panels vertical, 50/50 resizable)
- Triple (3 columns, 33/33/34 resizable)
- Quad (2x2 grid, rows resizable)
- Hex (3x2 grid, rows resizable)

// Implementation
- CSS Grid + Flexbox
- Custom drag handles (ResizableDivider.vue)
- localStorage persistence (per-layout proportions)
- Keyboard shortcuts (Ctrl+1-6)
```

### Technical Details

**Components:**
- `ResizableSplitContainer.vue` - Container with dividers
- `ResizableDivider.vue` - Drag handle component
- `WorkspacePanel.vue` - Individual panel (module loader)

**Composables:**
- `useResizablePanels.ts` - Resize logic (mouse/touch events)
- `useWorkspaceKeyboard.ts` - Keyboard shortcuts

**Store:**
- `windowsStore.ts` - Layout state, proportions, favorites

**Bundle Impact:** ~2KB gzipped (zero dependencies)

---

## Consequences

### Positive

✅ **Rychlejší implementace** - 2 dny místo 2 týdnů (floating windows)
✅ **Konzistentní UX** - Žádné ztracené okna, žádné překrývání
✅ **Performance** - CSS Grid je hardware-accelerated
✅ **Mobile-friendly** - Auto-collapse na single panel (<1024px)
✅ **Zero dependencies** - Custom implementation, full control
✅ **Accessibility** - Keyboard navigation (Ctrl+1-6)

### Negative

❌ **Méně flexibility** - Nelze umístit panel "kde chci"
❌ **Fixed presets** - Jen 6 layoutů (ne custom grid)
❌ **Nested resize limited** - Quad/Hex pouze row-level resize

### Mitigations

- **Phase 4:** Custom floating windows jako opt-in (power users)
- **Future:** Custom layout builder (drag-drop panel placement)
- **Workaround:** 6 presets pokrývá 90% use cases

---

## Alternatives Considered

### Alternative 1: Pure Floating Windows

**Pros:**
- Maximální flexibilita
- Známé UX (desktop apps)

**Cons:**
- Složitější implementace (collision, z-index, boundaries)
- Window management overhead
- Mobile nepoužitelné
- ~10KB bundle (external lib nebo custom complex logic)

**Rejected because:** UX complexity > flexibility benefit pro většinu uživatelů.

---

### Alternative 2: Fixed Tiled (No Resize)

**Pros:**
- Nejjednodušší implementace
- Žádný resize state management

**Cons:**
- Zero flexibility
- Power users frustrovaní
- Nelze přizpůsobit workflow

**Rejected because:** Uživatelé potřebují měnit proporce (např. wide table vs narrow sidebar).

---

## Implementation Timeline

**Phase 1 (v1.10.0 - Completed):**
- ✅ 6 preset layouts
- ✅ Simple resize (Dual-H, Dual-V, Triple)
- ✅ Nested resize (Quad, Hex rows)
- ✅ localStorage persistence
- ✅ Keyboard shortcuts
- ✅ Mobile auto-collapse

**Phase 2 (v2.0 - Future):**
- Custom layout builder (drag-drop)
- Column-level resize for Quad/Hex
- Layout export/import (JSON)

**Phase 3 (v3.0 - Future):**
- Floating windows (opt-in)
- Multi-monitor support
- Layout templates per workflow (e.g., "Pricing workflow", "Engineering workflow")

**Phase 4 (v4.0 - Power Users):**
- Custom popout windows (Chrome API)
- Collaborative layouts (shared workspaces)

---

## References

- **Implementation:** `docs/reference/UX-GUIDE.md` sekce 2 (Navigace a workspace)
- **Components:** `frontend/src/components/workspace/`
- **Related ADR:** ADR-023 (Workspace Module Architecture)
- **Inspiration:** VSCode split view, JetBrains IDE layouts

---

## Notes

**Floating windows = Future feature, NOT abandoned!**

Rozhodnutí pro resizable panels je pragmatické (time-to-market + UX consistency). Floating windows zůstávají v backlogu jako opt-in pro power users.

**User feedback:** Po 6 měsících produkčního použití přehodnotíme zda floating windows je stále požadavek.

---

**Version:** 1.0
**Last Updated:** 2026-01-30
