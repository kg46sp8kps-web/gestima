# ADR-053: Infor Data Readiness pro Přehled Zakázek, Plánování a Dílenský Terminál [ACCEPTED — BASELINE]

## Status
Přijato (baseline pro MVP řízení výroby v Gestimě).

## Kontext
Cíl je přesunout operativní řízení výroby do Gestimy:
- `Přehled zakázek` jako dispečerská obrazovka,
- jednoduché plánování/rovnání fronty mimo APS,
- dílenský terminál pro vykazování práce a materiálu.

Aby bylo možné navrhnout workflow bez slepých míst, byl proveden live extract Infor dat a ověřena dostupnost klíčových polí.

## Důkazy (vytěžená data)
Zdroje v repozitáři:
- `data/infor_live_extract_preview.json` (timestamp `2026-02-28T10:10:12Z`)
- `data/infor_live_dispatch_extract.json`
- `data/infor_live_coitems_extract.json`
- `data/infor_ido_info_preview.json`

Klíčová zjištění:
1. `SLCoitems`:
- extract `count=600`, `message_code=0`
- statusy: `O/P/Q/W/C/F` (`C/F` tvoří hotové řádky)
- vazba na VP je nekonzistentní:
  - `Job` vyplněn u 598/600 řádků (často interní/numerický identifikátor, ne vždy VP),
  - `CoitemJob` a `MOJob` jen 8/600.
- `SLCoitems` metadata obsahují `CoType`, `CoStat`, `Stat`, `CustNum`, `CoCustNum`.

2. `SLJobs`:
- v této instalaci je custom schema (`IteRybSLJobs`), část standardních properties není univerzálně dostupná.
- při dotazu na neexistující property vrací Infor `MessageCode=450` (bez HTTP chyby).

3. `SLJobRoutes`:
- je použitelný zdroj pro operace, WC, množství, stav (`Complete`, `QtyComplete`, `QtyScrapped`, `DerRybStav*`).
- obsahuje i nerelevantní typy/stavy pro dílnu (např. `Type=S/E`, `JobStat=W/F`) a musí se filtrovat dle use-case.

4. `IteCzTsdJbrDetails`:
- v této instanci se opakovaně chová jako detail/session view, ne stabilní primární zdroj dispečerské fronty.
- pro produkční čtení fronty je nutný kompatibilní fallback přes `SLJobRoutes`.

## Rozhodnutí
Pro MVP se zavádí explicitní data-kontrakt po doménách:

### A) Přehled zakázek (Dispečerský board)
Zdroje:
- primárně `SLCoitems`
- enrichment: `SLCustomers`, `SLJobs`, `SLJobRoutes`

Pravidla:
- defaultně pouze aktivní řádky `Stat IN (O,P,Q,W)`.
- hotové (`F`,`C`) pouze při přepnutí filtru `Zobrazit hotové`.
- nabídky/estimate se odfiltrují přes `CoType='R'` (pokud je pole dostupné).
- vazba zakázka ↔ VP je multi-candidate (ne pouze `CoitemJob/MOJob`), protože direct link je v datech nízký.

### B) Plánování (lightweight bez APS)
Zdroje:
- operační kapacita a sekvence z `SLJobRoutes`,
- termíny/zakázkový kontext ze `SLCoitems`,
- metadata VP z `SLJobs`.

Pravidla:
- Infor data jsou read-model; pořadí práce (priority, freeze, ruční přesuny) je authoritative v Gestimě.
- nové ready VP nejdou „naslepo na konec“; základní pořadí = due date + jednoduchý časový scoring + manuální override.
- neuvolněné VP jsou viditelné jako „zásobník“ (future lane), ale neblokují execution lane.

### C) Dílenský terminál
Zdroje:
- fronta/operace z `SLJobRoutes` (filtrované na výrobní operace),
- materiálové odvody přes custom `Ite*/IteCz*` flow (viz ADR-052).

Pravidla:
- modrá = pouze aktuálně rozpracovaná operace (`in_progress`), zelená = hotovo (`done`), jinak bez podbarvení.
- pro transakční zápis se nesmí použít jen raw read data; write musí jít přes ověřené SP workflow.

## Co je potřeba doplnit pro plánování (gap list)
Není ještě uzavřený plný datový kontrakt pro:
1. ready-flag VP (jednoznačný zdroj „material/production ready“),
2. not-ready reason (materiál/dokumentace/kooperace),
3. strojové kalendáře a dostupnost (pro přesnější průběžný čas),
4. audit trail změn fronty (kdo/co/kdy/proč).

Tyto body budou řešeny v Gestima overlay vrstvě (override/event log), nikoliv v Infor APS.

## Alternativy
1. Nechat řízení výroby plně v Infor APS.
- Zamítnuto: provozně se nepoužívá (nízká adherence fronty).

2. Používat jen přímé linky `CoitemJob`/`MOJob` jako jedinou vazbu.
- Zamítnuto: datově nedostatečné (v extraktu jen malá část řádků).

3. Přepsat vše na full finite-capacity engine hned v 1. fázi.
- Odloženo: vysoká složitost, neodpovídá požadavku na rychlé lightweight nasazení.

## Důsledky
Pozitivní:
- realistický baseline nad skutečně dostupnými daty,
- oddělení read-model (Infor) a dispatch rozhodování (Gestima),
- rychlá cesta k beta dispečerskému přehledu a navazující frontě.

Negativní:
- vazba zakázka ↔ VP není stoprocentně deterministická bez heuristik,
- schema variabilita mezi instalacemi vyžaduje fallback property sety,
- část plánovacích atributů musí vzniknout jako Gestima overlay data.

## Nesmíš
- brát `MessageCode=0` jako důkaz správného datového modelu bez validace polí,
- předpokládat, že `SLCoitems.Job` je vždy přímo výrobní příkaz,
- navrhovat frontu pouze podle Infor APS bez možnosti ručního dispečerského override.

## Další krok
Implementovat `dispatch_overlay` tabulky (`queue_overrides`, `dispatch_events`, `dispatch_notes`) a napojit je na nový planning workflow nad potvrzeným read-modelem z tohoto ADR.

