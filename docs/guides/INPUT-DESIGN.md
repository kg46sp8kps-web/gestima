# Input Design — Ghost styl

> Canonical vzor pro všechny formulářové vstupy v Gestimě.
> Verze: 1.0 · Platí od design-system.css v6.0

---

## Design rationale

Gestima je dark-only density-first aplikace. Inputy musí být na první pohled jasně
identifikovatelné jako editovatelné pole, ale nesmí vizuálně dominovat.

**Soft box** — jemný průhledný rámeček (`rgba(255,255,255,0.10)`) + lehký podklad (`rgba 4%`) +
malé zaoblení (`var(--rs)`) — dosahuje přesné rovnováhy: pole je vidět, ale neobtěžuje.
Na focusu se rámeček zesvětlí na `--b3` a bg se jemně zvýrazní.

---

## CSS spec

### Base state
```css
background: rgba(255,255,255,0.04);   /* jemný podklad — pole je vidět */
border: 1px solid var(--b2);          /* rgba(255,255,255,0.10) — subtilní rámeček */
border-radius: var(--rs);             /* 4px — mírné zaoblení */
color: var(--t2);                     /* mírně ztlumený text */
```

### Focus state
```css
border-color: var(--b3);              /* rgba(255,255,255,0.15) — viditelný rámeček */
background: rgba(255,255,255,0.07);   /* lehce světlejší bg */
color: var(--t1);                     /* text se rozjasní */
```

### Error state
```css
border-color: var(--warn);            /* amber #fbbf24 — NIKOLIV --err červená */
```

Hint text pod polem (`input-hint-error`) může zůstat `color: var(--err)` — je to text, ne rámeček.

### Disabled state
```css
opacity: 0.4;
cursor: not-allowed;
```

### Focus-visible (accessibility)
```css
outline: 2px solid rgba(255,255,255,0.5);
outline-offset: 2px;
```

---

## Kdy použít `Input.vue` vs inline `.fi`

| Situace | Řešení |
|---|---|
| Formuláře, dialogy, create/edit modaly | **`Input.vue`** |
| Filtry, search bary | **`Input.vue`** |
| Inline editace v tabulkové buňce | `.fi` (legacy v PartDetailCard, bude migrováno) |
| Batch pricing pole | **`Input.vue`** |

**Pravidlo:** Vždy `Input.vue`. `.fi` je legacy — používej jej pouze tam, kde již existuje.
Při nové práci vždy `Input.vue`.

---

## Dostupné komponenty

| Komponenta | Použití |
|---|---|
| `Input.vue` | Text, number, password, email, search |
| `Select.vue` | Native dropdown/select |
| `Textarea.vue` | Víceřádkový text (poznámky, popis) |

---

## Integrace — copy-paste příklady

### Input.vue
```vue
<Input
  v-model="form.name"
  label="Název dílu"
  placeholder="Zadej název…"
  :error="errors.name"
  hint="Maximálně 100 znaků"
  required
/>
```

### Select.vue
```vue
<Select
  v-model="form.workCenter"
  label="Pracoviště"
  :options="workCenterOptions"
  placeholder="— vyber —"
  :error="errors.workCenter"
/>
```

### Textarea.vue
```vue
<Textarea
  v-model="form.note"
  label="Poznámka"
  placeholder="Volný text…"
  :rows="4"
  hint="Interní poznámka, nezobrazuje se zákazníkovi"
/>
```

---

## Co NESMÍŠ dělat

- Hardcoded barvy — `border: 1px solid #444` → **STOP**. Použij `var(--b2)`.
- Ghost styl — `border: none; border-bottom: ...` → **STOP**. Soft box, ne ghost.
- Červená pro error border — `border-color: var(--err)` → **STOP**. Použij `var(--warn)`.
- Modrý focus ring → **STOP**. Vždy `rgba(255,255,255,0.5)`.
- Příliš tmavé bg — `rgba(255,255,255,0.01)` je neviditelné → použij alespoň `0.04`.
