# WORKSPACE-GUIDE v2.0

## Floating Windows Architektura

Gestima pouziva **Floating Windows** system — NE klasicke views/routing.

```
WindowsView.vue (container)
  └── FloatingWindow.vue (draggable, resizable okno)
        └── XxxListModule.vue (coordinator)
              ├── XxxListPanel.vue (levy panel — seznam)
              └── XxxDetailPanel.vue (pravy panel — detail)
```

Kazdy modul je split-pane coordinator: LEFT seznam + RIGHT detail.

---

## Module Pattern (povinny)

```
frontend/src/components/modules/
  XxxListModule.vue      — koordinator (split-pane)
  XxxListPanel.vue       — seznam + tlacitka
  XxxDetailPanel.vue     — detail polozky
```

Priklad: `QuotesListModule.vue` → `QuoteListPanel.vue` + `QuoteDetailPanel.vue`

Pravidla:
- Komponenty max 300 LOC (L-036, hook blokuje)
- `views/` jsou DEPRECATED — pouzij jen pro Auth, Admin, Settings, WindowsView
- Zadne `any` typy v TypeScriptu (L-049, hook blokuje)

---

## Klic. Composables

| Composable | Soubor | Co dela |
|------------|--------|---------|
| `useResizablePanels` | `composables/useResizablePanels.ts` | Resize logic (mouse/touch), sizes v %, auto-save do localStorage |
| `useWorkspaceKeyboard` | `composables/useWorkspaceKeyboard.ts` | Ctrl+1-6 pro prepinani layoutu |

`useResizablePanels` parametry: `initialSizes`, `direction`, `minSize`, `maxSize`, `onResize`.

---

## Workspace Layouts

6 preset layoutu, prepinani `Ctrl+1` az `Ctrl+6`, `Ctrl+0` reset.

| Layout | Popis |
|--------|-------|
| Single | 1 panel (100%) |
| Dual-H | 2 panely vedle sebe (resizable) |
| Dual-V | 2 panely nad sebou (resizable) |
| Triple | 3 sloupce (resizable) |
| Quad | 2x2 grid (radky resizable) |
| Hex | 3x2 grid (radky resizable) |

Proporce auto-save do localStorage per-layout. Mobile (<1024px) = single panel, dividers skryty.

---

## Store (workspace.ts)

Klic. akce:
```typescript
store.setLayout(layoutId)                        // prepni layout
store.updatePanelModule(area, module)            // priradi modul panelu
store.updateLayoutProportions(layoutId, sizes)   // uloz velikosti panelu
store.toggleFavorite(layoutId)                   // oblibeny layout
```

---

## Design System

Zdroj pravdy: `frontend/template.html` (vizualni) + `design-system.css` (runtime).
Detaily: `docs/reference/DESIGN-SYSTEM.md`.

- Ghost buttons ONLY
- WHITE focus ring
- Neutralni selected rows
- Ikony: `ICON_SIZE.*` z `@/config/design`, aliasy z `@/config/icons`
