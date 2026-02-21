# Verzovaci politika GESTIMA

**Verze dokumentu:** 2.0 (2026-02-17)

---

## Format: MAJOR.MINOR.PATCH

| Typ | Kdy |
|-----|-----|
| **MAJOR** | Breaking changes — nekompatibilni API, DB migrace bez backward compatibility |
| **MINOR** | Nova funkce (backward compatible) |
| **PATCH** | Bug fix (backward compatible) |

---

## Kde se verze updatuje

| Soubor | Co se meni |
|--------|-----------|
| `app/config.py` | `VERSION: str = "X.Y.Z"` — jediny zdroj pravdy |
| `CHANGELOG.md` | Pridej entry `## [X.Y.Z] - YYYY-MM-DD` |
| `README.md` | Jen pri MAJOR release |
| `CLAUDE.md` | Jen pri MAJOR release |

**ADRs se neverzuji** — jsou imutabilni, pouzivaji datum.

---

## Bump workflow

```
1. Implementace kodu + testy
2. Zmen VERSION v app/config.py
3. Pridej entry do CHANGELOG.md
4. git add app/config.py CHANGELOG.md
5. git commit -m "Bump version to X.Y.Z - popis"
6. git tag vX.Y.Z
7. git push origin main --tags
```

### CHANGELOG format

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added / Fixed / Changed / Breaking Changes
- Popis zmeny
```

---

## Git tag pravidla

- Tag format: `vX.Y.Z` (s prefixem `v`)
- Tag se vytvari VZDY pri kazdem releasu (MAJOR + MINOR + PATCH)
- Push tagu: `git push origin main --tags`
- Tag se NESMAZE ani NEMENI po pushnuti

---

## Release checklist

- [ ] `app/config.py` ma spravnou verzi
- [ ] `CHANGELOG.md` ma novou entry
- [ ] Git tag `vX.Y.Z` vytvoren
- [ ] Vsechny testy prosly (`pytest`)
