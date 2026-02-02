# UI Quick Start - Start Here

**🎯 Cíl:** Vytvořit jakékoliv UI za MAX 30 MINUT

**Status:** 🔒 PRODUCTION LOCKED

---

## 🚀 START HERE

Máš 2 dokumenty pro UI development:

### 1. [ULTIMATE UI GUIDE](./ULTIMATE-UI-GUIDE.md) ← **READ THIS FIRST**

**Obsahuje VŠECHNO:**
- Design tokens (spacing, colors, typography)
- Base komponenty (BaseButton, BaseCard, BaseInput, BaseBadge)
- Widget templates (copy-paste ready)
- Layout patterns (Info Grid, Action Grid, Lists)
- 30-min workflow
- CSS anti-patterns
- Production rules

**Použij pro:** Reference, templates, rules

---

### 2. [END-TO-END WORKFLOW](./END-TO-END-WORKFLOW.md) ← **FOLLOW THIS**

**Konkrétní příklad:**
- Manufacturing Items modul (real code)
- Krok za krokem (s časem)
- Mockup → Widgety → Config → Module → Debug
- Real prompty pro Claude.ai

**Použij pro:** First module, step-by-step guide

---

## ⚡ QUICK WORKFLOW

```bash
# 1. MOCKUP (5 min)
Excalidraw → Screenshot

# 2. CLAUDE.AI (10 min)
Upload screenshot → "Vytvoř Vue 3 widget podle ULTIMATE-UI-GUIDE.md"

# 3. CONFIG (3 min)
Copy template → Upravit IDs

# 4. MODULE (2 min)
Copy template → Upravit imports

# 5. REGISTRACE (2 min)
windows.ts + WindowsView.vue + AppHeader.vue

# 6. DEBUG (8 min)
Ctrl+Shift+D → Fix issues

# TOTAL: 30 min ✅
```

---

## 🎨 DESIGN TOKENS (Quick Reference)

```css
/* SPACING (4pt grid) */
padding: var(--space-3);     /* 8px - base */
gap: var(--space-2);         /* 6px - base gap */

/* TYPOGRAPHY */
font-size: var(--text-base); /* 12px */
font-weight: var(--font-medium);

/* COLORS */
color: var(--text-body);
background: var(--bg-surface);
border: 1px solid var(--border-default);

/* LAYOUT */
height: 100%;  /* VŽDY na widget root */
flex: 1;       /* Expandable content */
overflow: auto; /* Scrollable content */
```

---

## ❌ CSS ANTI-PATTERNS

```css
/* ❌ NIKDY */
height: 80px;           /* Fixed height */
padding: 8px;           /* Hardcoded spacing */
color: #ffffff;         /* Hardcoded color */
@media (max-width: 400px) { }  /* Media query */

/* ✅ VŽDY */
height: 100%;           /* Fluid */
padding: var(--space-3); /* Token */
color: var(--text-body); /* Token */
@container widget (max-width: 400px) { }  /* Container query */
```

---

## 🛠️ NÁSTROJE

### CSS Debug Overlay
**Aktivace:** `Ctrl+Shift+D`

**Použij když:**
- Widget má "useknutý spodek"
- Nevíš kde je problém se spacingem
- Widget se nescrolluje

### Base Components
```vue
<BaseButton variant="primary" @click="save">Save</BaseButton>
<BaseInput v-model="name" label="Name" :error="errors.name" />
<BaseCard padding="md"><p>Content</p></BaseCard>
<BaseBadge variant="success">Active</BaseBadge>
```

---

## 🔥 CLAUDE.AI PROMPT (Copy-Paste)

```
[Upload mockup screenshot]

Vytvoř Vue 3 <script setup> widget podle tohoto designu.

REQUIREMENTS:
✅ TypeScript
✅ Props: context?: { data?: YourType | null }
✅ Empty state: "No data"
✅ Design tokens: var(--space-3), var(--text-body)
✅ Container queries (NE @media)
✅ Fluid layout: height: 100%, flex: 1
✅ Base components z '@/components/base/'
✅ Max 200 LOC

ANTI-PATTERNS (NIKDY):
❌ height: 80px
❌ padding: 8px
❌ color: #fff
❌ @media queries

Return COMPLETE .vue file.
```

---

## 📋 30-MIN CHECKLIST

**Před začátkem:**
- [ ] Mockup narýsován
- [ ] Screenshot připraven

**Implementace:**
- [ ] Widgety vygenerovány (Claude.ai)
- [ ] Layout config vytvořen
- [ ] Main module vytvořen
- [ ] Registrace (3 files)

**Debug:**
- [ ] `Ctrl+Shift+D` aktivován
- [ ] Žádné CSS issues
- [ ] Responsive funguje
- [ ] Empty states OK

---

## 🆘 TROUBLESHOOTING

### "Widget má useknutý spodek"
1. `Ctrl+Shift+D`
2. Klikni na widget
3. Čti "Issues"
4. Fix: `overflow: hidden` → `overflow: auto`

### "Nevím jak začít"
1. Přečti [ULTIMATE-UI-GUIDE.md](./ULTIMATE-UI-GUIDE.md)
2. Následuj [END-TO-END-WORKFLOW.md](./END-TO-END-WORKFLOW.md)

---

## 📚 DALŠÍ GUIDES

- [VUEDRAGGABLE-GUIDE.md](./VUEDRAGGABLE-GUIDE.md) - Drag & drop patterns
- [DESIGN-SYSTEM.md](../reference/DESIGN-SYSTEM.md) - Color palette, tokens
- [ARCHITECTURE.md](../reference/ARCHITECTURE.md) - System overview

---

**🚀 NOW GO BUILD!**

Start: [ULTIMATE-UI-GUIDE.md](./ULTIMATE-UI-GUIDE.md)
