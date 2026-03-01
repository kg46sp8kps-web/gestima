# ADR-051: Gestima Dílna — Workshop Terminál [FULL REVERSE ENGINEERING — 2026-02-26]

> Status: IN PROGRESS — backend implementován, CHYBY zjištěny RE analýzou
> Revize: 2026-02-26 (po kompletní IL bytecode analýze InduStream.Forms.Std.dll)
>
> [!WARNING]
> Tento archivní dokument obsahuje historický stav poznání k 2026-02-26.
> Pro závazný manuální write flow používej:
> `docs/ADR/051-workshop-dilna-module.md` + `uploads/indu/industream-ido-mapping-verified.md`.
> Některé body zde (zejména stop flow/JMC návaznosti, near-atomic potvrzení zápisu a START/STOP guardrails) byly 2026-02-28 až 2026-03-01 zpřesněny podle nového IL důkazu a integračních incidentů.

---

## Kontext

Dělníci potřebují iPad terminál pro:
- Zobrazení fronty práce (filtr pracoviště → operace s plánem od/do + počet kusů)
- Start/Stop seřízení a výroby → sync do Inforu
- Odvod kusů, zmetků, odpracovaného času
- Výdej materiálu

Gestima funguje jako middleware: čte z Inforu IDO API, ukládá transakce lokálně, odesílá přes SP.

---

## KOMPLETNÍ ZJIŠTĚNÍ Z REVERSE ENGINEERINGU (100% z IL bytecodu)

### Zdroje pro analýzu
- `uploads/indu/InduStream/Test/Bin/InduStream.Forms.Std.dll` — VB.NET, .NET 4.7.1
- `uploads/indu/InduStream/Test/Bin/InduStream.Shared.dll`
- `uploads/indu/InduStream/Test/Bin/Config.ini`

### Config.ini
```ini
Server=192.168.1.17, Port=7505 (ION API), URL=http://192.168.1.17:8505
Language=1029 (čeština), AutoLogon=1, NoUpdate=0
```

---

## 1. FRONTA PRÁCE — IDO a pole

### IDO: `IteCzTsdJbrDetails` (NE SLJobRoutes!)
- **Default filtr**: `1 = 1` (vše — filter se načítá z DB terminalu)
- **Default sort**: `OpDatumSt ASC` (datum startu operace vzestupně)
- **Filtry per terminál**: `IteCzTsdBdFiltrySp` s `G(gvPcName)` — dle pracoviště, oddělení, hnízda, skupiny zdrojů

### Sloupce gridu (`PlanPrace - Grid`):
| Sloupec | Popis |
|---|---|
| `colJob` | Číslo výrobního příkazu |
| `colDil` | Díl (Item) |
| `colNazev` | Název dílu |
| `colOpDatumSp` | Datum splnění operace |
| `colOpDatumSt` | Datum startu operace |
| `colOper` | Číslo operace |
| `colZdroj` | Zdroj (Resource) |
| `colDerZbyva` | Zbývající kusy (derived) |
| `colVpMnoz` | Množství VP (Released Qty) |
| `colDnyZpoz` | Dny zpoždění |
| `colPriority` | Priorita |
| `colMajitel` | Majitel (Owner) |
| `colDerOperator` | Operátor (derived) |
| `colSkupina` | Skupina |
| `colSuffix` | Suffix |
| `colPtr` | RowPointer |
| `colState` | Stav (labor) |
| `colStateAsd` | Stav ASD (stroj) |
| `colPlanFlag` | Příznak plánu |
| `colStred` | Středisko |
| `colLzeDokoncit` | Lze dokončit |
| `colDoba` | Doba |
| `colKusy` | Kusy |
| `colZasobnikDen` | Zásobník (dny) |
| `colEmpNum` | Číslo zaměstnance |
| `colStartDate` | Datum zahájení |
| `colWc` | Pracoviště |
| `colData1, colData2, colData3` | Uživatelsky definovatelné sloupce |

### Detaily operace po kliknutí (z `IteCzTsdJbrDetails`):
- `OperNum`, `WcDesc`, `QtyReceived`, `QtyComplete`, `QtyMoved`, `QtyScrapped`
- `JrtQtyReceived`, `JrtQtyComplete`, `JrtQtyMoved`, `JrtQtyScrapped`
- `IteCzDept`, `IteCzCntrlPointDesc`

### Parsování Job+Suffix+OperNum:
- Pole `vJobSuffixOperNum` se parsuje přes split pomocí `gvJobSuffixSeparator` a `gvJobSuffixOperNumSeparator`

---

## 2. WORKFLOW — PŘIHLÁŠENÍ

### Sekvence přihlášení:
```
1. Zadání EmpNum (nebo RFID → IteCzInsGetRFIDEmpNumSp)
2. IteCzTsdValidateEmpNumDcSfcSp → vrací RV(vMultiJobFlag), V(vEmpName)
3. Kontrola duplicitního přihlášení (prompt ANO/DOTAZ)
4. IteCzInsLoadModuleSp → vrací RV(vResId), RV(vIdMachine), RV(vModule)
5. IteCzAsdLoginLogoutEmployeeSp (ASD modul)
6. IteCzInSInitDefCompParmsSp (přes IDO IteCzTsdStd) → všechny globální parametry:
   - vSeparator, vJobSuffixSeparator, vJobSuffixOperNumSeparator
   - vWhse, vPraceNaViceVP, vStartStroje, vKonecStroje, vStartPrace
   - vPovolitPrekroceniCasOper, vPovolitViceKusuNaOper
   - vExpandSerial, vExpandLot
   - vProCasPouzijOdvodKusuACasu, vPridatVyjimky, vHotoveOperace
   - vZobrazitVydejNaVP, vZobrazitPrevodNV
   - vAutoOznaceniRadku, vMnozstviPresunuRizenoNO, vPokracovatSPrihlasZam
7. IteCzTsdParamsSp → RV(vSkladovaTransakceVp)
8. IteCzTsdGetUserNameSp → RV(vUser)
9. IteCzTsdBdFiltrySp(G(gvPcName)) → filtry terminalu
10. Načtení IteCzTsdJbrDetails (fronta práce)
```

---

## 3. SP PRO ZÁPIS — PŘESNÉ POŘADÍ (IL bytecode, 100% jistota)

### A) `IteCzTsdUpdateDcSfc34Sp` — 20 parametrů
**Použití: POUZE pro odvod kusů (Module_01120 OdvodKusu)**
**NIKOLI pro Start/Stop!**

| Index | Parametr | V() notace | Datový typ | Default |
|---|---|---|---|---|
| 0 | @TEmpNum | G(gvEmpNum) | String | — |
| **1** | **(PRÁZDNÝ!)** | **""** | **String** | **""** |
| 2 | @TJobNum | V(vJob) | String | — |
| 3 | @TJobSuffix | V(vSuffix) | **Int16** | — |
| 4 | @TOperNum | V(vOperNum) | String | — |
| 5 | @TcQtuQtyComp | V(vQtyComplete) | Decimal | 0 |
| 6 | @TcQtuQtyScrap | V(vQtyScrapped) | Decimal | 0 |
| 7 | @TcQtuQtyMove | V(vQtyMoved) | Decimal | 0 |
| 8 | @THours | V(vHrs) | Decimal | 0 |
| 9 | @TComplete | V(vOperCompleteFlag) | String | "0" |
| 10 | @TClose | V(vJobCompleteFlag) | String | "0" |
| 11 | @TIssueParent | V(vIssueParentFlag) | String | "0" |
| 12 | @TLocation | V(vLoc) | String | "" |
| 13 | @TLot | V(vLot) | String | "" |
| 14 | @TReasonCode | V(vReasonCode) | String | "" |
| 15 | @SerNumList | V(vSerNumList) | String | "" |
| 16 | @TWc | V(vWc) | String | — |
| 17 | @Infobar | RV(vInfoBar) | String | "" (OUTPUT) |
| 18 | **@TStroj** | **V(vStroj)** | String | "" |
| 19 | **@TDatumTransakce** | **V(vDatumTransakce)** | String | "0" |

**KRITICKÉ**: Pozice 1 je PRÁZDNÝ STRING — TransType se do tohoto SP NEPOSÍLÁ!

---

### B) `IteCzTsdUpdateDcSfcWrapperSp` — 25 parametrů
**Použití: ZahajitPraci (01100), ZahajitNastaveni (01110), UkoncitNastaveni (01111)**

| Index | Parametr | Hodnota |
|---|---|---|
| 0 | (prázdný) | "" |
| 1 | EmpNum | V(vEmpNum) |
| 2 | MultiJobFlag | V(vMultiJobFlag) |
| **3** | **TransType** | **"1"/"2"/"3" (literál dle akce)** |
| 4 | JobNum | V(vJob) |
| 5 | JobSuffix | V(vSuffix) |
| 6 | OperNum | V(vOperNum) |
| 7 | QtyComplete | "" (prázdné pro Start) |
| 8 | QtyScrap | "" |
| 9 | QtyMoved | "" |
| 10 | Complete | "0" |
| 11 | Close | "0" |
| 12 | IssueParent | "0" |
| 13-16 | Location/Lot/ReasonCode/SerNumList | "" |
| 17 | Wc | "" |
| 18 | (prázdný) | "" |
| 19 | SourceModul | V(vSourceModul) = "01100"/"01110"/"01111" |
| 20 | IdMachine | G(gvIdMachine) |
| 21 | ResId | G(gvResid) |
| 22 | (flag) | "0" |
| 23 | Mode | V(vMode) |
| 24 | Infobar | RV(vInfoBar) (OUTPUT) |

**TransType mapování:**
- `"1"` = ZahajitNastaveni (setup_start)
- `"2"` = UkoncitNastaveni (setup_end)
- `"3"` = ZahajitPraci (start výroby)

---

### C) `IteCzInsWrapperDcsfcUpdateSp` — pro UkoncitPraci (01101)
Volán při ukončení práce s odvody. Má jiný počet parametrů (31 slotů dle IL).

### D) `IteCzTsdUpdateMchtrxSp` — machine transakce (VŽDY souběžně)
Voláno SOUBĚŽNĚ se všemi labor SP při Start/Stop.
Parametry: `V(vWc)`, `V(vStroj)`, `V(vOldEmpNum)`

### E) `IteCzTsdUpdateDcSfcMchtrxSp` — machine transakce pro UkoncitPraci

---

## 4. WORKFLOW KROK ZA KROKEM

### ZahajitSeřízení (modul 01110):
```
1. IteCzTsdValidateEmpNumDcSfcSp
2. IteCzTsdValidateMultiJobDcSfcSp → RV(vMultiJobFlag)
3. IteCzTsdValidateJobSp → RV(vJobSuffix), RV(vSuffix), RV(vItem)
4. IteCzTsdValidateOperNumSp
5. IteCzTsdValidateOperNumMachineSp → RV(vStroj), RV(vWc)
6. IteCzTsdUpdateDcSfcWrapperSp (TransType="1", SourceModul="01110")
7. IteCzTsdUpdateMchtrxSp (machine transakce zvlášť!)
```

### UkončitSeřízení (modul 01111):
```
1. Validace (emp, multi-job, job, oper)
2. IteCzTsdNormHSp → RV(vNormHrs), RV(vPrekroceniHrsFlag)
3. IteCzTsdIsMinuteSp + IteCzTsdMinutesSp → konverze
4. IteCzTsdUpdateDcSfcWrapperSp (TransType="2", SourceModul="01111")
5. IteCzTsdUpdateMchtrxSp
```

### ZahajitPráci (modul 01100):
```
1. Validace (emp, multi-job, job, oper)
2. IteCzTsdJobAvailableQtySp → dostupné kusy
3. IteCzTsdNormHSp → normované hodiny
4. IteCzTsdValidateOperNumMachineSp → vStroj, vWc
5. IteCzTsdUpdateDcSfcWrapperSp (TransType="3", SourceModul="01100")
6. IteCzTsdUpdateMchtrxSp (labor+machine)
7. IteCzAsdAddJobSp + IteCzAsdStartJobSp (ASD modul)
8. IteCzTsdBdSetKapacityStatesSp (update stavu v gridu)
```

### UkončitPráci + odvod (modul 01101):
```
1. Validace (emp, multi-job, job, oper, reason code)
2. IteCzTsdInitParmsSp → STAV POSLEDNÍ TRANSAKCE Z INFORU:
   - vLastTransType, vLastJob, vLastSuffix, vLastOperNum
   - vNormHrs, vCanCompleteHrs, vProcessedHrs, vExceedHrsFlag
   - vLotTracked, vSerialTracked, vLoc, vClosePrompt
   - vLastOperNumInJob, vZdrojStroj, vLastTransMchtrxType
3. Lot/Serial tracking (pokud je nastaveno)
4. IteCzInsWrapperDcsfcUpdateSp (labor odvod)
5. IteCzTsdUpdateDcSfcMchtrxSp (machine transakce)
6. IteCzTsdUpdateDcJmcSp (material consumption)
7. IteCzAsdGetQtyCompleteSp (ASD update)
```

### OdvodKusů (modul 01120, STANDALONE):
```
→ IteCzTsdUpdateDcSfc34Sp (20 params, pozice 1 = PRÁZDNÝ)
→ V(vTransType) je nastaven na "4" PŘED voláním, ale do SP se NEPOSÍLÁ
```

---

## 5. VÝDEJ MATERIÁLU (modul 01140, SAMOSTATNÝ krok)

```
IDO pro materiál: IteCzTsdSLJobMatls (filtr Job+Suffix+OperNum)
SP sekvence:
1. IteCzTsdCLMGetJobMaterialSp → seznam materiálů
2. IteCzTsdControlBFJobmatlItemSp → BF kontrola
3. IteCzTsdValidateItemDcJmcSp → vrací vQtuReq, vQtuIssue
4. IteCzTsdValidateQtyDcJmcSp → validace množství
5. IteCzTsdValidateLotDcJmcSp / IteCzTsdValidateSerNumSp → lot/SN
6. IteCzTsdProcessJobMatlTransDcSp → PROVEDENÍ VÝDEJE
7. IteCzTsdUpdateDcJmcSp → finální update

Backflush: gvZobrazitVydejNaVP + vIsMatlBackflush → automatický výdej při odvodu
```

---

## 6. MULTI-STROJ vs MULTI-VP

**NENÍ multi-stroj.** Je to **multi-VP** (více výrobních příkazů na 1 stroji):
- `gvPraceNaViceVP` — globální flag "práce na více VP"
- `IteCzTsdValidateMultiJobDcSfcSp` → validuje multi-VP flag
- 1 terminál = 1 stroj/resource (nastaveno v `IteCzInsLoadModuleSp`)
- Manning/dělení času operátora je MIMO InduStream — Infor LN si to dělí sám

---

## 7. STAVY TRANSAKCÍ V INFORU

### `IteCzTsdInitParmsSp` — "co Infor ví"
Po každém zahájení/ukončení Infor ukládá stav. `IteCzTsdInitParmsSp` při UkoncitPraci vrací:
- `vLastTransType` — typ poslední transakce (1/2/3/4)
- `vNormHrs` / `vCanCompleteHrs` / `vProcessedHrs` — normovane/možné/odpracované hodiny
- `vExceedHrsFlag` — překročení normovaných hodin
- `vLastOperNumInJob` — poslední operace (pro detekci zakončení)
- `vClosePrompt` — prompt pro uzavření VP
- `vLotTracked` / `vSerialTracked` — požadavky na sledování šarže/SN

---

## 8. CO JE ŠPATNĚ V NAŠÍ IMPLEMENTACI

| Chyba | Aktuální stav | Správně |
|---|---|---|
| Fronta práce IDO | `SLJobRoutes` | `IteCzTsdJbrDetails` |
| Počet params SFC34 | 18 | **20** (chybí @TStroj, @TDatumTransakce) |
| Pozice 1 SFC34 | `_trans_type_code()` | **""** (prázdný string!) |
| Start/Stop SP | SFC34 | **WrapperSp** (25 params) |
| UkoncitPraci SP | SFC34 | **IteCzInsWrapperDcsfcUpdateSp + mchtrx** |
| Machine transakce | neexistuje | `IteCzTsdUpdateMchtrxSp` souběžně |
| Validace před zápisem | žádná | ValidateEmpNum, ValidateJob, ValidateOperNum, ValidateMachine |
| Načtení stavu | žádné | `IteCzTsdInitParmsSp` při UkoncitPraci |
| Výdej materiálu | neimplementován | modul 01140 s ProcessJobMatlTransDcSp |

---

## 9. KOMPLETNÍ SEZNAM SP (118 celkem v Std.dll)

**Pro dílnu kritické:**
| SP | Kdy |
|---|---|
| `IteCzTsdUpdateDcSfc34Sp` | OdvodKusu (20 params, poz.1=prázdný) |
| `IteCzTsdUpdateDcSfcWrapperSp` | ZahajitPraci/Nastaveni, UkoncitNastaveni (25 params) |
| `IteCzInsWrapperDcsfcUpdateSp` | UkoncitPraci (INS wrapper) |
| `IteCzTsdUpdateMchtrxSp` | Machine transakce (souběžně) |
| `IteCzTsdUpdateDcSfcMchtrxSp` | Machine transakce pro UkoncitPraci |
| `IteCzTsdUpdateDcJmcSp` | Material consumption |
| `IteCzTsdProcessJobMatlTransDcSp` | Výdej materiálu |
| `IteCzTsdInitParmsSp` | Načtení stavu posl. transakce z Inforu |
| `IteCzTsdValidateEmpNumDcSfcSp` | Validace zaměstnance |
| `IteCzTsdValidateJobSp` | Validace VP |
| `IteCzTsdValidateOperNumSp` | Validace operace |
| `IteCzTsdValidateOperNumMachineSp` | Validace operace + stroj → vStroj, vWc |
| `IteCzTsdValidateMultiJobDcSfcSp` | Validace multi-VP |
| `IteCzTsdJobAvailableQtySp` | Dostupné kusy |
| `IteCzTsdNormHSp` | Normované hodiny |
| `IteCzTsdIsMinuteSp` / `IteCzTsdMinutesSp` | Konverze min/hod |
| `IteCzTsdBdFiltrySp` | Filtry terminalu |
| `IteCzTsdBdGetHorizontSp` | Horizont |
| `IteCzInsLoadModuleSp` | Přihlášení → stroj + resource |
| `IteCzInSInitDefCompParmsSp` | Globální parametry aplikace |
| `IteCzAsdAddJobSp` / `IteCzAsdStartJobSp` | ASD modul - sledování stroje |

---

## NESMÍŠ

- Posílat TransType na pozici 1 v SFC34 SP — tam patří prázdný string!
- Používat SLJobRoutes pro frontu práce — správně je IteCzTsdJbrDetails
- Posílat Start/Stop přes SFC34 — to je jen pro Odvod kusů
- Zapomenout na machine transakce (IteCzTsdUpdateMchtrxSp) souběžně s labor
- Posílat write transakce na LIVE Infor (router.py to 403 blokuje)
- Parsovat job čísla z URL path (obsahují lomítka) — vždy query params
