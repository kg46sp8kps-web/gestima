# Auditní zpráva GESTIMA

## 1. Nález: Absence "State Machine" (Stavového stroje)

Aktuální modely umožňují libovolný CRUD (Create, Read, Update, Delete). V ERP systému je nepřípustné, aby se data měnila nekontrolovaně.

**Auditní riziko:** Uživatel změní parametry stroje u dílu, který je již ve výrobě nebo byl vyfakturován.

**Navržené řešení:** Implementace Workflow Engine na úrovni modelů. Entita Part a Batch musí mít definované stavy (např. DRAFT -> CALCULATED -> OFFERED -> ORDERED -> LOCKED).

**Důsledek:** Přechod mezi stavy spouští validace a "zmrazení" dat.

---

## 2. Nález: Časová nekonzistence referenčních dat (Price Decay)

Systém aktuálně počítá ceny "živě" z číselníků (materiály, stroje). Pokud se zítra zvedne cena hliníku, změní se i cena kalkulace vytvořené před měsícem.

**Auditní riziko:** Ztráta historické pravdy. Nemůžeme dohledat, proč byla nabídka před půl rokem taková, jaká byla.

**Navržené řešení:** Immutable Snapshot Pattern. Tabulka Batch nebude odkazovat na ID materiálu v číselníku, ale v momentě přepnutí do stavu OFFERED zkopíruje všechny relevantní ceny a parametry do své vlastní struktury (např. tabulka batch_snapshots).

---

## 3. Nález: Nedostatečná granularita transakčního logování (Audit Trail)

Máme AuditMixin, ale ten sleduje jen created_by a updated_at. ERP vyžaduje detailní "kdo, kdy, co přesně změnil".

**Auditní riziko:** Při chybě ve výpočtu nelze rekonstruovat, který technolog a kdy změnil řezné podmínky.

**Navržené řešení:** Implementace Event Sourcingu pro klíčové entity. Každá změna v kalkulaci (přidání operace, změna času) vytvoří záznam v tabulce audit_events s JSON payloadem původního a nového stavu.

---

## 🛠️ Navržený plán důkladného vývoje (Fáze: Systémové jádro)

Tento plán ignoruje UI a soustředí se na "mozek" systému:

### Krok 1: Centralizace výpočetní logiky (Pure Service Layer)

**Cíl:** Oddělit výpočty od databázových modelů.

**Akce:** Vytvoření CalculationEngine, který je stateless. Dostane objekt Part + Context (ceny, stroje) a vrátí neměnný CalculationResult. To umožní testování tisíců scénářů bez nutnosti DB.

### Krok 2: Robustní Schema Migration Policy

**Cíl:** ERP systémy žijí roky. Změna schématu nesmí rozbít historická data.

**Akce:** Nastavení striktního procesu migrací přes Alembic s povinnými "data-migration" skripty pro přepočet starých kalkulací na nové vzorce.

### Krok 3: Implementace "Unit of Work" Patternu

**Cíl:** Komplexní kalkulace zahrnuje zápis do 5+ tabulek. Selhání jedné nesmí nechat systém v nekonzistentním stavu.

**Akce:** Zapouzdření operací do UnitOfWork (SQLAlchemy Session management), který garantuje atomicitu i při složitých operacích napříč moduly.

### Krok 4: Definice API Kontraktů (Internal API)

**Cíl:** Příprava na budoucí integraci s jinými systémy (účetnictví, sklad).

**Akce:** Dokumentace všech vnitřních služeb pomocí Pydantic schémat, která slouží jako závazný kontrakt, nezávislý na tom, zda na druhé straně sedí HTMX nebo externí API.

---

## 🛑 Auditorovo varování (Oponentura)

Pokud se vydáme touto cestou "Důkladného vývoje", musíme přijmout fakt, že viditelný pokrok bude pomalý. Budeme budovat infrastrukturu, kterou běžný uživatel neuvidí, ale která zajistí, že GESTIMA za 2 roky nezkolabuje pod vlastní vahou.

**Otázka:** Souhlasíš s tím, že příštím krokem bude technický návrh "State Machine" a "Snapshotting" schématu v databázi, namísto práce na šablonách?
