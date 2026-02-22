# Gestima ERP Vision

> Strategický dokument. Kam Gestima směřuje a co všechno řeší reálný provoz CNC výrobní firmy.
> Vytvořeno: 2026-02-22. Aktualizovat při změně strategie.

## Positioning

**Gestima = specializované ERP pro CNC výrobce. Ne generický software.**

- Hluboká TPV/kalkulace (prvky, řezné podmínky, AI odhady) — 10× hlubší než Helios/Infor
- UX na míru CNC provozu — ne generické formuláře
- Integrace s Infor/Helios pro účetnictví, mzdy, majetek
- Postupné přebírání provozních funkcí z Inforu

### Architektura: Gestima = provoz, Infor/Helios = účetnictví

```
┌─────────────────────────────────────────────────────┐
│                    GESTIMA (primární)                │
│                                                     │
│  Nabídky → Objednávky → Výroba → Expedice          │
│  TPV, Kalkulace, Materiál, Sklad, Zákazníci         │
│                                                     │
│         ▼ push doklady       ▲ pull stavy           │
├─────────────────────────────────────────────────────┤
│              SYNCHRONIZAČNÍ VRSTVA                   │
│         (obousměrná, ne jen import)                  │
├─────────────────────────────────────────────────────┤
│              INFOR / HELIOS (sekundární)             │
│                                                     │
│  Účetnictví, DPH, Banka, Mzdy, Majetek             │
│  Fakturace (generování z Gestima dat)               │
│  Statutární reporting                               │
└─────────────────────────────────────────────────────┘
```

### Co kde žije — hranice systémů

| Oblast | Gestima (vlastník) | Infor/Helios (příjemce/vlastník) |
|---|---|---|
| Díly / artikly | Master | Přijímá sync |
| TPV / technologie | Výhradně | — |
| Kalkulace / ceny | Výhradně | — |
| Materiál / polotovary | Master (kmenová data + sklad) | Přijímá pohyby pro účtování |
| Zákazníci / dodavatelé | Master | Sync jako obchodní partnery |
| Nabídky | Výhradně | — |
| Objednávky (prodejní) | Master | Přijímá pro fakturaci |
| Objednávky (nákupní) | Master | Přijímá pro účtování |
| Výrobní příkazy | Master | Přijímá pro přehled |
| Sklad (pohyby) | Master | Přijímá pro účtování skladu |
| Expedice | Master | Podklady pro fakturaci |
| Fakturace | Push podklady → | Master (generuje faktury) |
| Účetnictví | Read-only dashboard ← | Master |
| Banka, DPH, mzdy | — | Výhradně |

---

## Kompletní mapa provozních potřeb

> Zdroj: analýza Helios iNuvio dokumentace vs. reálný CNC provoz.
> Každá oblast označena: ✅ máme | ⚠️ částečně | ❌ chybí | 🔌 řeší Infor

### 1. Zákazník pošle poptávku

| Potřeba | Stav | Poznámka |
|---|---|---|
| Fakturační adresa | ⚠️ | Máme 1 adresu, chybí rozlišení fakturační/dodací/korespondenční |
| Dodací adresa | ❌ | Zákazník často chce dodat jinam než fakturovat |
| Země zákazníka | ✅ | `country` na Partner (od v2.0) |
| Reverse charge (EU) | ❌ | Musíme vědět: EU plátce → 0% DPH |
| Kredit limit | ❌ | Blokace expedice při překročení |
| Měna zákazníka | ❌ | EUR/CZK — default měna per partner |
| Platební podmínky | ❌ | Net 30/60, způsob platby |
| Cenová úroveň / slevy | ❌ | Zákaznické ceny, množstevní slevy |
| ARES ověření IČO/DIČ | ❌ | Auto-validace proti registru |
| Nespolehlivý plátce DPH | ❌ | Ručíte za DPH pokud zaplatíte nespolehlivému! |
| Kontaktní osoby (více) | ❌ | Dnes jen 1 contact_person text |
| Dodací podmínky (Incoterms) | ❌ | EXW/FCA/DAP — kdo platí dopravu |
| Historie jednání | ❌ | CRM pipeline, kontaktní jednání |
| Bankovní spojení zákazníka | ❌ | Pro platby, zápočty |
| Jazyk komunikace | ❌ | Zákazník z DE chce nabídku/DL německy |

### 2. Nabídka

| Potřeba | Stav | Poznámka |
|---|---|---|
| Nabídka v cizí měně (EUR) | ❌ | Dnes jen CZK |
| Kurz + datum kurzu | ❌ | CZK/EUR k datu nabídky |
| DPH na položkách | ⚠️ | `tax_percent` na celé nabídce, ne per položka |
| DPH režim (standard/reverse/export) | ❌ | Závisí na zákazníkovi |
| Slevy (hlavička + položka) | ⚠️ | `discount_percent` na hlavičce, ne na položce |
| Doprava a balení | ❌ | Přirážka nebo samostatná položka |
| Platnost nabídky | ✅ | `valid_until` |
| Požadovaný termín dodání | ❌ | Kdy zákazník chce |
| Slíbený termín dodání | ❌ | Kdy slíbíme |
| Kontaktní osoba (naše) | ❌ | Kdo nabídku zpracoval / obchodník |
| Důvod zamítnutí | ❌ | Proč zákazník odmítl (learning) |
| Nabídka → objednávka | ❌ | Automatická konverze po schválení |

### 3. Prodejní objednávka (neexistuje)

| Potřeba | Stav | Poznámka |
|---|---|---|
| Celý model SalesOrder | ❌ | Za APPROVED nabídkou nic není |
| Číslo objednávky zákazníka | ❌ | Externí reference |
| Status workflow | ❌ | Potvrzeno → ve výrobě → připraveno → expedováno |
| Požadovaný/slíbený termín | ❌ | |
| Rezervace materiálu | ❌ | Blokace polotovarů na zakázku |
| Částečné plnění | ❌ | 100ks objednáno, posílám 60 + 40 |
| Měna + kurz k datu objednávky | ❌ | |
| Středisko / zakázka (accounting) | ❌ | Pro Infor účtování |
| Generování výrobních příkazů | ❌ | Objednávka → VP automaticky |
| Generování expedice | ❌ | |

### 4. Nákupní objednávka (neexistuje)

| Potřeba | Stav | Poznámka |
|---|---|---|
| Celý model PurchaseOrder | ❌ | |
| Výběr dodavatele z katalogu | ❌ | Dnes `supplier` = text na MaterialItem |
| Cena v EUR | ❌ | |
| Dodací podmínky | ❌ | Incoterms, doprava |
| Stav (odesláno → potvrzeno → doručeno) | ❌ | |
| Vazba na příjemku | ❌ | Kolik z objednávky přišlo |
| Vedlejší náklady (doprava, clo) | ❌ | Rozpouští se do ceny materiálu |

### 5. Příjem materiálu (příjemka)

| Potřeba | Stav | Poznámka |
|---|---|---|
| Příjemka jako doklad | ❌ | Infor přepíše `stock_available` |
| Vazba na nákupní objednávku | ❌ | |
| Skutečná nákupní cena | ❌ | Ne katalogová, ale co jsme zaplatili |
| Šarže / tavba | ❌ | Z atestu dodavatele |
| Vstupní kontrola kvality | ❌ | |
| Vedlejší náklady | ❌ | Doprava + clo → přirážka k ceně/kg |
| Umístění (regál, pozice) | ❌ | Kam fyzicky uloženo |
| Účetní kontace | 🔌 | Gestima pošle pohyb, Infor zaúčtuje |

### 6. Výdej materiálu do výroby

| Potřeba | Stav | Poznámka |
|---|---|---|
| Výdejka jako doklad | ❌ | |
| Vazba na výrobní příkaz | ❌ | |
| Oceňovací metoda (FIFO/průměr) | ❌ | Cena výdeje |
| Trasovatelnost (šarže → díl) | ❌ | |

### 7. Expedice

| Potřeba | Stav | Poznámka |
|---|---|---|
| Dodací list | ❌ | Právní doklad |
| Vazba na objednávku | ❌ | |
| Částečná expedice | ❌ | |
| Balicí list | ❌ | Rozměry, hmotnost zásilky |
| Doprava / přepravce | ❌ | |

### 8. Fakturace

| Potřeba | Stav | Poznámka |
|---|---|---|
| Faktura vydaná | 🔌 | Gestima pošle podklady, Helios/Infor generuje |
| DPH rekapitulace | 🔌 | Ale Gestima musí poslat správnou sazbu! |
| DUZP | 🔌 | Datum zdanitelného plnění = datum dodání |
| Datum splatnosti | 🔌 | Z platebních podmínek zákazníka |
| Zálohy | 🔌 | Evidence záloh, odpočet na faktuře |
| Dobropis | 🔌 | Opravný daňový doklad |
| Reverse charge | 🔌 | Gestima musí správně klasifikovat! |
| Penalizace / upomínky | 🔌 | |
| Kontrolní hlášení | 🔌 | Gestima musí poslat správný limit (A4/A5/B) |

### 9. Platby a pohledávky

| Potřeba | Stav | Poznámka |
|---|---|---|
| Saldo pohledávek | ❌/🔌 | Dashboard z Inforu nebo vlastní |
| Párování plateb | 🔌 | Infor/Helios |
| Kredit limit kontrola | ❌ | Gestima musí blokovat expedici |
| Zápočty | 🔌 | |

### 10. Legislativa / compliance

| Potřeba | Stav | Poznámka |
|---|---|---|
| ARES ověření | ❌ | Auto-validace IČO/DIČ |
| Nespolehlivý plátce DPH | ❌ | Ručení za DPH! |
| Zveřejněný bankovní účet | ❌ | Platba na nezveřejněný = ručení |
| Kontrolní hlášení podklady | ❌ | Správná klasifikace dokladů |
| Intrastat | ❌ | Nad 12M CZK/rok do EU = povinné |
| GDPR | ❌ | Zdroj osobních údajů |

### 11. Kvalita (QMS)

| Potřeba | Stav | Poznámka |
|---|---|---|
| Reklamace přijatá (od zákazníka) | ❌ | Evidence, řešení, náklady |
| Reklamace vydaná (dodavateli) | ❌ | Vadný materiál |
| Kontrolní plány | ❌ | Co měřit, jak, tolerance |
| Správa měřidel | ❌ | Kalibrace, platnost |
| Hodnocení dodavatelů | ❌ | Kvalita, termíny, ceny |
| Údržba strojů | ❌ | Plánovaná údržba |
| Nápravná opatření (CAPA) | ❌ | |
| FMEA | ❌ | Analýza rizik |
| Materiálové atesty (3.1/3.2) | ❌ | EN 10204 certifikáty |

### 12. Materiál / sklad

| Potřeba | Stav | Poznámka |
|---|---|---|
| Kmenová data materiálu | ✅ | MaterialGroup → PriceCategory → Item |
| Typ položky (materiál/výrobek/kooperace) | ❌ | |
| Měrná jednotka | ❌ | kg/m/ks |
| Více dodavatelů per materiál | ❌ | Dnes 1 text pole |
| Min/max zásoby | ❌ | Kdy objednat |
| Skladové pohyby (příjem/výdej/převod) | ❌ | Dnes jen `stock_available` |
| Oceňování (FIFO/průměr) | ❌ | |
| Šarže / LOT | ❌ | |
| Umístění (sklad, regál, pozice) | ❌ | |
| Blokace vadného materiálu | ❌ | |
| Inventura | ❌ | |

### 13. Výroba

| Potřeba | Stav | Poznámka |
|---|---|---|
| Výrobní příkaz | ❌ | Plánované (Infor import existuje) |
| Kapacitní plánování | ❌ | |
| Odvádění operací | ❌ | |
| Skutečné časy vs. plánované | ⚠️ | ProductionRecord (import z Inforu) |
| Kooperace (externí operace) | ⚠️ | coop_days/price na operaci, ale ne jako objednávka |
| BOM / kusovník | ❌ | |

---

## Fáze rozšiřování

### Fáze 1: Datový základ (prerekvizita)
Rozšíření existujících modelů o chybějící provozní pole.
- Partner: země, DPH režim, platební podmínky, měna, dodací adresa
- Part: typ položky, MJ
- MaterialItem: MJ, min/max, dodavatel jako FK
- Quote: měna, kurz, DPH per položka, dodací termíny

### Fáze 2: Objednávkový cyklus
- SalesOrder (nabídka → objednávka → expedice)
- PurchaseOrder (nákup materiálu)
- DeliveryNote (dodací list)

### Fáze 3: Skladové hospodářství
- StockMovement (příjem/výdej/převod/inventura)
- Warehouse (sklady)
- Oceňovací metody

### Fáze 4: Výroba (MES)
- ProductionOrder (výrobní příkazy)
- Kapacitní plánování
- Odvádění operací

### Fáze 5: BOM / PLM
- BOMItem (kusovník)
- Revize, ECO
- MRP (rozpad požadavků)

### Fáze 6: Kvalita
- Reklamace (přijaté/vydané)
- Kontrolní plány
- Hodnocení dodavatelů

### Fáze 7: Obousměrný sync
- Push do Inforu/Heliosu (objednávky, pohyby, podklady k fakturaci)
- Pull z Inforu (zaúčtované doklady, platby, kurzy)

---

## Helios benchmark

> Referenční srovnání s Helios iNuvio (public.helios.eu/inuvio/doc/cs/).
> Ne proto abychom kopírovali, ale abychom věděli co existuje.

### Helios moduly vs. Gestima pokrytí

| Helios modul | Stránek doc | Gestima | Strategie |
|---|---|---|---|
| Obchodní partneři a CRM | 25 | ⚠️ Partner basic | Rozšířit |
| Sklady | 41 | ❌ jen stock_available | Vlastní zjednodušený |
| Nákup a prodej | 30 | ❌ jen Quote | Vlastní |
| Fakturace | 25 | 🔌 read-only z Infor | Push podklady → Infor |
| Pokladna | ~20 | — | Nepotřebujeme |
| Banka | ~20 | — | Zůstává v Inforu |
| Účetnictví | ~40 | 🔌 read-only | Zůstává v Inforu |
| Mzdy + Personalistika | ~50 | — | Zůstává v Inforu |
| Výroba (TPV) | 103 | ✅ naše core | Hlubší než Helios |
| QMS | 28 | ❌ | Fáze 6 |
| Projektové řízení | ~15 | — | Nepotřebujeme |
| Doprava | ~15 | — | Zjednodušeně v expedici |
| Intrastat | ~10 | ❌ | Pokud >12M/rok do EU |
| Celní sklady | ~15 | — | Nepotřebujeme |
| Controlling | ~10 | ⚠️ Accounting dashboard | Rozšířit |

### Helios kmenová karta: 120+ polí — co potřebujeme

| Skupina polí | Helios | Gestima potřebuje | Nepotřebujeme |
|---|---|---|---|
| Identifikace (10) | Reg.č, název 1-4, skupina, sortiment | ~5 (máme) | Název 2-4 |
| MJ (8) | 4 MJ + převody | ~3 (uom + 1 převod) | MJ inventura/výstup |
| Rozměry (8) | š/v/h/objem/hmotnost/palety | ~5 (máme) | Palety, vrstvy |
| Záruky + QC (6) | Vstup/výstup/QC datum | 0 | Vše (ne spotřební) |
| Dodavatel (6) | Dodavatel/lhůta/MOQ/balení | ~4 | Balící množství |
| Typ položky (4) | Dílec/montáž/materiál/nářadí | ~1 enum | |
| Sklad + chování (6) | FIFO/umístění/šarže/blokace | ~3 | |
| Účetní konta (10) | 5 kont + souvislé náklady | ~1 (accounting_group) | Konkrétní účty |
| Ceníky + slevy (15) | Multi-úroveň, multi-měna | ~3 (máme vlastní) | Helios cenotvorba |
| Čárové kódy (4) | EAN, PLU | ~1 (možná později) | PLU |
| Clo + SD (15) | Nomenklatura, sazby, lihovar | ~1 (celní kód pro Intrastat) | Alkohol, SD |
| Pokladna (4) | PLU, body, voucher | 0 | Vše |
| DPH (4) | Vstup/výstup/PDP | ~1 (DPH skupina) | Obsolete pole |
| ADR (5) | Nebezpečné zboží | 0 | Vše |
| Obrázek (1) | 1 obrázek | 0 (máme FileRecord) | |

**Celkem: ~120 polí Helios → ~25-30 polí Gestima potřebuje → ~15 máme → ~10-15 chybí**

---

## Poznámky

- Tento dokument je živý — aktualizovat při každém strategickém rozhodnutí
- Konkrétní implementační detaily patří do ADR dokumentů
- Pořadí fází může se změnit podle obchodních priorit
