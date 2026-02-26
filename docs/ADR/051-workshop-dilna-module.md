# ADR-051: Gestima Dílna — Workshop iPad terminál [IN PROGRESS — PŘEPSÁNO po RE analýze]
> Archive: docs/ADR/archive/051-workshop-dilna-module.md — přečti pro KOMPLETNÍ detail (118 SP, workflow, IL důkazy)

## Rozhodnutí
iPad terminál pro dělníky: fronta práce z `IteCzTsdJbrDetails`, START/STOP seřízení+výroby přes `IteCzTsdUpdateDcSfcWrapperSp` (25 params), odvod kusů přes `IteCzTsdUpdateDcSfc34Sp` (20 params, poz.1=prázdný), machine transakce zvlášť.

## KRITICKÉ OPRAVY zjištěné RE analýzou (2026-02-26, 100% z IL bytecodu)

### Fronta práce
- IDO: **`IteCzTsdJbrDetails`** (NE SLJobRoutes!)
- Sort: `OpDatumSt ASC`, filtr per terminál přes `IteCzTsdBdFiltrySp`

### SFC34 SP — 20 params (poz.1 = PRÁZDNÝ STRING, NE TransType!)
```
0: @TEmpNum    1: ""(prázdný!)  2: @TJobNum   3: @TJobSuffix(Int16)
4: @TOperNum   5: @TcQtuQtyComp  6: @TcQtuQtyScrap  7: @TcQtuQtyMove
8: @THours     9: @TComplete  10: @TClose  11: @TIssueParent
12: @TLocation  13: @TLot  14: @TReasonCode  15: @SerNumList
16: @TWc  17: @Infobar(OUTPUT)  18: @TStroj  19: @TDatumTransakce("0")
```
**Tento SP je POUZE pro OdvodKusu (modul 01120)!**

### WrapperSp — 25 params (TransType na poz.3)
Pro: ZahajitPraci/Nastaveni, UkoncitNastaveni
`"", EmpNum, MultiJobFlag, TransType(1/2/3), Job, Suffix, OperNum, "", "", "", "0","0","0","","","","","","", SourceModul, IdMachine, ResId, "0", Mode, Infobar(OUTPUT)`

### UkoncitPraci: `IteCzInsWrapperDcsfcUpdateSp` + `IteCzTsdUpdateDcSfcMchtrxSp`
### Machine transakce: `IteCzTsdUpdateMchtrxSp` VŽDY souběžně se Start/Stop

## State Machine (opravená)
```
ZahajitNastaveni → WrapperSp(TransType="1") + MchtrxSp
UkoncitNastaveni → WrapperSp(TransType="2") + MchtrxSp
ZahajitPraci     → WrapperSp(TransType="3") + MchtrxSp + AsdStartJobSp
UkoncitPraci     → InsWrapperDcsfcUpdateSp + DcSfcMchtrxSp + DcJmcSp
OdvodKusu        → SFC34Sp(20params, poz.1="")
```

## Klíčové soubory
- `app/services/workshop_service.py` — _build_sfc34_params() **NESPRÁVNĚ: 18 params, poz.1=TransType**
- `app/routers/workshop_router.py` — 6 endpointů (fronta z SLJobRoutes → ŠPATNĚ)
- `app/models/workshop_transaction.py` — WorkshopTransaction model + schemas
- `frontend/src/stores/workshop.ts` — startTimer, stopTimer (posílají na SFC34 → ŠPATNĚ)
- Migrace HEAD: `wk004_dilna_setup_trans_types`

## Co CHYBÍ (po RE analýze)
1. Fronta: přepsat na `IteCzTsdJbrDetails`
2. Start/Stop: přepsat na WrapperSp (25 params)
3. SFC34: opravit 20 params (poz.1="", +@TStroj, +@TDatumTransakce)
4. Machine transakce: přidat `IteCzTsdUpdateMchtrxSp` souběžně
5. UkoncitPraci: přepsat na InsWrapperDcsfcUpdateSp
6. IteCzTsdInitParmsSp: přidat načtení stavu před UkoncitPraci
7. Validace: ValidateEmpNum, ValidateJob, ValidateOperNum, ValidateMachine
8. Výdej materiálu: modul 01140 (ProcessJobMatlTransDcSp)
9. Admin UI pro infor_emp_num
10. Backend testy

## Nesmíš
- Posílat TransType na pozici 1 v SFC34 — PRÁZDNÝ STRING!
- Posílat Start/Stop přes SFC34 — správně WrapperSp
- Používat SLJobRoutes pro frontu — správně IteCzTsdJbrDetails
- Posílat na LIVE Infor (403 blokováno)
- Parsovat job čísla z URL path (lomítka → 404)
