# Verzovací politika GESTIMA

**Datum:** 2026-01-24
**Účel:** Standardizace verzování aplikace a dokumentace

---

## Problém: Inkonzistence verzí

**Zjištěno:** 2026-01-24

| Soubor | Verze | Typ |
|--------|-------|-----|
| `app/config.py` | `VERSION = "1.0.0"` | **App version** |
| `CHANGELOG.md` | `[2.10.0]` | Changelog entry |
| `CLAUDE.md` | `Verze: 2.10.0` | Doc version |
| `README.md` | `GESTIMA 1.0` | Marketing version |
| `docs/ARCHITECTURE.md` | `Verze: 1.1` | Doc version |
| `docs/UI_REFERENCE.md` | `v1.0 LOCKED` | Doc version |
| `docs/P2-PHASE-B-SUMMARY.md` | `Version: 2.10.0` | Doc version |

**Důsledek:** Chaos - není jasné, jaká je aktuální verze aplikace.

---

## Řešení: Semantic Versioning + Document Versioning

### 1. Aplikace (Semantic Versioning)

**Standard:** [Semantic Versioning 2.0.0](https://semver.org/)

**Formát:** `MAJOR.MINOR.PATCH` (např. `1.0.0`)

- **MAJOR** - breaking changes (nekompatibilní API, DB migrace bez backward compatibility)
- **MINOR** - nové funkce (backward compatible)
- **PATCH** - bug fixes (backward compatible)

**Single Source of Truth:** `app/config.py`

```python
class Settings(BaseSettings):
    VERSION: str = "1.0.0"  # ✅ JEDINÁ definice verze aplikace
```

**Použití:**
```python
# app/gestima_app.py
app = FastAPI(
    title="GESTIMA",
    version=settings.VERSION,  # Načítá z config.py
)
```

**API Endpoint:**
```bash
GET /version
# Response: {"version": "1.0.0", "name": "GESTIMA"}
```

---

### 2. Dokumentace (Document Versioning)

**Formát:** `X.Y` (např. `1.0`, `1.1`, `2.0`)

- **X** - major rewrite dokumentu (kompletní přepis)
- **Y** - minor update (nové sekce, opravy)

**Pravidlo:** Každý dokument má vlastní verzi (nezávislou na app verzi).

**Umístění:** V hlavičce dokumentu (metadata)

```markdown
# Název dokumentu

**Verze dokumentu:** 1.2
**Datum:** 2026-01-24
**Autor:** ...
```

---

### 3. ADR (Architecture Decision Records)

**Formát:** Datum přijetí (ne verze)

```markdown
# ADR-XXX: Název rozhodnutí

**Status:** Přijato
**Datum:** 2026-01-24
```

**Důvod:** ADR jsou imutabilní - jakmile přijato, nemění se. Není potřeba verzování.

---

## Aktuální stav (2026-01-24)

### Aplikace

| Vlastnost | Hodnota |
|-----------|---------|
| **App version** | `1.0.0` |
| **Source of truth** | `app/config.py` → `Settings.VERSION` |
| **Zobrazení** | `/docs` (Swagger), `/version` (API) |
| **Changelog** | `CHANGELOG.md` |

### CHANGELOG.md - OPRAVA

**Problém:** `CHANGELOG.md` obsahuje `[2.10.0]` - **NESPRÁVNĚ**

**Vysvětlení:** Čísla `2.x.x` byla použita během vývoje (evoluce z Kalkulator3000 v9.x).
Po úklidu a rename na GESTIMA by měla být verze resetována na `1.0.0`.

**Rozhodnutí:**
- ✅ **Squash** všechny P0/P1/P2 změny do `[1.0.0] - 2026-01-24` (první produkční release)
- ✅ Starší changelog entries (2.x.x) přesunout do sekce `## Pre-release (Development)`

**Důvod:**
- GESTIMA 1.0 je **první produkční verze**
- Verze 2.x.x by měla být až při breaking changes

---

## Navržená korekce verzí

### App version (config.py)

```python
# app/config.py
class Settings(BaseSettings):
    VERSION: str = "1.0.0"  # ✅ SPRÁVNĚ - první produkční release
```

**Status:** ✅ UŽ SPRÁVNĚ

---

### CHANGELOG.md

**Před (NESPRÁVNĚ):**
```markdown
## [2.10.0] - 2026-01-24
...
## [2.9.0] - 2026-01-24
...
```

**Po (SPRÁVNĚ):**
```markdown
## [1.0.0] - 2026-01-24 - First Production Release

### Added
- ✅ P0: Authentication & Authorization (OAuth2, JWT, RBAC)
- ✅ P0: HTTPS deployment (Caddy reverse proxy)
- ✅ P1: Structured logging, global error handler, transaction safety
- ✅ P1: Backup CLI (backup, backup-list, backup-restore)
- ✅ P1: CORS, Rate limiting (slowapi)
- ✅ P2: Optimistic locking (version check)
- ✅ P2: Material Hierarchy (MaterialGroup + MaterialItem)
- ✅ P2: Minimal Snapshot (Batch freeze, price stability)

### Tests
- 98/98 tests passing

### Documentation
- Kompletní ADRs (001, 003-008, 011-012)
- CLAUDE.md (production requirements)
- Audit reports (audit.md, audit-p2b.md)

---

## Pre-release (Development)

**Note:** Tyto verze byly během migrace z Kalkulator3000 v9.x.
Uchovány pro historický kontext.

### [2.10.0] - 2026-01-24 (pre-release)
- P2 Fáze B: Minimal Snapshot

### [2.9.0] - 2026-01-24 (pre-release)
- P2 Fáze A: Material Hierarchy

... (zbytek starého changelogu)
```

---

### CLAUDE.md

**Před:**
```markdown
**Verze:** 2.10.0 (2026-01-24)
```

**Po:**
```markdown
**Verze dokumentu:** 2.11 (2026-01-24)
**GESTIMA verze:** 1.0.0
```

**Důvod:** CLAUDE.md je **dokument**, ne aplikace. Má vlastní verzování (2.11 = 11. update).

---

### README.md

**Před:**
```markdown
# GESTIMA 1.0 - CNC Cost Calculator
```

**Po:**
```markdown
# GESTIMA - CNC Cost Calculator

**Verze:** 1.0.0
**Datum:** 2026-01-24
**Status:** Production Ready
```

---

## Verzovací workflow (do budoucna)

### Při nové feature (MINOR)

1. **Implementace** - feature v kódu
2. **Inkrementovat verzi:**
   ```python
   # app/config.py
   VERSION: str = "1.1.0"  # was 1.0.0
   ```
3. **Update CHANGELOG.md:**
   ```markdown
   ## [1.1.0] - 2026-XX-XX
   ### Added
   - Nová feature XYZ
   ```
4. **Commit:**
   ```bash
   git add app/config.py CHANGELOG.md
   git commit -m "Bump version to 1.1.0 - Add feature XYZ"
   git tag v1.1.0
   git push origin main --tags
   ```

### Při bug fix (PATCH)

```python
# app/config.py
VERSION: str = "1.0.1"  # was 1.0.0
```

```markdown
## [1.0.1] - 2026-XX-XX
### Fixed
- Bug fix ABC
```

### Při breaking change (MAJOR)

```python
# app/config.py
VERSION: str = "2.0.0"  # was 1.x.x
```

```markdown
## [2.0.0] - 2026-XX-XX
### Breaking Changes
- Removed API endpoint XYZ
- Changed database schema ABC

### Migration Guide
1. Backup your database
2. Run migration: `alembic upgrade head`
3. Update API calls to use new endpoint
```

---

## Verzování dokumentů (best practices)

### Velký dokument (ARCHITECTURE.md, CLAUDE.md)

**Kdy inkrementovat:**
- **X.0 → (X+1).0** - kompletní přepis dokumentu
- **X.Y → X.(Y+1)** - nová sekce, významná změna

**Jak:**
```markdown
**Verze dokumentu:** 1.3 (2026-01-24)
**GESTIMA verze:** 1.0.0
**Changelog dokumentu:**
- 1.3: Přidána sekce "Verzování"
- 1.2: Aktualizace P2 requirements
- 1.1: Oprava ADR linků
- 1.0: První verze
```

### Malý dokument (ADR, audit reports)

**Verzování není nutné** - používá se datum.

**Důvod:** Tyto dokumenty jsou **imutabilní snapshot** rozhodnutí v čase.

---

## Checklist (před každým release)

- [ ] **App version** v `app/config.py` správná?
- [ ] **CHANGELOG.md** aktualizován?
- [ ] **Git tag** vytvořen? (`git tag vX.Y.Z`)
- [ ] **README.md** má správnou verzi?
- [ ] **CLAUDE.md** má správnou GESTIMA verze?
- [ ] Všechny **testy** prošly? (`pytest`)
- [ ] **Dokumentace** odpovídá kódu?

---

## Příklady (správně vs špatně)

### ✅ SPRÁVNĚ

**App version:**
```python
# app/config.py
VERSION: str = "1.2.3"  # ✅ Semantic Versioning
```

**CHANGELOG.md:**
```markdown
## [1.2.3] - 2026-02-01  # ✅ Stejné jako app version
### Fixed
- Bug ABC
```

**CLAUDE.md:**
```markdown
**Verze dokumentu:** 2.15 (2026-02-01)  # ✅ Document version (nezávislá)
**GESTIMA verze:** 1.2.3  # ✅ Odkaz na app version
```

---

### ❌ ŠPATNĚ

**App version:**
```python
# app/config.py
VERSION: str = "2.10.0"  # ❌ Kde je verze 2.0.0 - 2.9.0?
```

**CHANGELOG.md:**
```markdown
## [2.10.0] - 2026-01-24  # ❌ První release je 2.10? Co se stalo s 1.x?
```

**CLAUDE.md:**
```markdown
**Verze:** 2.10.0  # ❌ Není jasné, jestli je to app nebo doc version
```

---

## Reference

- **Semantic Versioning:** https://semver.org/
- **Keep a Changelog:** https://keepachangelog.com/
- **Git Tagging:** https://git-scm.com/book/en/v2/Git-Basics-Tagging

---

## Kdo verzuje a kdy

### Aplikace (app/config.py)

**KDO:**
- Developer při implementaci nové feature/bugfix
- AI asistent AUTOMATICKY při dokončení implementace

**KDY:**
```
Feature implementována → Inkrementuj VERSION v config.py → Update CHANGELOG.md → Git commit + tag
```

**DŮLEŽITÉ:** Version SE MĚNÍ při každé nové feature/bugfix před commitem!

---

### Dokumenty (všechny .md soubory)

**KDO:**
- Developer/AI při významné změně dokumentu

**KDY:**
- **Velká změna** (nová sekce, přepis): X.Y → X.(Y+1)
- **Malá změna** (oprava typo, doplnění): Nemusí se verzovat

**PRAVIDLO:** Pokud nejsi jistý, NEVERZUJ. Dokumenty jsou v Gitu, historie je zachována.

---

### CHANGELOG.md (speciální případ)

**KDO:**
- Developer/AI při KAŽDÉ změně v aplikaci

**KDY:**
- Při bump verze v `app/config.py`
- Před git commitem

**FORMÁT:**
```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- Feature ABC

### Fixed
- Bug XYZ
```

**KRITICKÉ:** CHANGELOG se VŽDY updatuje souběžně s `app/config.py`.

---

### ADRs (immutable)

**KDO:**
- Developer/AI při architektonickém rozhodnutí

**KDY:**
- Pouze při vytvoření (JEDNOU)

**NEVERZUJÍ SE** - jsou imutabilní snapshot rozhodnutí.

---

## Workflow: Bump Version (Kompletní návod)

### Scénář: Implementace nové feature

**Krok 1: Implementace**
```bash
# Napsat kód + testy
git add app/services/new_feature.py tests/test_new_feature.py
```

**Krok 2: Bump Version**
```python
# app/config.py
VERSION: str = "1.1.0"  # was 1.0.0 (MINOR bump - nová feature)
```

**Krok 3: Update CHANGELOG.md**
```markdown
## [1.1.0] - 2026-01-25

### Added
- New Feature XYZ v `app/services/new_feature.py`
  - Funkce A, B, C
  - 5 nových testů
```

**Krok 4: Commit + Tag**
```bash
git add app/config.py CHANGELOG.md
git commit -m "Bump version to 1.1.0 - Add feature XYZ"
git tag v1.1.0
git push origin main --tags
```

**Trvání:** 2-3 minuty

---

### Scénář: Bug fix

**Stejný postup, ale:**
```python
# app/config.py
VERSION: str = "1.0.1"  # was 1.0.0 (PATCH bump)
```

```markdown
## [1.0.1] - 2026-01-25

### Fixed
- Bug ABC v `app/routers/xyz.py` (issue #123)
```

---

### Scénář: Breaking change

**Stejný postup, ale:**
```python
# app/config.py
VERSION: str = "2.0.0"  # was 1.x.x (MAJOR bump)
```

```markdown
## [2.0.0] - 2026-02-01

### Breaking Changes
- Removed deprecated API endpoint `/api/old`
- Changed database schema: `parts.old_field` → `parts.new_field`

### Migration Guide
1. Backup your database: `python gestima.py backup`
2. Run migration: `alembic upgrade head`
3. Update API calls to use new endpoint
```

---

## Automatizace (pro AI asistenta)

**PRAVIDLO:** Po dokončení implementace AUTOMATICKY:

```
1. ✅ Zkontrolovat app/config.py VERSION
2. ✅ Aktualizovat CHANGELOG.md (přidat entry)
3. ✅ Navrhnout git commit message s novou verzí
4. ❌ NEPTAT SE uživatele ("Mám verzovat?") - prostě to udělat
```

**Příklad commit message:**
```
Bump version to 1.1.0 - Add Health Check endpoint

- Implementován GET /health endpoint
- Checks: DB, backups, disk space
- 7 nových testů
- Dokumentace: docs/NEXT-STEPS.md aktualizován
```

---

## Checklist (pro každý release)

- [ ] **App version** v `app/config.py` správná? (MAJOR.MINOR.PATCH)
- [ ] **CHANGELOG.md** má entry pro novou verzi?
- [ ] **Git tag** vytvořen? (`git tag vX.Y.Z`)
- [ ] **README.md** má správnou verzi? (pokud je to MAJOR release)
- [ ] **CLAUDE.md** má správnou GESTIMA verze? (pokud je to MAJOR release)
- [ ] Všechny **testy** prošly? (`pytest`)
- [ ] **Dokumentace** odpovídá kódu?

---

## FAQ

### Q: Musím verzovat každou malou změnu v dokumentu?
**A:** NE. Dokumenty verzuj pouze při významných změnách (nová sekce, přepis). Git má historii.

### Q: Kdy vytvořit ADR?
**A:** Při architektonickém rozhodnutí (viz CLAUDE.md sekce "Kdy vytvořit ADR").

### Q: Co když zapomenu aktualizovat CHANGELOG?
**A:** Oprav to v dalším commitu. Příklad: `git commit -m "docs: Update CHANGELOG for v1.1.0"`

### Q: Jak verzovat dokumenty jako CLAUDE.md?
**A:**
```markdown
**Verze dokumentu:** 2.12 (YYYY-MM-DD)
**GESTIMA verze:** 1.1.0
```
První číslo = doc version (nezávislá), druhé = app version (odkaz).

---

## Akce (HOTOVO)

- [x] Opravit `CHANGELOG.md` - squash 2.x.x → 1.0.0 ✅
- [x] Opravit `CLAUDE.md` - rozdělit app vs doc version ✅
- [x] Opravit `README.md` - přidat explicitní verzi ✅
- [ ] Vytvořit `/version` API endpoint (volitelné)
- [ ] Přidat version do footeru aplikace (UI) (volitelné)

---

**Verze dokumentu:** 1.1
**Datum:** 2026-01-24
**Autor:** Documentation Audit
**Status:** ✅ SCHVÁLENO & IMPLEMENTOVÁNO
