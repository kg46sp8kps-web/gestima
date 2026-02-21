# ADR-023: Workspace Module Architecture

**Status:** Prijato (Design Phase)
**Date:** 2026-01-28
**Timeline:** v3.0+ (Q2 2026+)

---

## Context

Potrebujeme flexibilni workspace system: vice modulu na obrazovce soucasne, propojene barevnymi "linky". Zmena v jednom modulu automaticky aktualizuje propojene moduly.

```
┌─ Workspace ─────────────────────────────────┐
│  [Parts] ──🔴── [BatchSets]                 │
│     │                                        │
│    🔴 (cerveny link = sdileny context)       │
│     ↓                                        │
│  [Operations]                                │
│                                              │
│  [Customers] ──🟢── [Quotes]                │
└─────────────────────────────────────────────┘
```

---

## Decision

### Architektura (3 vrstvy)

**1. Module Interface** — kazdy modul implementuje:
- `moduleType`, `moduleId`, `linkColor`, `linkContext`
- `init()`, `onLinkChange(context)`, `destroy()`
- `emitToLink(eventType, data)`

**2. LinkManager** — centralni komunikace:
- 5 link barev: red, green, blue, yellow, purple
- `emit(color, payload)` — notifikuje vsechny subscribers
- `subscribe/unsubscribe(color, module)`
- Stav persistovan v localStorage

**3. WorkspaceController** — layout management:
- `addPanel(moduleType, linkColor, position)`
- `removePanel(panelId)`
- Layout ulozen v localStorage

**4. BroadcastChannel sync** — volitelna synchronizace mezi okny prohlizece

### Migracni plan

| Faze | Kdy | Co |
|------|-----|----|
| Phase 1 | TEd (v1.5+) | Moduly jako Alpine components, bez workspace UI |
| Phase 2 | v2.0 | Pridat LinkManager, propojit moduly pres eventy |
| Phase 3 | v3.0+ | Plny Workspace UI (drag/resize/saved layouts) |

### Checklist pro novy modul

Kazdy novy modul MUSI:
- Implementovat ModuleInterface
- Prijimat `config.linkColor` a `config.moduleId`
- Implementovat `onLinkChange(context)`
- Emitovat zmeny pres `emitToLink()`
- Byt registrovan v ModuleRegistry
- Fungovat standalone i v linked contextu

---

## Consequences

### Vyhody
- Modularna architektura — kazdy modul je nezavisla komponenta
- Zpetna kompatibilita — existujici stranky fungují bez zmeny (Phase 1)
- Postupna migrace bez prepisovani existujiciho kodu

### Trade-offs
- 9-12 sprintu pro plny workspace (Phase 3)
- Vyssi komplexita pro nove moduly (nutno implementovat interface)

### Zamitnuty alternativy
- iFrames — pomalé, slozita komunikace
- Web Components — overkill pro Alpine.js stack
- React/Vue migrace — masivni refaktoring, ztrata investice do Alpine.js

---

## Soubory

```
app/static/js/
├── core/
│   ├── module-interface.js
│   ├── module-registry.js
│   ├── link-manager.js
│   ├── workspace-controller.js
│   └── multi-window-sync.js
└── modules/
    ├── parts.js
    ├── batch-sets.js
    └── ...
```

---

## Related ADRs

- ADR-022: BatchSet Model (prvni workspace-ready modul)
- ADR-013: localStorage UI Preferences (layout persistence)
