# ADR-026: Universal Module Pattern (Split-Pane Layout)

**Status:** Accepted (2026-01-31)
**Related:** ADR-024 (Vue SPA Migration), ADR-025 (Workspace Layout System)

## Context

Původní monolitické moduly porušovaly L-036 (PartOperationsModule: 796 LOC, PartMaterialModule: 984 LOC) a měly nekonzistentní UX. Všechny modulové okna potřebují stejný layout pattern s podporou Standalone a Linked módu.

## Decision

**Universal Split-Pane Pattern** pro všechna modulová okna:

```
ModuleCoordinator.vue  (<300 LOC — POVINNÉ)
├── LEFT PANEL
│   ├── Standalone mode: PartListPanel.vue (320px)   ← SDÍLENÁ komponenta
│   └── Linked mode: Collapsed badge (80px)
└── RIGHT PANEL
    ├── ModuleHeader.vue (~100 LOC)
    └── ModuleDetailPanel.vue (300-700 LOC)
```

## Rules

1. **Coordinator** — pouze layout + state, žádná business logika, max 300 LOC
2. **Standalone** (`linkingGroup === null`): plný PartListPanel, user vybírá díl
3. **Linked** (`linkingGroup !== null`): collapsed badge "Linked to {part_number}", auto-sync s kontextem
4. **PartListPanel.vue** je SDÍLENÁ — importují ji všechny coordinatory
5. **Design tokens**: výhradně z `design-system.css`, žádné hardcoded hodnoty

## Key Files

```
frontend/src/components/modules/
├── PartOperationsModule.vue   (218 LOC)
├── PartMaterialModule.vue     (219 LOC)
├── PartPricingModule.vue      (223 LOC)
├── PartMainModule.vue         (209 LOC)
├── parts/PartListPanel.vue    ← reused by all
├── operations/OperationsHeader.vue + OperationsDetailPanel.vue
├── material/MaterialHeader.vue + MaterialDetailPanel.vue
└── pricing/PricingHeader.vue + PricingDetailPanel.vue
```

## Coordinator Props Interface

```typescript
interface Props {
  partNumber?: string      // Pro initial selection
  linkingGroup?: LinkingGroup | null  // null = standalone, string = linked
}
```

## Context Sync (Linked Mode)

```typescript
// Watch linked context changes
watch(() => contextStore.getContext(props.linkingGroup), (context) => {
  if (isLinked.value && context) {
    selectedPart.value = partsStore.parts.find(p => p.id === context.partId)
  }
}, { immediate: true })
```

## Consequences

- Všechny coordinatory: 209-223 LOC (L-036 compliance — 67-78% redukce z originálu)
- PartListPanel reused 4+ moduly — single source of truth pro seznam dílů
- Business logika izolována v Detail panelech
- DetailPanels mohou překračovat 300 LOC (domain complexity je oprávněná výjimka)
- Nové moduly (Batches, WorkCenters, Orders) MUSÍ následovat tento pattern

## Future

- Extrahovat `LinkedBadge.vue` (eliminovat duplicitu badge šablony)
- `GenericListPanel<T>` pro Batches, Materials, WorkCenters
