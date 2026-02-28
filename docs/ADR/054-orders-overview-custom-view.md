# ADR-054: Přehled zakázek — přechod na custom IDO IteRybPrehledZakazekView

## Status
Přijato (implementováno 2026-02-28).

## Kontext
Původní implementace `fetch_orders_overview` používala 5 nezávislých IDO volání:

| # | IDO | Účel | Record cap |
|---|-----|------|-----------|
| 1 | SLCoitems | Řádky zakázek | 10 000 |
| 2 | SLJobs | VP joby (item-matching) | 5 000 |
| 3 | SLJobRoutes | Operace/routing VP | 8 000 |
| 4 | SLCustomers | Název zákazníka | 5 000 |
| 5 | SLCos | Hlavička zakázky (CustNum) | 5 000 |

Problémy:
- **Chyběly blanket zakázky** (`CoType='B'`): starý filtr `CoType='R'` vynechával 23 řádků (4 zákazníci).
- **Pomalé**: 5 síťových round-tripů, celkově ~33 000 záznamů k načtení.
- **Komplexní client-side join**: VP matching přes Item kód, customer lookup přes 2 tabulky.
- **CustNum null na SLCoitems**: filtr zákazníka musel být client-side přes SLCos lookup.

## Rozhodnutí
Přejít na **`IteRybPrehledZakazekView`** — custom Infor IDO (SQL view), který již obsahuje všechna potřebná data pre-joinovaná na úrovni databáze.

### Struktura view (klíčová pole)

| Skupina | Pole | Popis |
|---------|------|-------|
| Zakázka | CoNum, CoLine, CoRelease, Stat | Identifikace řádku |
| Zákazník | CustNum, CustName, CustPo, CustShipName | Přímo na řádku (ne lookup) |
| Díl | Item, ItemDescription | Položka |
| Množství | QtyOrderedConv, QtyShipped, QtyOnHand, QtyWIP | Stav plnění |
| Termíny | DueDate, PromiseDate, ProjectedDate, ConfirmedDate | + RybDeadLineDate, RybCoOrderDate |
| VP Job | Job, Suffix, JobCount | Napojený výrobní příkaz |
| Operace | Wc01–Wc10 | Kódy pracovišť (flat) |
| Stav operací | Comp01–Comp10, Wip01–Wip10 | Dokončeno / rozpracováno |
| Materiál | Mat01–Mat03, MatComp01–03, MatWip01–03 | Materiálové vstupy + stav |
| Custom Ryb | Baleni, Regal, TotalWeight, PriceConv, RybCena | Specifická pole Kovorybka |

### Mapování stavu operací
```
Comp[N] == 1              → "done"
Wip[N] == 1 && Comp[N]==0 → "in_progress"
else                      → "idle"
```

### Filtr neaktivních VP
View vrací i historicky napojené dokončené joby (např. `14VP11/152`, Stat=C).
Heuristika: **VP se zobrazí jako kandidát jen pokud má routované operace** (Wc01 existuje).
Job bez operací = buď dokončený, nebo ještě nerouting → nezobrazovat.

## Výsledek

| Metrika | Před | Po |
|---------|------|----|
| API volání na Infor | 5 | **1** |
| Řádky zakázek (Stat=O) | 165 (jen CoType=R) | **188** (R+B) |
| Unikátní zakázky | 83 | **87** |
| Client-side join | Ano (5 indexů) | **Ne** |
| CustNum filtr | Client-side | **Server-side** |

## Propojení se systémem priorit

### Existující infrastruktura
Systém priorit již funguje přes tabulku `production_priorities`:

```
┌─────────────────────────┐
│   TileOrdersOverview    │
│  cycleRowTier() click   │
│  🔥 ⚡ —                │
└────────┬────────────────┘
         │ PUT /production-planner/tier
         │ { job, suffix, tier }
         ▼
┌─────────────────────────┐
│  production_priorities  │
│  infor_job  │ priority  │
│  infor_suf  │ is_hot    │
└─────────────────────────┘
```

### Linking key
Všechny systémy sdílejí klíč **`(Job, Suffix)`**:
- Přehled zakázek: `vp_candidates[].job` + `suffix`
- Fronta práce: `Job` + `Suffix` v queue itemu
- Production priorities: `infor_job` + `infor_suffix`

### Propojení s frontou práce (TODO)
Aktuálně fronta práce (`fetch_wc_queue`) **nečte** z `production_priorities`.
Pro řazení fronty dle urgence je potřeba:

1. Po načtení fronty z Inforu připojit priority z DB (join přes job+suffix)
2. Řadit: `is_hot` DESC → `priority` ASC → `OpDatumSt` ASC
3. Frontend: vizuální indikace urgentních operací ve frontě

Implementačně jde o ~20 řádků kódu v `fetch_wc_queue` / `fetch_machine_plan`.

## Konfigurace
```env
INFOR_CONFIG=LIVE   # Readonly čtení z live Inforu
```
Zápisy (POST transakce) zůstávají blokované v `workshop_router.py`.
