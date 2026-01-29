# Debug Workflow (Roy's Way)

**Verze:** 1.0 (2026-01-29)
**Extrahováno z:** CLAUDE.md v3.9

**Účel:** Debugování často zabere víc času než psaní kódu. Tento workflow šetří hodiny.

---

## Hlavní pravidlo

> **1 problém = 1 root cause = 1 fix**

**Nikdy:** 3+ pokusy na "zkoušku"
**Vždy:** Analyzuj → Pochop → Oprav jednou

---

## Krok 1: STOP - Nepřidávej kód! (0-2 min)

Když něco nefunguje:

```
1. ✅ F12 → Console tab
2. ✅ Přečti PRVNÍ chybu (další jsou často následné)
3. ✅ Klikni na odkaz vpravo (např. app.js:123) → ukáže přesný řádek
```

**RED FLAGS:**
| Typ chyby | Význam |
|-----------|--------|
| `SyntaxError` | Problém v JavaScript/HTML syntaxi |
| `ReferenceError` | Proměnná neexistuje (komponenta se neinicializovala) |
| `TypeError` | Špatný typ dat |

---

## Krok 2: Identifikuj Root Cause (2-5 min)

### SyntaxError Checklist

- [ ] **Inline JSON v HTML atributu?** (`x-data="func({{ json }})"`)
  - **FIX:** Přesuň do `<script>window.DATA = {{ json | tojson | safe }}</script>`

- [ ] **`<script>` tag v included template?** (Jinja2 `{% include %}`)
  - **FIX:** Přesuň do parent template `{% block scripts %}`

- [ ] **Trailing comma v JavaScript objektu?**
  - **FIX:** Použij `{% if not loop.last %},{% endif %}` v Jinja2 loops

- [ ] **Escapované znaky v řetězci?**
  - **FIX:** Použij Jinja2 `| safe` filter

### ReferenceError Checklist

- [ ] **Alpine.js komponenta se neinicializovala?**
  - **Důvod:** Syntax error výše (oprav ten)
- [ ] **Chybějící `x-data` atribut?**
- [ ] **Event listener před inicializací?**

---

## Krok 3: Oprav jednou editací (1-2 min)

**Pravidlo 1 editace:**
```
✅ Najdi root cause
✅ Udělej JEDNU opravu
✅ Test
```

**Pokud nefunguje:**
```
❌ NESTŘÍLEJ dalšími pokusy!
✅ git revert (vrať změnu)
✅ Znovu analyzuj (možná špatný root cause)
```

---

## Co NEDĚLAT (Anti-patterns)

❌ **Záplaty na záplaty:**
```
Pokus 1: Přidat console.log
Pokus 2: Změnit event listener
Pokus 3: Přidat try/catch
Pokus 4: Komentovat kód
Pokus 5: Vytvořit "simple" verzi
...
Pokus 15: ???
```

❌ **"Možná to pomůže" syndrome:**
- Měnit věci bez analýzy
- Komentovat kód "na zkoušku"
- Přidávat `!important`, `|| null`, `try/catch` všude

❌ **Ignorovat první chybu:**
- Scrollovat přes 50 chyb v konzoli
- Řešit 10. chybu místo 1.

---

## Common Pitfalls

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| `SyntaxError: Unexpected token` | Inline JSON v HTML atributu | `<script>window.DATA = {{ json \| tojson \| safe }}</script>` |
| `ReferenceError: X is not defined` | Alpine.js se neinicializoval | Fix syntax error (viz výše) |
| `</script>` tag uprostřed HTML | Include má vlastní `<script>` | Přesuň do parent `{% block scripts %}` |
| Trailing comma error | Jinja2 loop generuje `,` za posledním | `{% if not loop.last %},{% endif %}` |
| Page načítá ale nic nefunguje | JavaScript crash | Console tab = první chyba! |

---

## Debug Checklist (před další editací)

```
- [ ] Přečetl jsem PRVNÍ chybu v Console?
- [ ] Vím PŘESNĚ na kterém řádku je problém?
- [ ] Rozumím PROČ ten řádek způsobuje chybu?
- [ ] Mám JEDNO konkrétní řešení (ne "zkusím tohle")?
```

**Pokud jakákoliv odpověď je "NE":**
→ **STOP! Analyzuj víc, NEPIŠ kód!**

---

## Real-World Příklad

### ❌ Co jsem dělal (60+ minut):

1. Přidal console.log debugging (3 min)
2. Změnil `@close-modal` → `x-on:close-modal` (2 min)
3. Opravil trailing commas v JS objektech (5 min)
4. Přesouval `<script>` tagy mezi soubory (10 min)
5. Zakomentoval included template (5 min)
6. Vytvořil "simple" HTML verzi bez Alpine.js (5 min)
7. ... 15+ pokusů bez analýzy
8. **Celkem: 60+ minut**

### ✅ Co jsem měl udělat (5 minut):

1. Console: `SyntaxError: Unexpected token ';'` → Syntax error v JS (1 min)
2. View Source (Ctrl+U): Našel `x-data="adminPanel([{...34 objektů...}])"` (2 min)
3. Identifikace: Obří inline JSON = known issue (1 min)
4. **FIX:** Přesunout do `<script>window.NORMS = {{ json }}` (1 min)
5. **Celkem: 5 minut**

---

## Roy's Debug Mantras

> **"Have you tried turning it off and on again?"**
> = Hard refresh (Ctrl+Shift+R) pro vymazání cache

> **"This is going to be a long day..."**
> = >3 chyby stejného typu → root cause je JEDEN problém

> **"Did you see the first error?"**
> = První chyba v Console je klíč. Zbytek jsou následné.

> **"Stop patching, find the cause!"**
> = 3+ pokusy = špatný přístup. STOP a analyzuj.

---

## Tool Checklist

### Browser DevTools
- **Console tab** - chyby + warnings
- **Sources tab** - breakpoints (pokud potřebuješ)
- **Network tab** - API calls (pokud je problém s backendem)

### View Page Source (Ctrl+U)
- Vidíš co Jinja2 skutečně vygeneroval
- Najdeš inline JSON, escapované znaky, HTML strukturu

### Git
- `git diff` - co jsem změnil?
- `git checkout -- file.html` - vrať soubor
- `git log --oneline -5` - co fungovalo naposledy?

---

## Kdy Eskalovat (zeptat se uživatele)

```
IF (60+ minut debugging AND stále nefunguje):
    ✅ Shrň co jsi zkoušel
    ✅ Ukaž PRVNÍ chybu v Console
    ✅ Ptej se na root cause, ne na další "fix"

    ❌ NE: "Zkusil jsem 10 věcí a nic nefunguje"
    ✅ ANO: "Console říká X na řádku Y, nerozumím proč"
```

---

**Poučení:** Většina bugů má **1 root cause**. Najdi ho PŘED psaním kódu.

---

**Zpět na:** [CLAUDE.md](../../CLAUDE.md)
