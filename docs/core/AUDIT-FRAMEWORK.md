# GESTIMA AUDIT FRAMEWORK

**Version:** 3.0 (2026-02-18) | **Maintained by:** Auditor Agent

---

## AUDIT TYPES

| Type | Trigger | Priority | Output |
|------|---------|----------|--------|
| POST-CLEANUP | 100+ LOC deleted | MANDATORY | `docs/audits/YYYY-MM-DD-cleanup-audit.md` |
| POST-FEATURE | Feature complete (3+ files) | MANDATORY | `docs/audits/YYYY-MM-DD-feature-audit.md` |
| POST-MIGRATION | Alembic migration | MANDATORY | `docs/audits/YYYY-MM-DD-migration-audit.md` |
| PRE-RELEASE | Before `git tag vX.Y.Z` | **BLOCKING** | `docs/audits/YYYY-MM-DD-pre-release-audit.md` |

**PRE-RELEASE audit je BLOCKING — zadny tag bez APPROVED audit.**

---

## BLOCKING CRITERIA (P0) — MUSI byt fixnuto pred taggem

| # | Issue | L-code |
|---|-------|--------|
| 1 | Security vulnerability (auth bypass, SQL injection, XSS) | — |
| 2 | `pytest` nebo `vitest` FAIL | — |
| 3 | `npm run build` FAIL | — |
| 4 | `alembic upgrade head` FAIL | — |
| 5 | `db.commit()` bez try/except | L-008 |
| 6 | FK bez `ondelete=` → orphaned records risk | — |
| 7 | Vue komponenta >300 LOC | L-036 |
| 8 | Secrets v kodu | L-042 |
| 9 | Smoke test FAIL (critical user path nefunguje) | — |
| 10 | API breaking change bez migracniho planu | — |
| 11 | Chybejici rollback plan pro MAJOR/MINOR release | — |
| 12 | `npm ci` / `pip install` FAIL na ciste instalaci | — |

---

## ANTI-PATTERN CHECKLIST (L-XXX)

Plny seznam: `docs/reference/ANTI-PATTERNS.md`

| Code | Check | Hook |
|------|-------|------|
| L-008 | Vsechny `db.commit()` v try/except/rollback | validate_edit.py |
| L-009 | Zadne hole typy — `Field()` s constraints | validate_edit.py |
| L-036 | Zadna Vue komponenta >300 LOC | validate_frontend.py |
| L-040 | .md soubory POUZE v `docs/` (ne v rootu) | validate_docs.py |
| L-042 | Zadne secrets/credentials v kodu | validate_edit.py |
| L-043 | Zadne bare `except:` nebo `except...pass` | validate_edit.py |
| L-044 | Zadne `print()`, `console.log()`, `debugger` | validate_edit.py + validate_frontend.py |
| L-049 | Zadny TypeScript `any` typ | validate_frontend.py |
| L-001 | Vypocty POUZE v Python services/, NE v JS | manual review |

---

## AUDIT CHECKLIST (15 oblasti)

### 1. Code Quality (vaha: 12%)
- [ ] Zadne orphaned imports po smazanych modulech
- [ ] Zadne Vue komponenty bez reference (`import` check)
- [ ] Zadne bloky >10 radku zakomentovaneho kodu
- [ ] Zadne duplicitni CSS (.btn, .badge) mimo `design-system.css`
- [ ] Zadne hardcoded barvy/spacing mimo CSS vars
- [ ] L-008 / L-009 / L-036 / L-042 / L-043 / L-044 / L-049 (viz tabulka vyse)

### 2. Test Coverage (vaha: 12%)
- [ ] Kazdy `app/routers/*_router.py` ma `tests/test_*_router.py`
- [ ] Kazdy `app/services/*_service.py` ma `tests/test_*_service.py`
- [ ] Happy path, 404/409/422 error responses, auth check pokryte
- [ ] `pytest` PASS, `vitest` PASS — 0 failures

### 3. Smoke Tests & Critical Paths (vaha: 10%)

Critical user paths ktere MUSI fungovat pred kazdym releasem:

| # | Path | Jak overit |
|---|------|-----------|
| 1 | Login → Dashboard | Prihlaseni, zobrazeni hlavni stranky |
| 2 | Part CRUD | Vytvorit dil → editovat → smazat |
| 3 | Quote flow | Vytvorit nabidku → pridat polozky → cenova kalkulace |
| 4 | Material lookup | Vyhledat material → prirazeni k dilu → cena spravna |
| 5 | Infor import | Import dat z Infor → data se zobrazi spravne |
| 6 | File upload/preview | Upload souboru → preview PDF → stahnuti |
| 7 | Technology generation | AI generovani operaci → spravne casy |

- [ ] Vsechny critical paths projdou manualne NEBO pres E2E test
- [ ] Zadny path nevyhazuje 500 error
- [ ] Spravna data se zobrazi po kazde operaci (ne stale/cached)
- [ ] Multi-user scenario: 2 uzivatele soucasne nekorumuji data

### 4. API Contract & Breaking Changes (vaha: 8%)

```bash
# Jak zjistit breaking changes:
# 1. Porovnej endpointy mezi tagi
git diff vPREV..HEAD -- app/routers/ | grep -E '(@router\.|def )'
# 2. Over ze frontend vola existujici endpointy
grep -r 'api/' frontend/src/api/ | sort
# 3. Over response modely
grep -r 'response_model=' app/routers/ | sort
```

- [ ] Zadny endpoint odstranen bez deprecation notice v predchozi verzi
- [ ] Vsechny nove/zmenene endpointy maji aktualizovane frontend API calls
- [ ] Response model zmeneny → frontend typy aktualizovane (`frontend/src/types/`)
- [ ] Query parametry zmenene → frontend volani aktualizovane
- [ ] Breaking changes explicitne vyznacene v CHANGELOG.md s migration guide
- [ ] Pro MAJOR release: migracni guide v `docs/guides/MIGRATION-vX.md`

### 5. Architecture (vaha: 8%)
- [ ] Nova architektonicka rozhodnuti maji ADR, `docs/ADR/README.md` aktualizovan
- [ ] Nove UI komponenty jako `*Module.vue`, NE `*View.vue`
- [ ] Business logika POUZE v `app/services/` (L-001)
- [ ] CSS tokeny: barvy pres `var(--color-*)`, spacing pres `var(--space-*)`

### 6. Security (vaha: 12%)
- [ ] Vsechny protected endpointy maji `get_current_user` / `require_role`
- [ ] Zadne plaintext passwords, zadny raw SQL (SQLAlchemy ORM)
- [ ] Zadne `v-html` s user input
- [ ] Zadne secrets v kodu ani git historii (L-042)
- [ ] CORS nastaveni spravne (ne `allow_origins=["*"]` v produkci)
- [ ] Rate limiting na auth endpointech aktivni
- [ ] Input sanitization na vsech user-facing endpointech

### 7. Performance (vaha: 6%)
- [ ] Zadne `await db.get()` v loopu (pouzij `selectinload`)
- [ ] FK sloupce maji index
- [ ] Large collections (>100 items) paginovane
- [ ] Vsechny I/O operace async

### 8. Database Integrity (vaha: 8%)
- [ ] `alembic upgrade head` PASS, linearni migration chain
- [ ] Vsechny `ForeignKey()` maji `ondelete="CASCADE|RESTRICT|SET NULL"`
- [ ] Partial unique index pro soft delete: `WHERE deleted_at IS NULL`
- [ ] Vsechny modely maji `created_at`, `updated_at`, `created_by`, `updated_by`

### 9. Upgrade Path & Data Migration (vaha: 8%)

- [ ] `alembic upgrade` z predchozi tagged verze PASS (ne jen `head`)
- [ ] Existujici data preziji migraci beze ztraty (testovat na kopii prod DB)
- [ ] Seed scripty kompatibilni s existujicimi daty (UPSERT, ne DELETE+INSERT)
- [ ] Defaultni hodnoty pro nove NOT NULL sloupce definovane v migraci
- [ ] Zpetna kompatibilita: stara verze frontend muze cist data z nove DB (min. read-only)

### 10. Rollback Plan (vaha: 4%)

Pro kazdy MAJOR/MINOR release MUSI existovat rollback plan:

```
Rollback plan sablona:
1. DETEKCE: Jak pozname ze release selhal? (metriky, logy, user reports)
2. ROZHODNUTI: Kdo rozhodne o rollbacku? (owner/team lead)
3. POSTUP:
   a. git checkout vPREV
   b. alembic downgrade -1 (pokud migrace ma downgrade)
   c. npm run build && python gestima.py run
   d. Overeni ze rollback funguje
4. DATA: Jsou data z nove verze kompatibilni se starou? Ztrati se neco?
5. KOMUNIKACE: Kdo informuje uzivatele?
```

- [ ] Rollback plan zdokumentovan v audit reportu
- [ ] Alembic migrace maji `downgrade()` implementovany (ne jen `pass`)
- [ ] Rollback testovan na staging/kopii (idealne)
- [ ] Recovery Time Objective (RTO) definovany: max X minut na rollback

### 11. Environment & Configuration (vaha: 4%)

- [ ] `.env.example` aktualizovan se vsemi potrebnymi promennymi
- [ ] Vsechny env vars maji fallback/default v `app/config.py`
- [ ] Zadne hardcoded URLs, porty, cesty — vse pres config
- [ ] Rozdily prod vs dev zdokumentovane (napr. DEBUG=false, CORS origins)
- [ ] `python gestima.py run` funguje na ciste instalaci bez manualnich kroku

### 12. Error Handling & Observability (vaha: 4%)

- [ ] Klicove operace logovane (import, kalkulace, auth, CRUD) pres `logging` modul
- [ ] Structured logging format: `logger.info("action", extra={"entity_id": id})`
- [ ] Konzistentni error response format: `{"detail": "message"}` nebo `{"detail": {"code": "X", "message": "Y"}}`
- [ ] Zadne tihe polknute chyby (`except: pass`)
- [ ] Health check endpoint (`/health` nebo `/api/health`) vraci status + verzi
- [ ] Startup logy: verze, DB stav, konfigurace (bez secrets)

### 13. Concurrency & Data Integrity (vaha: 4%)

- [ ] SQLite WAL mode aktivni (`PRAGMA journal_mode=WAL`)
- [ ] Zadne race conditions pri soubeznем zapisu (optimistic locking nebo DB-level constraints)
- [ ] Idempotentni operace tam kde je to potreba (import, seed)
- [ ] File upload: atomicky zapis (temp → rename, ne primo do cilove cesty)
- [ ] Zadne globalni mutable state v async kontextu

### 14. Dead Code & Unused Dependencies (vaha: 2%)

```bash
# Jak najit dead code:
# 1. Nepouzivane npm packages
npx depcheck
# 2. Nepouzivane Python imports
# (ruff check --select F401)
# 3. Nepouzivane API endpointy (definovane v backend, nikde nevolane z frontend)
grep -roh 'router\.\(get\|post\|put\|patch\|delete\).*"[^"]*"' app/routers/ | \
  sed 's/.*"\(.*\)"/\1/' | sort | while read ep; do
    grep -rq "$ep" frontend/src/ || echo "UNUSED: $ep"
  done
# 4. Nepouzivane DB tabulky/modely
grep -roh 'class \w*(Base)' app/models/ | sed 's/class \(.*\)(Base)/\1/' | while read m; do
    grep -rq "$m" app/routers/ app/services/ || echo "UNUSED MODEL: $m"
  done
```

- [ ] Zadne nepouzivane npm packages (`npx depcheck` — 0 unused)
- [ ] Zadne nepouzivane Python imports (`ruff check --select F401`)
- [ ] Zadne API endpointy ktere nikdo nevola
- [ ] Zadne DB modely/tabulky ktere nikdo necte ani nezapisuje
- [ ] Zadne nepouzivane Vue komponenty (definovane ale nikde neimportovane)
- [ ] Zadne nepouzivane TypeScript typy/interfaces

### 15. Build Reproducibility & Release Artifacts (vaha: 2%)

- [ ] `package-lock.json` commitnuty a aktualni (`npm ci` PASS)
- [ ] `requirements.txt` nebo `pyproject.toml` ma pinned verze
- [ ] Build je deterministicky: 2x `npm run build` → stejny output
- [ ] `app/config.py` VERSION odpovida planovane verzi
- [ ] Git tag format `vX.Y.Z` konzistentni
- [ ] Vsechny commity od posledniho tagu maji entry v CHANGELOG.md

### BONUS: Accessibility (informativni, neblocking)

- [ ] Keyboard navigation funguje na hlavnich modulech (Tab, Enter, Esc)
- [ ] Fokus indikator viditelny (ne skryty `outline: none`)
- [ ] Interaktivni elementy maji dostatecnou click area (min 44x44px)
- [ ] Kontrastni pomery min 4.5:1 pro text (WCAG AA)
- [ ] `aria-label` nebo `title` na icon-only buttonech

### BONUS: CHANGELOG Quality (informativni, neblocking)

- [ ] Kazdy commit od posledniho tagu ma odpovidajici CHANGELOG entry
- [ ] User-facing zmeny oddelene od internich (Added/Fixed/Changed vs Internal)
- [ ] Breaking changes maji `### Breaking Changes` sekci s migration guide
- [ ] Autori/kontributori zminen pokud je jich vic

---

## DEPENDENCIES (oblast 15 v checklistu)

- [ ] `npm audit --production` — 0 high/critical
- [ ] `pip-audit` — 0 high/critical
- [ ] Zadne GPL/AGPL dependencies (licence kompatibilita)
- [ ] Zadne deprecated packages s known vulnerabilities

---

## SCORING & VERDIKT

| Score | Status | Akce |
|-------|--------|------|
| 90-100 | EXCELLENT | APPROVED — immediate deploy |
| 75-89 | GOOD | APPROVED s minor warnings |
| 60-74 | ACCEPTABLE | Fix P1 issues pred deploy |
| <60 | FAILED | BLOCKED — fix P0 issues |

### Vahy (celkem 100%)

| Oblast | Vaha | Komentar |
|--------|------|----------|
| 1. Code Quality | 12% | Zakladni hygiena kodu |
| 2. Test Coverage | 12% | Automaticke overeni |
| 3. Smoke Tests | 10% | Funguje to realne? |
| 4. API Contract | 8% | Frontend↔Backend soulad |
| 5. Architecture | 8% | ADR, patterns, separace |
| 6. Security | 12% | Auth, XSS, secrets, CORS |
| 7. Performance | 6% | N+1, indexy, async |
| 8. Database Integrity | 8% | Migrace, FK, audit fields |
| 9. Upgrade Path | 8% | Data preziji upgrade |
| 10. Rollback Plan | 4% | Jak se vratit zpet |
| 11. Environment | 4% | Config, .env, defaults |
| 12. Observability | 4% | Logging, errors, health |
| 13. Concurrency | 4% | WAL, race conditions |
| 14. Dead Code | 2% | Cleanup, no bloat |
| 15. Build Reproducibility | 2% | Deterministicky build |
| Dependencies | 0% | Informativni (ale P0 pokud critical vuln) |
| Accessibility | 0% | Informativni bonus |
| CHANGELOG Quality | 0% | Informativni bonus |

---

## PRE-RELEASE AUDIT POSTUP

```
1. PRIPRAVA
   - Urcit predchozi tag: git describe --tags --abbrev=0
   - Urcit scope zmen: git log vPREV..HEAD --oneline
   - Urcit typ release: MAJOR / MINOR / PATCH

2. AUTOMATICKE KONTROLY (spustit vsechny)
   pytest tests/ -v
   cd frontend && npm run build && npm run type-check && npm run test
   alembic upgrade head
   npm audit --production
   npx depcheck

3. MANUALNI REVIEW (projit checklist oblasti 1-15)
   - Kazda oblast: projit checkboxy, zapsat nalezene issues
   - Issues kategorizovat: P0 (blocking) / P1 (fix pred deploy) / P2 (nice to have)

4. SMOKE TESTS (projit critical paths)
   - Spustit `python gestima.py dev`
   - Projit vsech 7 critical paths (viz sekce 3)
   - Zaznamenat PASS/FAIL pro kazdy path

5. ROLLBACK PLAN (pro MAJOR/MINOR)
   - Vyplnit rollback plan sablonu
   - Overit ze migrace maji downgrade()

6. SCORING
   - Obodovat kazdou oblast 0-100%
   - Vypocitat vazeny prumer
   - Urcit verdikt: EXCELLENT / GOOD / ACCEPTABLE / FAILED

7. REPORT
   - Zapsat do docs/audits/YYYY-MM-DD-pre-release-audit.md
   - Commit audit reportu PRED taggem
```

---

## HOOK REFERENCE

| Hook | Kdy bezi | Co kontroluje |
|------|----------|---------------|
| `validate_edit.py` | PreToolUse Edit/Write na `app/**/*.py` | L-008, L-009, L-042, L-043, L-044 |
| `validate_frontend.py` | PreToolUse Edit/Write na `*.vue`, `*.ts` | L-036, L-044, L-049 |
| `validate_docs.py` | PreToolUse Edit/Write na `*.md` | L-040 |
| `commit_guard.py` | PreToolUse Bash (git commit) | sensitive files, debug v diff, CHANGELOG |
| `definition_of_done.py` | Stop hook | testy, migrace, response_model |

**Hooks = exit 2 = BLOCKING. Dokumentace = "mel bys" = AI muze ignorovat.**

---

## POST-AUDIT AKCE

**APPROVED (score >= 75):** Fix P0 issues → re-audit → update CHANGELOG → commit audit report → `git tag -a vX.Y.Z`

**BLOCKED (score < 60):** Vytvor tickety pro P0 issues → fix → re-audit → iterate.

**Po kazdem auditu:** Nova anti-patterns → `docs/reference/ANTI-PATTERNS.md` | Opakovane issues → pridat do hooks | Learnings → `CLAUDE.local.md`.
