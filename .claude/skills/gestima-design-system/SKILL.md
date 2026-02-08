---
name: gestima-design-system
description: Design system tokens, colors, spacing and component patterns for Gestima UI
---

# Gestima Design System

## Target Display
27" monitor @ 2560x1440 — ultra-compact ERP style

## Design Principles
- Dark-first theme
- Refined & Subtle (no loud colors)
- Ultra-compact (maximize data density)

## Color Palette (CSS Variables)
```css
--color-primary: #991b1b;        /* Red — brand */
--color-danger: #f43f5e;         /* Pink — destructive actions */
--color-success: #22c55e;        /* Green — confirmations */
--color-warning: #eab308;        /* Yellow — caution */
--color-bg-primary: #1a1a2e;     /* Dark background */
--color-bg-secondary: #16213e;   /* Panel background */
--color-bg-tertiary: #0f3460;    /* Card background */
--color-text-primary: #e2e8f0;   /* Main text */
--color-text-secondary: #94a3b8; /* Secondary text */
--color-border: #334155;         /* Borders */
```

## Spacing Grid
```css
--spacing-xs: 2px;
--spacing-sm: 4px;
--spacing-md: 8px;
--spacing-lg: 12px;
--spacing-xl: 16px;
--spacing-2xl: 24px;
```

## Icon Sizes (Lucide)
```typescript
// frontend/src/config/design.ts
ICON_SIZE = { xs: 12, sm: 14, md: 16, lg: 20, xl: 24 }
```

## Component Rules
- VŽDY používej CSS tokeny z `design-system.css`
- NIKDY hardcoded barvy (`#3b82f6` → `var(--color-primary)`)
- NIKDY hardcoded spacing (`12px` → `var(--spacing-lg)`)
- Showcase komponent: `/showcase` route

## Full reference
Viz `docs/reference/DESIGN-SYSTEM.md`
