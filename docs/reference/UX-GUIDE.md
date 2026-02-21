# GESTIMA UX Guide v2.0

**Jediny zdroj pravdy pro vsechno "jak se aplikace chova".** Vizualni tokeny, barvy, CSS tridy → viz [DESIGN-SYSTEM.md](DESIGN-SYSTEM.md).

> **2 dokumenty, jasne rozdeleni:**
> - **DESIGN-SYSTEM.md** = "Jak to vypada?" (tokeny, barvy, CSS, ikony, vizualni komponenty)
> - **UX-GUIDE.md** (tento) = "Jak se to chova?" (flows, interakce, dialogy, navigace, a11y)

---

## 1. Filosofie

| Pilir | Proc | Dusledek |
|-------|------|----------|
| **Dark-first** | Optimalizovano pro dilnu a kancelar (vecerni smena) | Vsechny barvy testovany na tmavem pozadi |
| **Compact density** | Hodne dat na male plose — tabulky, formulare, ribbony | Default = compact, touch = comfortable |
| **Floating windows** | Uzivatel porovnava data z vice modulu najednou | Kazdy modul = samostatne okno, linking groups |
| **Ghost-only** | Cistota, minimalni vizualni sum | Transparentni tlacitka, zadne filled, zadne gradienty |

**Cilovy uzivatel:** Technolog / kalkulant ve strojirenske firme. Pracuje s cisly (casy, rozmery, ceny). Potrebuje rychlost a prehled, ne vizualni efekty.

---

## 2. Navigace a workspace

### 2.1 App layout

```
┌─────────────────────────────────────────────────────────────┐
│  AppHeader (56px, fixed)                                    │
│  ┌──────┐ ┌──────────┐ ┌─────────────┐ ┌────────────────┐  │
│  │ Menu │ │ Search   │ │ Arrange btns│ │ Quick Modules  │  │
│  └──────┘ └──────────┘ └─────────────┘ └────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Workspace (flex: 1)                                        │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐               │
│  │ FloatWin  │  │ FloatWin  │  │ FloatWin  │               │
│  │ (Module)  │  │ (Module)  │  │ (Module)  │               │
│  └───────────┘  └───────────┘  └───────────┘               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  AppFooter (32px, fixed) │ Status │ Density toggle │        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Floating windows architektura

```
WindowsView.vue (container)
  └── FloatingWindow.vue (draggable, resizable okno)
        └── XxxListModule.vue (coordinator)
              ├── XxxListPanel.vue (levy panel — seznam)
              └── XxxDetailPanel.vue (pravy panel — detail)
```

Kazdy modul je **split-pane coordinator**: LEFT seznam + RIGHT detail.

**Pravidla:**
- Komponenty max **300 LOC** (L-036)
- `views/` jsou DEPRECATED — pouzij jen pro Auth, Settings, WindowsView
- Zadne `any` typy v TypeScriptu

### 2.3 Jak uzivatel otvira moduly

| Metoda | Popis | Kdy pouzit |
|--------|-------|------------|
| **Hamburger menu** | Levy drawer (280px), vsechny moduly + layouty + nastaveni | Plny prehled, mene casty pristup |
| **SearchBar** | Type-ahead filtrovani nazvu modulu | Rychly pristup, keyboard-first |
| **Quick Modules** | 4 ikonova tlacitka vpravo v headeru | Nejcasteji pouzivane moduly |
| **Oblibene layouty** | Bar pod headerem, ulozene pohledy | Obnoveni kompletniho workspace |
| **Linked window** | `openLinked()` z jineho modulu | Otevreni child okna se sdilenym kontextem |

### 2.4 Mapa modulu

| Modul | Typ okna | Primarni use case |
|-------|----------|-------------------|
| **Part Main** | master | Sprava dilu — CRUD, zakladni informace |
| **Technology** | master/child | Operace + materialy pro dil |
| **Pricing** | master/child | Cenova kalkulace, batch sety |
| **Partners** | standalone | CRM — zakaznici a dodavatele |
| **Quotes** | standalone | Nabidky a poptavky |
| **Manufacturing** | master | Vyrobni polozky |
| **Accounting** | standalone | Financni dashboard, obrat, bilance |
| **TimeVision** | standalone | AI odhad casu z vykresu |
| **File Manager** | standalone | Sprava souboru, nahravani, preview |
| **Batch Sets** | standalone | Sprava vyrobnich davek |
| **Materials** | standalone | Katalog materialu |
| **Admin** | standalone | Material normy, pracoviste, cenove kategorie |

### 2.5 Window management

**Zakladni akce:**
- **Drag** — uchop titlebar, pretahni kamkoli (snap 15px k hranam a ostatnim oknum)
- **Resize** — uchop roh okna, min 300×200px
- **Minimize** — tlacitko v titlebaru, okno zmizi do taskbaru
- **Maximize** — tlacitko v titlebaru, 100vw × (100vh − 88px)
- **Close** — tlacitko v titlebaru

**Arrange mody:** Grid | Horizontal | Vertical

**Persistence:** Layouty se ukladaji do localStorage. Defaultni layout se nacte pri startu.

### 2.6 Workspace layouts

6 preset layoutu, prepinani `Ctrl+1` az `Ctrl+6`, `Ctrl+0` reset:

| Layout | Popis |
|--------|-------|
| Single | 1 panel (100%) |
| Dual-H | 2 panely vedle sebe (resizable) |
| Dual-V | 2 panely nad sebou (resizable) |
| Triple | 3 sloupce (resizable) |
| Quad | 2×2 grid (radky resizable) |
| Hex | 3×2 grid (radky resizable) |

Proporce auto-save do localStorage per-layout. Mobile (<1024px) = single panel, dividery skryty.

**Composables:**

| Composable | Co dela |
|------------|---------|
| `useResizablePanels` | Resize logic (mouse/touch), sizes v %, auto-save do localStorage |
| `useWorkspaceKeyboard` | Ctrl+1–6 pro prepinani layoutu |

**Store akce** (`workspace.ts`):
```typescript
store.setLayout(layoutId)
store.updatePanelModule(area, module)
store.updateLayoutProportions(layoutId, sizes)
store.toggleFavorite(layoutId)
```

### 2.7 Window linking system

Moduly se propojuji pres **linking group** (barva). Propojena okna sdileji kontext (vybrany Part) pres `windowContext` store.

```
Barvy: red │ blue │ green │ yellow
Role:  master (ridi kontext) │ child (sleduje kontext)
```

**Role a chovani:**

| Role | Levy panel (PartList) | Sleduje context | Context ribbon |
|------|-----------------------|-----------------|----------------|
| `null` (standalone) | viditelny | ne | ne |
| `'master'` | viditelny | ne — ridi context | ne |
| `'child'` | skryty | ano | ano |

**Jak otevrit prilnkovane okno — `useLinkedWindowOpener`:**

```typescript
const { openLinked } = useLinkedWindowOpener({
  get windowId()     { return props.windowId },
  get linkingGroup() { return props.linkingGroup ?? null },
  onGroupAssigned(group) {
    if (selectedPart.value?.id > 0) {
      contextStore.setContext(group, selectedPart.value.id, ...)
    }
  }
})

openLinked('part-technology', `Technologie - ${part.part_number}`)
```

**Chovani:** Pokud master **nema** barvu → auto-assign volna barva. Pokud master **ma** barvu → child se otevre ve stejne barve.

**Props ktere musi kazdy modul prijimat:**

```typescript
interface Props {
  windowId?:     string
  windowRole?:   'master' | 'child' | null
  linkingGroup?: 'red' | 'blue' | 'green' | 'yellow' | null
}
```

**Template podminky:**

```html
<!-- Levy panel: standalone (null) NEBO master -->
<div v-if="!linkingGroup || windowRole === 'master'" class="left-panel">

<!-- Context ribbon: jen pro child -->
<div v-if="linkingGroup && windowRole !== 'master' && selectedPart" class="context-ribbon">

<!-- Full-width pravy panel: jen pro child -->
<div class="right-panel" :class="{ 'full-width': linkingGroup && windowRole !== 'master' }">
```

**Watch na context — jen pro child:**

```typescript
watch(contextPartId, (newPartId) => {
  if (props.windowRole === 'master') return  // master context nesleduje
  // child logic...
})
```

**Implementovane moduly:**

| Modul | Master | Child |
|-------|--------|-------|
| PartMainModule | ano | — |
| ManufacturingItemsModule | ano | — |
| PartTechnologyModule | ano | ano |
| PartPricingModule | ano | ano |

---

## 3. Uzivatelske flows

### 3.1 Login a inicializace

```
/login → zadej credentials → POST /api/auth/login
       → JWT HttpOnly cookie
       → prefetchAll() (parts, materials, work centers)
       → redirect /windows
       → nacti defaultni layout (pokud nastaven)
       → zobraz floating windows
```

### 3.2 Part CRUD

**Zobrazeni a vyber:**
1. Otevri Part Main modul (menu / search / quick module)
2. Levy panel: virtualizovany seznam dilu (search input nahore)
3. Klik na dil → pravy panel zobrazi detail (info-ribbon)

**Vytvoreni noveho dilu:**
1. Klik na "+" tlacitko v headeru leveho panelu
2. Zobrazi se PartCreateForm v pravem panelu
3. Vyplneni: article_number, nazev
4. Klik "Ulozit" → API POST → dil se prida na zacatek seznamu
5. Toast success: "Dil vytvoren"

**Editace:**
1. Klik na Edit ikonu v info-ribbonu
2. Ribbon prejde do edit mode (`--bg-raised` + `--border-strong`)
3. Uprava poli
4. Klik "Ulozit" nebo Klik "Zrusit"
5. Toast success/cancel

**Smazani:**
1. Klik na Trash ikonu
2. `confirm()` dialog (type: danger): "Opravdu chcete smazat dil?"
3. Potvrzeni → API DELETE (soft delete) → dil zmizi ze seznamu
4. Toast success: "Dil smazan"

### 3.3 Technology workflow

```
Part Main [master, red] ──openLinked──→ Technology [child, red]
                                        │
                                        ├─ Context ribbon (cislo dilu, nazev)
                                        ├─ MaterialInputSelectorV2 (parser)
                                        ├─ Operations table (VueDraggable)
                                        └─ Production history
```

**Pridani operace:** Klik "+" nebo Ctrl+N → nova operace na konci → collapsed

**Editace operace (inline):**
- Seq: double-click → input → Enter ulozi, Escape zrusi
- Pracoviste: click na cislo → TypeAheadSelect → vyber → auto-pojmenovani operace
- Casy (tp, tj): primo v inputu → debounced save (500ms)
- Koeficienty (Ko, Ke): primo v inputu → debounced save

**Prerazeni operaci:** Drag handle (GripVertical) → pretahni → renumber seq 10-20-30...

**Material input parser:**
1. Zadej text: "D20 1.4301 100mm"
2. API parsuje → preview vysledku (prumer, material, delka)
3. Uzivatel potvrdi NEBO upravi rucne (MaterialManualInput fallback)
4. **NIKDY** auto-confirm — vzdy preview pred ulozenim

### 3.4 Pricing workflow

1. Otevri Pricing modul (standalone nebo linked z Part Main)
2. Vyber dil → zobrazi se pricing detail
3. Klik "Pridat davku" → zadej mnozstvi
4. System automaticky vypocita cenu (material + operace + rezie)
5. Price breakdown zobrazen v tabulce

### 3.5 Partner management

1. Otevri Partners modul
2. Levy panel: seznam partneru s tabs (Vsichni / Zakaznici / Dodavatele)
3. Klik na partnera → pravy panel s FormTabs (Zakladni / Kontakt / Adresa / Poznamky)
4. Edit mode toggle → uprava → ulozeni → toast success
5. Novy partner: "+" tlacitko → formular → ulozit

### 3.6 Quote creation

**Z poptavky (AI):**
1. QuoteFromRequest modul → nahraj PDF poptavky
2. AI parsuje → extrahuje polozky, mnozstvi, pozadavky
3. Preview → uzivatel potvrdi/upravi → vytvori nabidku

**Manualne:**
1. Quotes modul → "+" nova nabidka
2. Vyber zakaznika → pridej polozky → souhrn
3. Uloz nabidku

### 3.7 File management

1. File Manager modul → split-pane (seznam vlevo, preview vpravo)
2. Upload: drag & drop zona nebo klik pro vyber
3. Soubor se linkuje k entitam (Part, Operation, Quote) pres polymorfni FileLink
4. Preview: PDF inline viewer, obrazky primo v panelu

---

## 4. Interakcni patterns

### 4.1 Inline editing vs modal — rozhodovaci strom

```
Kolik poli editujes?
│
├─ 1 pole → INLINE EDIT (click-to-edit)
│            Priklad: seq v OperationRow, workcenter select
│
├─ 2–5 logicky spojenych → INFO RIBBON EDIT MODE
│                           Priklad: Part detail, Partner basic info
│
└─ 6+ poli NEBO komplexni validace → MODAL
                                      Priklad: CuttingConditionEditModal, SaveLayoutDialog
```

### 4.2 Edit mode toggle (info-ribbon pattern)

```
[View mode]                          [Edit mode]
┌─────────────────────────────┐      ┌─────────────────────────────┐
│ bg-surface + border-default │  →   │ bg-raised + border-strong   │
│ Hodnoty jako text           │      │ Hodnoty v inputech          │
│ Edit ikona (tuzka)          │      │ Ulozit + Zrusit tlacitka    │
└─────────────────────────────┘      └─────────────────────────────┘

Spusteni: Klik na Edit ikonu → isEditing = true
Ulozeni:  Klik "Ulozit" → API call → isEditing = false → toast
Zruseni:  Klik "Zrusit" NEBO Escape → isEditing = false (data neukladat)
```

**ZAKAZANO:** Cerveny border v edit mode. Pouzit `--border-strong` (viz DESIGN-SYSTEM.md s.5).

### 4.3 Drag & drop

**Operace reordering (VueDraggable):**
- Handle: `.drag-handle` (GripVertical ikona)
- Ghost: `opacity: 0.4`
- Chosen: `cursor: grabbing`
- **Sync guard:** Behem dragu (`isDragging = true`) se preskoci watch na store — prevence race condition
- Po dropu: renumber seq 10-20-30... → bulk API update

**Window dragging:**
- Uchop: titlebar
- Snap: 15px k hranam viewportu a k ostatnim oknum
- Omezeni: okno zustane ve viewportu

### 4.4 Search a filtrovani

**Pravidlo:** Vzdy client-side filter nad nactenymi daty. Server search jen kdyz dataset > 5000 zaznamu.

| Komponenta | Chovani |
|-----------|---------|
| **AppSearchBar** | Type-ahead filtrovani nazvu modulu, dropdown |
| **PartListPanel** | Search input, computed filter pres parts store |
| **TypeAheadSelect** | ArrowDown/Up, Enter vyber, Escape zruseni, Tab vyber + focus move |
| **Partner tabs** | Filtrovani pres tab (Vsichni / Zakaznici / Dodavatele) |

### 4.5 Selection patterns

**Single row selection:**
- Klik na radek → `--state-selected` (bily overlay 6% opacity)
- Druhy klik na stejny radek → deselect
- Detail panel se zobrazi/aktualizuje pri selekci

### 4.6 Click-to-edit (OperationRow pattern)

```
[Display mode]          [Edit mode]
 "10"          →  ┌──────────┐
 (double-click)   │ 10       │  ← input s auto-select
                  └──────────┘
                  Enter = ulozit, Escape = zrusit, Blur = ulozit
```

---

## 5. Formularove patterns

### 5.1 Input komponenta

```vue
<Input
  v-model="form.name"
  label="Nazev dilu"
  placeholder="napr. Loziskove teleso"
  required               <!-- cervena * u labelu -->
  :error="errors.name"   <!-- cerveny border + chybova zprava -->
  hint="Max 100 znaku"   <!-- sedy text pod inputem -->
  mono                   <!-- monospace font pro cisla -->
/>
```

**Direktiva `v-select-on-focus`:** Na vsech numericckych inputech. Klik = select all.

**Number inputy:** Skryte nativni sipky (no spinners). Krokovy vstup pres step atribut.

### 5.2 TypeAheadSelect

Plne ovladatelny klavesnici:
- **ArrowDown/Up** — navigace v seznamu
- **Enter** — vyber aktualni polozky
- **Escape** — zruseni bez vyberu
- **Tab** — vyber + presun focusu na dalsi pole
- **Typing** — filtruje seznam v realnem case
- `maxVisible: 8` — max 8 polozek, pak "+X dalsich..."
- Click outside = cancel

### 5.3 Material parser

```
Textovy vstup: "D20 1.4301 100mm"
                    │
                    ▼
            API parseMaterialDescription
                    │
                    ▼
            Preview (prumer=20, mat=1.4301, delka=100)
                    │
           ┌────────┴────────┐
           │                 │
       [Potvrdit]      [Upravit rucne]
           │                 │
           ▼                 ▼
     Ulozit MI        MaterialManualInput
```

**PRAVIDLO:** NIKDY automaticky potvrzovat vysledek parseru. Vzdy preview + explicitni potvrzeni.

### 5.4 Validace

- **Inline error:** Cerveny border na inputu + chybova zprava pod inputem
- **Required marker:** Cervena `*` u labelu
- **Timing:** Validuj pri blur NEBO pri change (ne az pri submit)
- **Server validace:** 422 odpoved → namapuj chyby na fieldy z response body

### 5.5 Debounced save

```
Uzivatel pise → debounce timer 500ms → API call
                │
                ├─ Novy keystroke? → reset timer
                ├─ Timer vyprsely? → odeslat
                └─ Component unmount? → flush vsechny pending timery!
```

- Timer per field/per entity (`Map<entityId, timeout>`)
- `onBeforeUnmount`: flush pending timery (prevence data loss)
- Behem ukladani: zadny spinner (prilis casty)

### 5.6 Edit mode lifecycle

```typescript
// 1. Start edit
function startEdit() {
  editForm = { ...originalData }
  isEditing = true
}

// 2. Save
async function saveEdit() {
  if (!validate(editForm)) return
  await api.update(editForm)
  isEditing = false
  showSuccess('Ulozeno')
}

// 3. Cancel
function cancelEdit() {
  isEditing = false  // editForm se zahodi
}
```

---

## 6. Dialog system a zpetna vazba

### 6.1 Ctyri stavy kazde datove sekce

**KAZDA** komponenta zobrazujici data z API MUSI resit vsechny 4 stavy:

```
                    ┌──────────────┐
                    │ initialLoad? │
                    └──────┬───────┘
                           │
                    ┌──────┴──────┐
                   ANO           NE
                    │             │
              ┌─────▼─────┐  ┌───▼───────┐
              │  LOADING   │  │ data.len? │
              │  Spinner + │  └───┬───────┘
              │  text      │      │
              └────────────┘  ┌───┴───┐
                             =0      >0
                              │       │
                        ┌─────▼────┐ ┌▼──────┐
                        │  EMPTY   │ │ DATA  │
                        │  HERO    │ │ table │
                        │  ikona + │ │ list  │
                        │  text +  │ │ cards │
                        │  CTA     │ └───────┘
                        └──────────┘
```

| Stav | Vizual | Pravidla |
|------|--------|----------|
| **LOADING** | Spinner + text "Nacitam..." | Jen pri prvnim loadu (`initialLoading`). NIKDY pri re-fetch |
| **EMPTY** | HERO ikona (48px) + text + hint s CTA | Hint: "Klikni na + pro pridani" |
| **ERROR** | Chybova zprava + Retry tlacitko | Uzivatelsky srozumitelna zprava, ne stack trace |
| **DATA** | Normalni zobrazeni | Tabulka, seznam, karty... |

**Anti-pattern:** Bliknuti spinneru pri prepnuti entity. Reseni: `initialLoading` flag (true jen pri uplne prvnim loadu).

### 6.2 Toast notifikace

```typescript
import { useUiStore } from '@/stores/ui'
const ui = useUiStore()

ui.showSuccess('Ulozeno')            // 3s
ui.showError('Chyba pri ukladani')   // 5s
ui.showWarning('Pozor na duplicitu') // 4s
ui.showInfo('Nacteno 42 polozek')    // 3s

// Custom trvani (0 = nezmizi, vyzaduje rucni dismiss)
ui.showToast('Zprava', 'info', 10000)
```

**Pravidla:**
- Pozice: vpravo nahore, pod header
- Auto-dismiss + manualni dismiss (klik)
- **NIKDY** toast pro kritickou chybu ktera blokuje workflow → pouzit dialog

### 6.3 Dialog system (confirm / alert)

**POVINNE** pro vsechny potvrzovaci a informativni modaly. **ZAKAZANO** `window.confirm()` / `window.alert()`.

```typescript
import { confirm, alert } from '@/composables/useDialog'

// Potvrzeni destruktivni akce
const ok = await confirm({
  title: 'Smazat?',
  message: 'Tato akce je nevratna!',
  type: 'danger',
  confirmText: 'Smazat',
  cancelText: 'Zrusit'
})
if (ok) await deleteItem()

// Informativni alert
await alert({ title: 'Uspech', message: 'Ulozeno', type: 'success' })
```

**confirm() API:**

| Option | Type | Default | Popis |
|--------|------|---------|-------|
| `title` | `string` | required | Titulek dialogu |
| `message` | `string` | required | Podporuje `\n` pro odradkovani |
| `type` | `'danger' \| 'warning' \| 'info' \| 'success'` | `'warning'` | Vizualni typ |
| `confirmText` | `string` | `'Potvrdit'` | Text potvrzovacih tlacitka |
| `cancelText` | `string` | `'Zrusit'` | Text zrusovacih tlacitka |

Vraci `true` (potvrzeno) nebo `false` (zruseno / ESC).

**alert() API:** Stejne options jako `confirm`, navic typ `'error'`, bez `cancelText`. Resolves on close.

**Typy dialogu:**

| Typ | Ikona | Barva | Pouziti |
|-----|-------|-------|---------|
| `danger` | Trash2 | Pink | Smazani, destruktivni akce |
| `warning` | AlertTriangle | Orange | Upozorneni |
| `info` | Info | Blue | Informativni |
| `success` | Check | Green | Potvrzeni uspechu |
| `error` | XCircle | Pink | Chyba (jen alert) |

**Keyboard:** Enter = confirm/close, ESC = cancel/close

**Architektura:**
- Composable: `frontend/src/composables/useDialog.ts`
- Komponenty: `ConfirmDialog.vue`, `AlertDialog.vue` (globalne v App.vue)
- Jeden dialog zaroven, Promise-based, auto-cleanup

**Kdy dialog vs Modal.vue:**

| Dialog system (`confirm`/`alert`) | Modal.vue primo |
|-----------------------------------|-----------------|
| Smazani, nevratne akce | Formulare s inputy |
| Unsaved-changes varování | Multi-step wizards |
| Jednoduche success/error notifikace | Scrollable content |
| | File upload |

**Anti-patterns:**
```typescript
// SPATNE
if (window.confirm('Delete?')) { ... }
alert('Error!')
const showDialog = ref(false)  // v-model pattern

// SPRAVNE
const ok = await confirm({ title: 'Delete?', message: '...', type: 'danger' })
```

**Custom modal pattern (pro formulare):**
```vue
<Modal v-model="show" size="md">
  <template #header><FileIcon :size="20" /><h3>Title</h3></template>
  <!-- content -->
  <template #footer>
    <button class="icon-btn" @click="cancel"><X :size="24" /></button>
    <button class="icon-btn icon-btn-primary" @click="submit"><Check :size="24" /></button>
  </template>
</Modal>
```

### 6.4 Toast vs dialog — rozhodovaci strom

```
Je akce nevratna? (delete, overwrite)
├─ ANO → confirm() dialog (type: danger)
│
└─ NE → Potrebuje uzivatel odpovedet?
         ├─ ANO → confirm() nebo alert() dialog
         │
         └─ NE → Je to jen feedback?
                  ├─ ANO → Toast (success/error/warning/info)
                  │
                  └─ Blokuje to workflow?
                     ├─ ANO → alert() dialog (type: error)
                     └─ NE → Toast error (5s)
```

### 6.5 Loading patterns

| Pattern | Kdy | Jak |
|---------|-----|-----|
| **Global loading** | Inicializace, prefetch | `useUiStore().isLoading` (counter-based) |
| **Module initial load** | Prvni nacteni dat | `store.initialLoading` (true jen jednou) |
| **Button loading** | Odeslani formulare | Button prop `loading` → spinner, disabled |
| **Inline** | Debounced save | Zadny vizualni indikator |

---

## 7. Error handling UX

### 7.1 API chyby

| HTTP Status | UX reakce |
|-------------|-----------|
| **Network error** | Toast error + "Zkontrolujte pripojeni" |
| **401 Unauthorized** | Redirect na /login |
| **404 Not Found** | Toast error + prazdny stav |
| **409 Conflict** | Toast warning + "Data byla zmenena jinym uzivatelem" + reload |
| **422 Validation** | Inline error messages na fieldech |
| **500 Server Error** | Toast error + technicky detail v console.error |

### 7.2 Validacni zpravy

- Zobrazit **pod** inputem, cerveny text (`.input-error`)
- Cerveny border na inputu (`.input-error-state`)
- Required pole: cervena `*` u labelu
- **Validuj co nejdriv** — pri blur nebo change, ne az pri submit
- Server 422: namapuj errors na fieldy z response body

### 7.3 Optimistic updates

| Operace | Chovani |
|---------|---------|
| **Drag reorder** | Okamzity vizualni update → backend bulk update. Pri chybe: rollback |
| **Inline edit** | Okamzity update v store → debounced API. Pri chybe: restore + toast error |
| **Delete** | Confirm dialog PRED smazanim (ne optimistic). Po potvrzeni: odeber → API call |

### 7.4 Conflict resolution

Optimistic locking (ADR-008):
1. Kazda entita ma `version` sloupec
2. Pri updatu se posle `version` v requestu
3. Neshoduje se → 409 Conflict
4. UX: Toast warning + nabidka "Nacist znovu"

---

## 8. Responsive chovani

### 8.1 Container queries

**PRAVIDLO:** Pouzivat `@container`, NIKDY `@media`. Container queries reagoji na sirku kontejneru (okna), ne viewportu.

| Sirka kontejneru | Sloupce |
|-------------------|---------|
| < 400px | 1 |
| 400–600px | 2 |
| 600–900px | 3 |
| 900–1200px | 4 |
| > 1200px | 6 (max 1600px) |

### 8.2 Mobile auto-collapse

Pri viewportu < 1024px:
- Floating windows: maximized
- Split-pane: vertikalni stack (seznam nad detailem)
- Resize dividery: skryty

### 8.3 Density mody

| Mod | Default | Pouziti |
|-----|---------|---------|
| **compact** | ANO | Desktop, factory terminal |
| **comfortable** | NE | Tablet, touch screen |

Prepnuti: toggle v footeru. Implementace: `data-density` atribut na `<html>`.
Persistence: localStorage (`gestima-density`).

---

## 9. Pristupnost (a11y)

### 9.1 Klavesnicova navigace

| Klavesa | Kontext | Akce |
|---------|---------|------|
| **Tab** | Globalni | Standardni focus flow |
| **Escape** | Modal / dropdown / edit mode | Zavreni / zruseni |
| **Enter** | Dialog / formular | Potvrzeni akce |
| **ArrowDown/Up** | TypeAheadSelect, seznamy | Navigace v polozakch |
| **Ctrl+N** | Technology modul | Nova operace |
| **Ctrl+1–6** | Workspace | Prepnuti layout presetu |

**`useKeyboardShortcuts` composable:**
```typescript
const { registerShortcut } = useKeyboardShortcuts()
registerShortcut({ key: 'n', ctrl: true, handler: () => addItem() })
// Auto-cleanup na onBeforeUnmount
```
- `allowInInput: false` (default) — nespusti se v inputu
- `allowInInput: true` — i v inputu (vyjimecne)

### 9.2 Focus management

- **Focus ring:** BILY (`--focus-ring`), **NIKDY** modry
- **Focus background:** Jemny bily tint (`--focus-bg`)
- `:focus-visible` na vsech interaktivnich prvcich
- Auto-focus pri otevreni modalu na confirm tlacitko
- Auto-focus pri otevreni TypeAheadSelect na input

### 9.3 ARIA atributy

| Prvek | Atributy |
|-------|----------|
| Modal / Dialog | `role="dialog"`, `aria-modal="true"` |
| Toast container | `aria-live="polite"` |
| Icon buttons | `aria-label` nebo `title` |
| Expandable sekce | `aria-expanded="true/false"` |
| Interaktivni prvky | `data-testid` |

### 9.4 WCAG 2.1 AA checklist

- [ ] Kontrast textu: min 4.5:1
- [ ] Min velikost textu: `--text-xs` (12px)
- [ ] Touch target: min 24×24px, doporuceny 32×32px
- [ ] Respektovat `prefers-reduced-motion`
- [ ] Barva neni jediny nositel informace (vzdy ikona + barva)
- [ ] Prazdne stavy: descriptivni text (ne jen ikona)
- [ ] Tabulky: `<th>` s popisem sloupce

---

## 10. Animace a prechody

### 10.1 Transition tokeny

| Token | Pouziti |
|-------|---------|
| `--t-fast` | Hover, focus ring, micro-interactions |
| `--t-normal` | Panel otevreni, mode switch |
| `--t-slow` | Modaly, toasty, page transitions |

### 10.2 Kdy animovat

| ANO | NE |
|-----|----|
| Hover efekty | Initial page load |
| Focus ring transitions | Data refresh / re-fetch |
| Expand/collapse | Inline edit toggle |
| Toast vstup/vystup | Badge update |
| Drag feedback | Zmena hodnoty v tabulce |
| Dropdown otevreni/zavreni | |

### 10.3 Specificke animace

**Toast:** Enter: `translateX(100px)` + `opacity: 0` → normal (0.3s). Leave: reverse + `scale(0.8)`.

**Dropdown:** Enter: `opacity: 0` + `translateY(-4px)` → normal (0.15s). Leave: reverse.

**Drag & drop:** Ghost: `opacity: 0.4`. Chosen: `cursor: grabbing`. Animation: 200ms.

**Action card hover:** `translateY(-1px)` + subtle glow + brand border.

### 10.4 Pravidla

1. **VZDY** pouzit transition tokeny: `var(--t-fast/normal/slow)`
2. **NIKDY** JS-based animace pro jednoduche prechody
3. **`prefers-reduced-motion`:** Vypnout non-essential animace
4. Resize handle: brand color on hover s `var(--t-fast)`

---

## 11. Rozhodovaci stromy

### 11.1 Modal vs floating window vs inline

```
Uzivatel potrebuje porovnat data s jinym modulem?
│
├─ ANO → FLOATING WINDOW (openLinked / openWindow)
│
└─ NE → Kolik poli?
         ├─ 1 pole → INLINE EDIT (click-to-edit)
         ├─ 2–5 poli → INFO RIBBON EDIT MODE
         └─ 6+ / komplexni → MODAL
```

### 11.2 Toast vs dialog

```
Akce je nevratna?
├─ ANO → CONFIRM DIALOG (type: danger)
└─ NE → Uzivatel musi odpovedet?
         ├─ ANO → CONFIRM DIALOG
         └─ NE → Blokuje workflow?
                  ├─ ANO → ALERT DIALOG (type: error)
                  └─ NE → TOAST
```

### 11.3 Inline edit vs form modal

```
Jeden field?
├─ ANO → CLICK-TO-EDIT (double-click → input → blur saves)
└─ NE → 2-5 spojenych?
         ├─ ANO → EDIT MODE TOGGLE (info-ribbon)
         └─ NE → MODAL s formularem
```

### 11.4 Paginace vs virtualizace

```
Pocet zaznamu?
├─ < 100 → ZADNA PAGINACE
├─ 100–1000 → SIMPLE PAGINATION (DataTablePagination)
└─ > 1000 → TANSTACK VIRTUAL + INFINITE SCROLL (ADR-049)
```

### 11.5 Standalone vs linked child

```
Modul zobrazuje vlastni seznam entit?
├─ ANO → STANDALONE (vlastni ListPanel)
└─ NE → Navazano na Part?
         ├─ ANO → LINKED CHILD (context ribbon, auto-sync)
         └─ NE → STANDALONE (bez leveho panelu)
```

---

## 12. Checklist pro novy modul

### Architektura
- [ ] Coordinator `XxxModule.vue` < 300 LOC
- [ ] Split-pane: `XxxListPanel.vue` + `XxxDetailPanel.vue`
- [ ] Props: `windowId`, `windowRole`, `linkingGroup`
- [ ] Linked mode: context ribbon pro child windows

### Stavy
- [ ] LOADING: Spinner + text (jen `initialLoading`)
- [ ] EMPTY: HERO ikona + text + CTA hint
- [ ] ERROR: Chybova zprava + retry
- [ ] DATA: Normalni zobrazeni

### Design system
- [ ] Ghost-only buttons (ZADNE filled)
- [ ] Ikony z `@/config/icons` s `ICON_SIZE.*`
- [ ] CSS tokeny `var(--*)` (ZADNE hardcoded hex/px)
- [ ] Container queries (ZADNE media queries)
- [ ] Fluid heights (ZADNE fixed px heights)
- [ ] Focus ring bily (NIKDY modry)
- [ ] Edit mode: `--bg-raised` + `--border-strong`

### Interakce
- [ ] `useKeyboardShortcuts` kde relevantni
- [ ] `data-testid` na interaktivnich prvcich
- [ ] Toast pro CRUD operace
- [ ] `confirm()` pro destruktivni akce
- [ ] Debounced save s flush na `onBeforeUnmount`
- [ ] `v-select-on-focus` na numericckych inputech

### Vykon
- [ ] Virtualizace pro seznamy > 100 polozek (ADR-049)
- [ ] Store prefetch v `usePrefetch.ts`
- [ ] Lazy loading pro tezke komponenty

---

## 13. Referencni implementace

| Soubor | Demonstruje |
|--------|-------------|
| `frontend/src/components/modules/operations/OperationsDetailPanel.vue` | Drag & drop, debounced save, 4 stavy, keyboard shortcuts |
| `frontend/src/components/modules/operations/OperationRow.vue` | Inline editing, click-to-edit, TypeAheadSelect |
| `frontend/src/components/modules/PartMainModule.vue` | Split-pane coordinator, linked windows, CRUD lifecycle |
| `frontend/src/stores/ui.ts` | Toast API, density system, loading counter |
| `frontend/src/composables/useKeyboardShortcuts.ts` | Keyboard shortcut registration |
| `frontend/src/composables/useDialog.ts` | Promise-based confirm/alert |

**Souvisejici ADR:**

| ADR | Rozhodnuti |
|-----|------------|
| [ADR-025](../ADR/025-workspace-layout-system.md) | Workspace Layout System (6 layoutu, resize) |
| [ADR-026](../ADR/026-universal-module-pattern.md) | Universal Module Pattern (split-pane, < 300 LOC) |
| [ADR-030](../ADR/030-universal-responsive-module-template.md) | Responsive Module Template (container queries) |
| [ADR-049](../ADR/049-virtualized-list-performance.md) | Virtualized List Performance (TanStack Virtual) |
| [ADR-008](../ADR/008-optimistic-locking.md) | Optimistic locking (conflict resolution) |
| [ADR-013](../ADR/013-localstorage-ui-preferences.md) | localStorage pro UI preferences |

---

_Verze: 2.0 (2026-02-21) | Zdroj pravdy pro UX/chovani. Vizual → DESIGN-SYSTEM.md_
