# GIT-GUIDE v2.0

## Commit Message Format

```
feat:     nova funkce
fix:      oprava bugu
refactor: prepis kodu (bez zmeny funkce)
docs:     dokumentace
test:     testy
chore:    build, deps, config
```

Priklady:
```
feat: pridana moznost filtrovani parts
fix: oprava vypoctu ceny pri zapornem mnozstvi
```

Pravidla:
- Kratke, vystizne (do 72 znaku)
- V cestine nebo anglictine — konzistentne v projektu
- Malymi pismeny po dvojtecce

---

## Branch Strategy

```
main          — stabilni, deployovatelna verze VZDY
feature/xyz   — nova feature (vetvi z main, merge zpet)
fix/xyz       — bugfix (vetvi z main)
```

Workflow pro feature:
```bash
git checkout -b feature/technology-builder
# ...vyvoj, testy...
git merge main             # sync pred merge
git checkout main
git merge feature/xyz
git branch -d feature/xyz
```

Primo do main: hotfixes, male zmeny (1-2 soubory).

---

## Verzovani (Git Tags)

Semantic versioning: `MAJOR.MINOR.PATCH`

| Typ | Kdy |
|-----|-----|
| `v2.1.0` | Nova feature (minor) |
| `v2.1.1` | Bugfix (patch) |
| `v3.0.0` | Breaking change (major) |

```bash
git tag v2.1.0
git push --tags
```

Tag vzdy po commitu na main, pred deployem do produkce.

---

## Uzitecne prikazy

```bash
git status                  # co je zmeneno
git log --oneline -10       # poslednich 10 commitu
git diff                    # co presne jsem zmenil
git restore <file>          # vrat soubor na posledni commit
git reset --soft HEAD~1     # vrat posledni commit (soubory zustaji)
```
