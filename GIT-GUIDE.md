# Git Guide - Jednoduše a Prakticky

**Pro:** Vývojáře GESTIMA
**Čas:** 5 minut k pochopení

---

## 🎯 Co Je Git? (Jednou větou)

**Git = Google Drive pro kód** - ukládá verze, sdílí s kolegy, vrací změny zpět.

---

## 📚 Základní Pojmy

### Repository (Repo)
**= Projekt na GitHubu**

Tvůj projekt: `gestima`

### Commit
**= Uložená verze**

Jako "Save" ve Wordu, ale s popisem co jsi změnil.

```bash
git commit -m "feat: přidána nová funkce"
```

### Branch
**= Kopie projektu pro experimenty**

```
main ──────●──────●  (stabilní verze)
           │
           └──●──●  feature-xyz (tvoje kopie, experimentuješ)
```

### Tag
**= Značka verze**

```
main ──●────●─────●─────●
      v1.0  v1.1  v1.2  v1.6.0
```

### Push/Pull
**= Upload/Download na GitHub**

```bash
git push    # Upload tvých změn → GitHub
git pull    # Download změn z GitHubu → tvůj Mac
```

---

## 🚀 Denní Workflow (Co Děláš Každý Den)

### 1. Ráno - Stáhni Nejnovější Verzi

```bash
cd ~/Documents/__App_Claude/Gestima
git pull
```

**Co to dělá:** Stáhne změny z GitHubu (pokud jsi něco změnil jinde).

### 2. Během Dne - Pracuj Normálně

```bash
# Vyvíjej v editoru
# Změň soubory
# Testuj
python gestima.py test
```

**Git zatím nic nedělá** - jen ty měníš soubory.

### 3. Konec Dne - Ulož Změny

#### A) Podívej se co jsi změnil

```bash
git status
```

**Výstup:**
```
modified:   app/routers/parts_router.py
modified:   app/templates/parts/edit.html
```

#### B) Přidej změny do "nákupního košíku"

```bash
git add .
```

**Co to dělá:** Přidá **všechny** změněné soubory.

**Alternativa - přidej jen konkrétní soubor:**
```bash
git add app/routers/parts_router.py
```

#### C) Commit = Ulož s popisem

```bash
git commit -m "feat: přidána možnost filtrování parts"
```

**Formát commit message:**
```
feat: nová funkce
fix: oprava bug
docs: změna dokumentace
refactor: přepsání kódu (beze změny funkce)
test: přidání testů
```

#### D) Push = Upload na GitHub

```bash
git push
```

**Hotovo!** Změny jsou na GitHubu.

---

## 🔄 Kompletní Příklad (Celý Den)

```bash
# Ráno
cd ~/Documents/__App_Claude/Gestima
git pull

# Během dne
# ...vývoj...
python gestima.py test

# Večer
git status          # Co jsem změnil?
git add .          # Přidat vše
git commit -m "feat: přidán export do PDF"
git push           # Upload na GitHub

# Done!
```

---

## 🏷️ Verzování (Když Vydáváš Novou Verzi)

**Kdy:** Po větší feature, před deployem do produkce.

```bash
# Zkontroluj že vše je committed
git status  # Mělo by být "nothing to commit"

# Vytvoř tag
git tag v1.7.0

# Push tag
git push --tags

# GitHub → Releases → v1.7.0 se zobrazí
```

**Pojmenování verzí:**
```
v1.0.0  Major release (velká změna)
v1.1.0  Minor release (nová feature)
v1.1.1  Patch (bugfix)
```

---

## 🐛 Troubleshooting (Když Něco Nejde)

### Problém: "Your branch is behind origin/main"

**Důvod:** Někdo (nebo ty na jiném PC) pushoval změny.

**Fix:**
```bash
git pull
```

### Problém: "Conflict" při pull

**Důvod:** Ty i někdo jiný změnili stejný soubor.

**Fix:**
```bash
# Git ukáže konflikt v souboru (označený <<<<<<< a >>>>>>>)
# Otevři soubor, vyber správnou verzi, smaž značky
# Pak:
git add .
git commit -m "merge: vyřešení konfliktu"
git push
```

### Problém: Commitoval jsem špatně

**Fix - ještě jsi nepushoval:**
```bash
git reset --soft HEAD~1  # Vrátí poslední commit, soubory zůstanou změněné
# Oprav chybu
git add .
git commit -m "opravená zpráva"
```

**Fix - už jsi pushoval:**
```bash
# Udělej nový commit s opravou
git commit -m "fix: oprava předchozího commitu"
git push
```

### Problém: Smazal jsem soubor omylem

**Fix:**
```bash
git restore app/routers/parts_router.py  # Obnoví soubor
```

### Problém: Chci smazat všechny lokální změny

**Fix:**
```bash
git checkout -- .  # Zahodí VŠECHNY neuložené změny! Opatrně!
```

---

## 📖 Užitečné Příkazy

### Zobrazení

```bash
git status              # Co je změněno?
git log --oneline -10   # Posledních 10 commitů
git diff                # Co přesně jsem změnil? (před commit)
```

### Historie

```bash
git log --oneline --graph  # Vizuální strom commitů
git show <commit-hash>     # Detail konkrétního commitu
```

### Branches (Pokud Někdy Budeš Potřebovat)

```bash
git branch                    # Seznam branchí
git checkout -b feature-xyz   # Vytvoř novou branch
git checkout main             # Přepni na main
git merge feature-xyz         # Sluč feature do main
```

---

## ✅ Best Practices

### 1. Commituj Často

```
❌ 1× týdně velký commit (těžko se vrací změny)
✅ 5× denně malé commity (každá feature zvlášť)
```

### 2. Piš Srozumitelné Commit Messages

```
❌ "update"
❌ "fix stuff"
❌ "změny"

✅ "feat: přidán export do PDF"
✅ "fix: oprava výpočtu ceny při záporném množství"
✅ "docs: aktualizace README s novými příkazy"
```

### 3. Pull Před Push

```bash
# Vždy před pushem:
git pull
git push
```

Zabrání konfliktům.

### 4. Test Před Commit

```bash
python gestima.py test  # Testy prošly?
git add .
git commit -m "feat: xyz"
git push
```

---

## 🎓 Když Potřebuješ Víc

**Pro pokročilé:**
- [DEPLOYMENT.md](DEPLOYMENT.md) - Kompletní Git setup (SSH keys, GitHub, atd.)
- [Git Documentation](https://git-scm.com/doc) - Oficiální dokumentace

**Pro začátečníky:**
- Tento soubor stačí! ✅

---

## 💡 Cheat Sheet (Vytiskni a Přilep na Zeď)

```
┌─────────────────────────────────────────┐
│  GIT CHEAT SHEET                        │
├─────────────────────────────────────────┤
│  Denní workflow:                        │
│  1. git pull                            │
│  2. ...vývoj...                         │
│  3. git add .                           │
│  4. git commit -m "feat: xyz"           │
│  5. git push                            │
├─────────────────────────────────────────┤
│  Troubleshooting:                       │
│  git status        (co je změněno?)     │
│  git pull          (stáhni změny)       │
│  git restore file  (vrať soubor)        │
├─────────────────────────────────────────┤
│  Verzování:                             │
│  git tag v1.7.0                         │
│  git push --tags                        │
└─────────────────────────────────────────┘
```

---

## ❓ Otázky?

**Nerozumíš něčemu?** Přečti si tu sekci znovu, nebo se zeptej.

**Chceš víc detailů?** Otevři [DEPLOYMENT.md](DEPLOYMENT.md).

**Hodně štěstí!** 🚀
