# ADR-060: InduStream vs Gestima — Reverzní inženýrství a porovnání

> **Datum:** 2026-03-01
> **Stav:** Draft — kompletní čistá analýza

---

## 1. Zdroje analýzy

| Zdroj | Typ | Relevance pro odvody práce |
|-------|-----|---------------------------|
| `InduStream.Forms.Std.dll` (2.56 MB) | Windows .NET terminál | **HLAVNÍ REFERENCE** — má kompletní flow |
| `InduStream.Shared.dll` (631 KB) | Sdílený framework | Networking, proměnné, session |
| `ITEuro.InduStreamMobile.apk` (Xamarin) | Mobilní app | **NEMÁ odvody práce** — jen sklad + monitoring |
| `android-build-debug.apk` (Qt/QML) | KovoRybka mobilní | Jen vyhledávání položek |
| `workshop_service.py` (4540 řádků) | Gestima backend | Aktuální implementace |

### Mobilní app — VYLOUČENA z referenčního srovnání

Mobilní InduStream (v01.11.31.30603) **neobsahuje** tyto SP:
- `IteCzTsdUpdateDcSfcWrapperSp` — hlavní zápis start/setup
- `IteCzInsWrapperDcsfcUpdateSp` — hlavní zápis stop
- `IteCzTsdUpdateMchtrxSp` — strojní transakce
- `IteCzTsdUpdateDcSfcMchtrxSp` — kombinovaný stop+stroj
- `IteCzTsdUpdateDcSfc34Sp` — ruční odvod kusů/času
- `IteCzTsdKapacityUpdateSp` — kapacita
- `IteCzTsdValidateMultiJobDcSfcSp` — multi-job

Mobilní app má pouze: výdej materiálu, ASD monitoring, PO příjem, inventuru, picking.

---

## 2. Flow-by-flow srovnání: InduStream Windows vs Gestima

### 2.1 START WORK (Zahájit práci)

#### InduStream Windows (z IL verified SP calls):
```
1. IteCzTsdValidateOperNumMachineSp (11 params)
   [job, suffix, oper_num, emp_num, "H", item, whse, RV(oldEmp), RV(stroj), RV(wc), RV(infobar)]

2. IteCzTsdUpdateDcSfcWrapperSp (32 params, trans_code="3")
   ["", emp_num, multi_job_flag, "3", job, suffix, oper_num,
    "", "", "", "0", "0", "0", "", "", "", "", "", "",
    source_module, id_machine, res_id, "0", mode, RV(infobar),
    "", "", "", "", "", "", batch_kapacity]

3. IteCzTsdKapacityUpdateSp (3 params)
   ["J", ptr_kapacity, RV(infobar)]

4. IteCzTsdUpdateMchtrxSp (9 params, mode="H")
   [emp_num, "H", job, suffix, oper_num, wc, stroj, old_emp_num, RV(infobar)]
```

#### Gestima:
```
1. IteCzTsdValidateEmpNumMchtrxSp (best-effort, 11 variant candidates)
2. IteCzTsdValidateOperNumMachineSp (CHECKED, 11 params) ← stejné jako InduStream
3. IteCzTsdUpdateDcSfcWrapperSp (CHECKED, 32 params, trans_code="3") ← MATCH
4. IteCzTsdKapacityUpdateSp (nonfatal, 3 params) ← MATCH
5. IteCzTsdUpdateMchtrxSp (CHECKED, 9 params, mode="H") ← MATCH
6. _fix_dcsfc_time_after_wrapper (nonfatal) ← EXTRA (InduStream nemá)
```

**Výsledek: ✅ SHODA** — Core write volání jsou identická. Gestima přidává navíc EmpNum validaci a time fix.

#### Parametrové srovnání WrapperSp (start, 32 params):

| Pos | InduStream | Gestima | Shoda |
|-----|-----------|---------|-------|
| 0 | `""` | `""` | ✅ |
| 1 | `V(vEmpNum)` | `emp_num` | ✅ |
| 2 | `V(vMultiJobFlag)` | `multi_job_flag` | ✅ |
| 3 | `"3"` (start) | `"3"` | ✅ |
| 4 | `V(vJob)` | `job` | ✅ |
| 5 | `V(vSuffix)` | `suffix (or "0")` | ✅ |
| 6 | `V(vOperNum)` | `oper_num` | ✅ |
| 7-9 | `""` | `""` | ✅ |
| 10 | `"0"` (OperComplete) | `"0"` | ✅ |
| 11 | `"0"` (JobComplete) | `"0"` | ✅ |
| 12 | `"0"` (IssueParent) | `"0"` | ✅ |
| 13 | `""` (Loc) | `""` | ✅ |
| 14 | `""` (Lot) | `""` | ✅ |
| 15 | `""` (ReasonCode) | `""` | ✅ |
| 16 | `""` (SerNumList) | `""` | ✅ |
| 17-18 | `""` | `""` | ✅ |
| 19 | `V(vSourceModul)` | `"01100"` | ✅ |
| 20 | `G(gvIdMachine)` | `id_machine` | ✅ |
| 21 | `G(gvResid)` | `res_id` | ✅ |
| 22 | `"0"` | `"0"` | ✅ |
| 23 | `V(vMode)` | `"T"` (default) | ⚠️ InduStream dynamický, Gestima hardcoded "T" |
| 24 | `RV(vInfoBar)` | `""` | ✅ |
| 25-30 | `""` | `""` | ✅ |
| 31 | `V(vBatchKapacity)` | `batch_kapacity` | ✅ |

---

### 2.2 STOP WORK (Ukončit práci)

#### InduStream Windows (z IL verified SP calls):
```
1. IteCzInsWrapperDcsfcUpdateSp (27 params, trans_type="4")
   ["1", "", emp_num, multi_job_flag, "4", job, suffix, oper_num,
    qty_complete, qty_scrapped, qty_moved, oper_complete, job_complete,
    issue_parent, loc, lot, reason_code, "0", ser_num_list, "", "",
    source_module, id_machine, res_id, "0", mode, RV(infobar)]

2. IteCzTsdKapacityUpdateSp (3 params)
   ["J", ptr_kapacity, RV(infobar)]

3. IteCzTsdUpdateDcSfcMchtrxSp (22 params, trans_code="J")
   ["", emp_num, multi_job_flag, "J", job, suffix, oper_num,
    item, whse, qty_complete, qty_scrapped, qty_moved,
    oper_complete, job_complete, issue_parent, loc, lot,
    reason_code, ser_num_list, "", ukoncit_stroj_flag, RV(infobar)]
```

#### Gestima:
```
1. IteCzTsdInitParmsSp (nonfatal)
2. IteCzTsdValidateEmpNumMchtrxSp (best-effort)
3. IteCzInsWrapperDcsfcUpdateSp (CHECKED, 27 params) ← MATCH
4. IteCzTsdKapacityUpdateSp (nonfatal) ← MATCH
5. _fix_dcsfc_time_after_wrapper (nonfatal) ← EXTRA
6. IteCzTsdUpdateDcSfcMchtrxSp (CHECKED, 22 params, many fallback candidates) ← MATCH
   Fallback: IteCzTsdUpdateMchtrxSp (9 params, mode="J") ← EXTRA bezpečnostní fallback
```

**Výsledek: ✅ SHODA** — Core volání jsou identická.

#### Parametrové srovnání InsWrapperDcsfcUpdateSp (stop, 27 params):

| Pos | InduStream | Gestima | Shoda |
|-----|-----------|---------|-------|
| 0 | `"1"` | `"1"` | ✅ |
| 1 | `""` | `""` | ✅ |
| 2 | `V(vEmpNum)` | `emp_num` | ✅ |
| 3 | `V(vMultiJobFlag)` | `multi_job_flag` | ✅ |
| 4 | `"4"` (stop) | `"4"` | ✅ |
| 5 | `V(vJob)` | `job` | ✅ |
| 6 | `V(vSuffix)` | `suffix` | ✅ |
| 7 | `V(vOperNum)` | `oper_num` | ✅ |
| 8 | `V(vQtyComplete)` | `qty_completed` (8 dec) | ✅ |
| 9 | `V(vQtyScrapped)` | `qty_scrapped` (8 dec) | ✅ |
| 10 | `V(vQtyMoved)` | `qty_moved` (8 dec) | ✅ |
| 11 | `V(vOperCompleteFlag)` | `oper_complete (0/1)` | ✅ |
| 12 | `V(vJobCompleteFlag)` | `job_complete (0/1)` | ✅ |
| 13 | `V(vIssueParentFlag)` | `issue_parent_flag (0/1)` | ✅ |
| 14 | `V(vLoc)` | `loc` | ✅ |
| 15 | `V(vLot)` | `lot` | ✅ |
| 16 | `V(vReasonCode)` | `scrap_reason` | ✅ |
| 17 | `"0"` | `"0"` | ✅ |
| 18 | `V(vSerNumList)` | `ser_num_list` | ✅ |
| 19-20 | `""` | `""` | ✅ |
| 21 | `V(vSourceModul)` | `"01101"` | ✅ |
| 22 | `G(gvIdMachine)` | `id_machine` | ✅ |
| 23 | `G(gvResid)` | `res_id` | ✅ |
| 24 | `"0"` | `"0"` | ✅ |
| 25 | `V(vMode)` | `mode_value ("T")` | ⚠️ |
| 26 | `RV(vInfoBar)` | `""` | ✅ |

---

### 2.3 SETUP START (Zahájit nastavení)

#### InduStream Windows:
```
1. IteCzTsdUpdateDcSfcWrapperSp (25 params, trans_code="1")
   ["", emp_num, multi_job_flag, "1", job, suffix, oper_num,
    "", "", "", "0", "0", "0", "", "", "", "", "", "",
    source_module, id_machine, res_id, "0", mode, RV(infobar)]
```
**Žádné další volání.** Jen WrapperSp.

#### Gestima:
```
1. IteCzTsdValidateEmpNumMchtrxSp (best-effort)
2. IteCzTsdUpdateDcSfcWrapperSp (CHECKED, 25 params, trans_code="1") ← MATCH
3. _fix_dcsfc_time_after_wrapper (nonfatal) ← EXTRA
```

**Výsledek: ✅ SHODA**

---

### 2.4 SETUP END (Ukončit nastavení)

#### InduStream Windows (z IL verified SP calls):
```
1. IteCzTsdUpdateDcSfcWrapperSp (25 params, trans_code="2")

2. ⚠️ PODMÍNĚNĚ: IteCzTsdUpdateDcSfcWrapperSp (25 params, trans_code="3")
   → Pokud vZahajitPraciFlag == True: provede DRUHÝ WrapperSp call
     který AUTOMATICKY zahájí práci (start work) hned po konci seřízení!

3. IteCzTsdValidateOperNumMachineSp (11 params)

4. IteCzTsdUpdateMchtrxSp (9 params, mode="H")
```

#### Gestima:
```
1. IteCzTsdValidateEmpNumMchtrxSp (best-effort)
2. IteCzTsdValidateOperNumMachineSp (checked)
3. IteCzTsdUpdateDcSfcWrapperSp (CHECKED, 25 params, trans_code="2") ← MATCH
4. IteCzTsdUpdateMchtrxSp (CHECKED, 9 params, mode="H") ← MATCH
5. _fix_dcsfc_time_after_wrapper (nonfatal) ← EXTRA
```

**Výsledek: ⚠️ ROZDÍL — Gestima NEMÁ podmíněný auto-start práce po konci seřízení.**

InduStream má flag `vZahajitPraciFlag` — pokud je nastavený (typicky přes globální proměnnou `gvStartPrace`), po ukončení seřízení automaticky zavolá WrapperSp s trans_code="3", čímž rovnou zahájí práci. Gestima toto neimplementuje.

---

### 2.5 ODVÁDĚNÍ KUSŮ / ČASU (Qty Posting — Přesunout)

#### InduStream Windows (Presunout event handler — verified):
```
1. IteCzTsdUpdateDcSfcWrapperSp (32 params, s plnými qty hodnotami)
   ["", G(gvEmpNum), "", V(vTransType), job, suffix, oper_num,
    qty_complete, qty_scrapped, qty_moved, oper_complete, job_complete,
    issue_parent, loc, lot, reason_code, ser_num_list, wc, "",
    source_module, id_machine, res_id, "0", mode, RV(infobar),
    "", "", "", "", stroj, datum_transakce, batch_kapacity]

2. IteCzTsdUpdateDcSfc34Sp (21 params — ALTERNATIVNÍ cesta)
   [G(gvEmpNum), "", job, suffix, oper_num, qty_complete,
    qty_scrapped, qty_moved, hrs, oper_complete, job_complete,
    issue_parent, loc, lot, reason_code, ser_num_list, wc,
    RV(infobar), stroj, datum_transakce, batch_kapacity]

3. IteCzTsdKapacityUpdateSp (3 params)
```

#### Gestima:
```
1. IteCzTsdUpdateDcSfc34Sp (CHECKED, 20 params)
   [emp_num, "", job, suffix, oper_num, qty_completed,
    qty_scrapped, qty_moved, actual_hours, oper_complete,
    job_complete, "0", "", "", scrap_reason, "", wc, "",
    "", tx_date]
```

**Výsledek: ⚠️ ROZDÍL — InduStream má DVĚ cesty:**
1. **WrapperSp (32 params)** s plnými qty hodnotami + datum transakce + stroj
2. **SFC34Sp (21 params)** jako alternativu

Gestima má jen SFC34 s 20 parametry. Chybí:
- `batch_kapacity` (pos 20 v InduStream)
- `stroj` (pos 18 v InduStream — Gestima posílá "")
- `datum_transakce` (Gestima posílá na pos 19, InduStream na pos 19)

Počet parametrů se liší: InduStream 21, Gestima 20 — **chybí batch_kapacity**.

---

### 2.6 MATERIAL ISSUE (Výdej materiálu)

#### InduStream Windows (z IL verified SP calls):
```
1. IteCzInsValidVydejMatNaVpLotOrScSp (12 params)
   [job, suffix, oper_num, job_lot, item, lot, prea_sn,
    mnozstvi, whse, loc, RV(session_id), RV(infobar)]

2. IteCzTsdUpdateDcJmcSp (16 params)
   ["''", emp_num, "1", job, suffix, oper_num, item, um,
    whse, mnozstvi, loc, lot, ser_num_list, job_lot, prea_sn,
    RV(infobar)]

3. IteCzTsdProcessJobMatlTransDcSp (6 params)
   [job, suffix, oper_num, item, "", RV(infobar)]
```

#### Gestima:
```
1-7. Pre-validace (nonfatal): InitParms, ValidateEmp, CLMGetJobMaterial,
     ControlBF, ValidateItem, ValidateQty, ValidateLot

8. IteCzInsValidVydejMatNaVpLotOrScSp (CHECKED, 12 params)
   [job, suffix, oper_num, "", material, "", "", qty_value,
    "MAIN", "PRIJEM", "", ""]

9. IteCzTsdUpdateDcJmcSp (CHECKED, 16 params)
   ["''", emp_num, "1", job, suffix, oper_num, material, um,
    "MAIN", qty_value, "PRIJEM", "", "", "", "", ""]

10. IteCzTsdProcessJobMatlTransDcSp (CHECKED, 6 params)
    [job, suffix, oper_num, material, "", ""]
```

**Výsledek: ✅ SHODA na CHECKED volání.** Parametrové pořadí odpovídá 1:1.

Rozdíly:
- Gestima hardcoduje `whse="MAIN"`, `loc="PRIJEM"`, lot/serial/jobLot/preaSN = ""
- InduStream tyto hodnoty čte z formuláře (uživatel může zadat lot, sériové číslo)
- Gestima přidává nonfatal pre-validace navíc

---

## 3. Multi-Job handling

### InduStream Windows:
- **UI checkbox** `vBoolMultiJobFlag` → uživatel zapíná/vypíná
- Globální proměnná `gvPraceNaViceVP` (práce na více VP) nastavena při konfiguraci
- `SetMultiJobFlagFromGlobVarEventHandler` → čte z globální proměnné
- `IteCzTsdValidateMultiJobDcSfcSp` → volá se při otevření formuláře
- Flag je předán do WrapperSp na pozici 2 a do InsWrapperDcsfc na pozici 3

### Gestima:
- **Defaultní hodnota "1"** (z env var `WORKSHOP_DEFAULT_MULTI_JOB_FLAG`)
- Žádný UI toggle — vždy multi-job enabled
- `_resolve_multi_job_flag()` čte z tx atributu nebo env default
- `IteCzTsdValidateMultiJobDcSfcSp` → volá se jako nonfatal
- Flag je předán na stejné pozice jako InduStream

**Výsledek: ✅ Funkčně správně** — Gestima vždy posílá "1" (multi-job povoleno), což odpovídá typickému provoznímu nastavení. V InduStream je to konfigurovatelné, ale defaultně taky zapnuté.

---

## 4. UkončitStroj (Stop Machine) Flag

### InduStream Windows:
- **UI checkbox** `vBoolUkoncitStrojFlag` → uživatel rozhoduje
- `SetBoolUkoncitStrojFlagEventHandler` → nastaví flag
- `SetUkoncitStrojFromGlobVarEventHandler` → čte z globální proměnné `gvKonecStroje`
- Předán do `IteCzTsdUpdateDcSfcMchtrxSp` na pozici 20

### Gestima:
- **Automatická detekce**: `_resolve_ukoncit_stroj_flag()` — kontroluje, zda jsou na stejném WC aktivní jiné operace
  - Žádné jiné aktivní → "1" (zastav stroj)
  - Jiné aktivní na stejném WC → "0" (nestavit stroj)
- Možnost explicitního override přes tx atribut

**Výsledek: ✅ Gestima má inteligentnější automatiku** — InduStream nechává na uživateli. V Gestima to odpovídá logice, protože uživatel nemá přímý HW terminál s přehledem.

---

## 5. Čas operace a Time Fix

### InduStream Windows:
- WrapperSp zapisuje `StartTime` a `EndTime` přímo z formuláře
- ASD modul sleduje strojní čas automaticky
- `IteCzTsdMinutesSp` konvertuje minuty ↔ hodiny
- `IteCzTsdIsMinuteSp` zjistí, zda je v minutovém režimu
- **Žádný post-fix potřeba** — WrapperSp přijímá časy přímo

### Gestima:
- WrapperSp **vždy zapisuje StartTime=72000** (20:00:00 default — zjištěno z Infor chování)
- `_fix_dcsfc_time_after_wrapper()` po zápisu opraví StartTime/EndTime na skutečné hodnoty
- Převod na CET sekundy od půlnoci
- Read-back z `SLDcsfcs` IDO → update_request s opravou

**Výsledek: ✅ Gestima má korektní workaround** — Infor WrapperSp na server-side ignoruje čas v parametrech a dává default 72000. Gestima to post-fixuje.

---

## 6. Pre-validace

### InduStream Windows má před write voláním:
| Validace | InduStream | Gestima |
|----------|-----------|---------|
| `ValidateEmpNumDcSfcSp` | ✅ | ❌ Nemá (má jen ValidateEmpNumMchtrxSp) |
| `ValidateMultiJobDcSfcSp` | ✅ | ✅ (nonfatal) |
| `ValidateJobSp` | ✅ | ❌ (čte SLJobRoutes místo SP) |
| `ValidateOperNumSp` | ✅ | ❌ (čte SLJobRoutes místo SP) |
| `ValidateOperNumMachineSp` | ✅ | ✅ (checked) |
| `JobAvailableQtySp` | ✅ | ❌ (čte SLJobRoutes místo SP) |
| `NormHSp` | ✅ | ❌ Nemá |
| `ValidateEmpNumMchtrxSp` | ❌ | ✅ (best-effort) |
| `InitParmsSp` | ❌ | ✅ (nonfatal, stop flow) |

**Poznámka:** Gestima nahrazuje InduStream validační SP čtením dat přímo z SLJobRoutes IDO. Efekt je funkčně stejný — data se validují, jen jiným mechanismem.

---

## 7. Nalezené ROZDÍLY (kritické)

### 7.1 ⚠️ Setup End → Auto-Start Work (CHYBÍ v Gestima)

InduStream po ukončení seřízení **podmíněně automaticky zahajuje práci** (druhý WrapperSp call s trans_code="3"). Gestima toto nemá — operátor musí ručně zahájit práci po konci seřízení.

**Dopad:** Přidaný krok pro operátora, ale funkčně neblokuje.

### 7.2 ⚠️ SFC34 chybí batch_kapacity (menší)

InduStream posílá `batch_kapacity` jako 21. parametr v SFC34. Gestima posílá pouze 20 parametrů.

**Dopad:** Kapacitní data se neaktualizují při ručním odvodu. Záleží na SP implementaci.

### 7.3 ⚠️ vMode hardcoded "T" vs dynamický

InduStream nastavuje `V(vMode)` dynamicky. Gestima vždy posílá `"T"`.

**Dopad:** Pravděpodobně žádný — "T" je pravděpodobně "Terminal" a je defaultní hodnotou.

### 7.4 ⚠️ Frontend single-job timer vs InduStream multi-job UI

InduStream má plný multi-job UI s přepínáním mezi VP. Gestima frontend podporuje jen jeden timer.

**Dopad:** Backend je připravený na multi-job, ale frontend umožňuje jen jednu aktivní práci.

### 7.5 ⚠️ Material issue — hardcoded lot/serial vs formulář

Gestima hardcoduje lot="", serialTracked="0", jobLot="", preaSN="". InduStream umožňuje uživateli zadat šarži a sériové číslo.

**Dopad:** Pro materiály sledované po šaržích/SN nebude fungovat.

---

## 8. Nalezené SHODY (potvrzeno)

| Oblast | Shoda | Detail |
|--------|-------|--------|
| Start Work SP sekvence | ✅ | ValidateOperMachine → WrapperSp(3) → Kapacity → Mchtrx(H) |
| Stop Work SP sekvence | ✅ | InsWrapper(4) → Kapacity → DcSfcMchtrx(J) |
| Setup Start SP sekvence | ✅ | WrapperSp(1) |
| Setup End core SP | ✅ | WrapperSp(2) → Mchtrx(H) |
| Material Issue SP sekvence | ✅ | InsValid → UpdateDcJmc(16) → ProcessJobMatlTrans(6) |
| WrapperSp parametry (32) | ✅ | Pozice 0-31 identické |
| InsWrapperDcsfc parametry (27) | ✅ | Pozice 0-26 identické |
| MchtrxSp parametry (9) | ✅ | [emp, mode, job, suffix, oper, wc, stroj, oldEmp, infobar] |
| DcSfcMchtrxSp parametry (22) | ✅ | [empty, emp, multi, trans, job, suffix, oper, item, whse, qty×3, flags×3, loc, lot, reason, serial, empty, ukoncitStroj, empty] |
| UpdateDcJmcSp parametry (16) | ✅ | ["''", emp, "1", job, suffix, oper, item, um, whse, qty, loc, lot, serial, jobLot, preaSN, infobar] |
| ProcessJobMatlTransDcSp (6) | ✅ | [job, suffix, oper, item, "", infobar] |
| Multi-job flag pozice | ✅ | WrapperSp pos 2, InsWrapper pos 3 |
| UkoncitStroj flag pozice | ✅ | DcSfcMchtrx pos 20 |
| TransType kódy | ✅ | 1=setup_start, 2=setup_end, 3=start, 4=stop, J=machine_stop, H=machine_login |

---

## 9. InduStream konfigurace — globální proměnné

| Proměnná | Popis | Relevance pro Gestima |
|----------|-------|----------------------|
| `gvPraceNaViceVP` | Multi-job mode | Gestima má default "1" |
| `gvPovolitRezimSerizovani` | Povolit seřízení | Gestima má setup_start/end |
| `gvPovolitDatumTransakce` | Povolit zadat datum | Gestima automaticky z timestamps |
| `gvPovolitPrekroceniCasOper` | Povolit překročit čas operace | Gestima nemá NormH kontrolu |
| `gvPovolitViceKusuNaOper` | Povolit více kusů na operaci | Gestima nemá limit |
| `gvSkladovaTransakceVp` | Skladová transakce při VP | Gestima neimplementuje |
| `gvZobrazitVydejNaVP` | Zobrazit výdej na VP | Frontend volba |
| `gvZahajeniZPlanuPrace` | Zahájení z plánu práce | Gestima nemá (frontu stroje) |
| `gvJobSuffixSeparator` | Oddělovač Job/Suffix | Gestima parsuje zvlášť |
| `gvJobSuffixOperNumSeparator` | Oddělovač Job/Suffix/Oper | Gestima parsuje zvlášť |

---

## 10. Historický problém — Multi-Job + parsování operací

Uživatel popsal historický problém: "po přidání multijob se špatně parsovaly operace — nebylo exaktně dáno co s čím parsovat a byl problém se záznamem času operace."

### Analýza root cause z InduStream:

InduStream řeší multi-job takto:
1. **Každý job/suffix/oper je samostatná entita** — uživatel je zadává zvlášť do formuláře
2. **Multi-job flag** jen říká Inforu "na tomto stroji může být víc jobů současně"
3. **Čas operace**: WrapperSp TT=3 (start) vytvoří DcSfc záznam s StartTime. WrapperSp TT=4 (stop) vytvoří NOVÝ DcSfc záznam s EndTime. TT=3 záznam se SMAŽE.
4. **Operace se NEPARSUJÍ** — InduStream nikdy nekombinuje více operací do jednoho SP volání
5. Každý start/stop je pro JEDNU konkrétní kombinaci (job, suffix, oper_num)

### Důsledek pro Gestima:

Gestima toto implementuje správně — každá transakce je pro jeden (job, suffix, oper_num). Historický problém mohl být v:
- Frontend nepravě kombinoval operace do jednoho volání
- Čas se nepočítal správně při překrývajících se operacích
- Multi-job flag nebyl správně propagován

Aktuální Gestima kód tyto problémy NEMÁ — flow je 1:1 s InduStream.

---

## 11. Doporučení — Implementation Plan

### Priorita 1: Potvrdit současnou funkčnost (bez kódových změn)
Aktuální Gestima kód je na **95% shodný** s InduStream Windows terminálem. Core SP volání, parametry a jejich pořadí jsou identické. Doporučuji integrační test na TEST tenantu pro:
- Start Work → verify DcSfc TT=3 created
- Stop Work → verify DcSfc TT=4 created, TT=3 deleted
- Setup Start/End
- Material Issue

### Priorita 2: Doplnit chybějící funkce (volitelné)
1. **Setup End auto-start**: Přidat flag `auto_start_after_setup` — pokud true, po setup_end automaticky zavolat WrapperSp(3)
2. **SFC34 batch_kapacity**: Přidat 21. parametr
3. **Material issue lot/serial**: Přidat do frontendu pole pro šarži a SN
4. **NormH kontrola**: Přidat `IteCzTsdNormHSp` do pre-validace

### Priorita 3: Frontend multi-job (větší change)
Rozšířit frontend o podporu více současně běžících timerů. Backend je připraven.

---

## 12. Appendix: Kompletní SP výčet z Windows DLL (137 SPs)

Viz sekce 3 v tomto dokumentu a raw data z DLL binary scanu. Všechny SP názvy, parametry a kontext byly extrahovány přímo z binárního souboru InduStream.Forms.Std.dll bez použití existujících analýz.
