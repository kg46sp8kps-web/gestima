# ADR-051: Gestima Dílna — Workshop terminál (manuální write flow) [ACCEPTED — VERIFIED]
> Revize: 2026-03-01
> Primární důkaz: `uploads/indu/industream-ido-mapping-verified.md`
> Reprodukovatelný artefakt: `uploads/indu/InduStream/analysis/industream_verified_sp_calls.json`

## Kontext
Workshop terminál musí zapisovat práci a materiál do Inforu přes stejnou transakční logiku jako legacy InduStream klient. Tento ADR fixuje závazný manuální write flow bez domýšlení a odděluje jej od ASD/automatického sběru ze strojů.

## Rozhodnutí
Pro manuální terminálové akce se používá přesný SP call-order ověřený z IL (`VB$StateMachine_*::MoveNext` v `InduStream.Forms.Std.dll`).

### Ověřený call-order (manuál)
1. `setup_start`: `IteCzTsdUpdateDcSfcWrapperSp` (25, `TransType="1"`).
2. `start`: `IteCzTsdValidateOperNumMachineSp` (11) -> `IteCzTsdUpdateDcSfcWrapperSp` (32, `TransType="3"`) -> `IteCzTsdKapacityUpdateSp` (3) -> `IteCzTsdUpdateMchtrxSp` (9, mode `"H"`).
3. `setup_end`: `IteCzTsdUpdateDcSfcWrapperSp` (25, `TransType="2"`) -> podmíněně druhý wrapper (`TransType="3"` dle `vZahajitPraciFlag`) -> `IteCzTsdValidateOperNumMachineSp` (11) -> `IteCzTsdUpdateMchtrxSp` (9, mode `"H"`).
4. `stop`: `IteCzInsWrapperDcsfcUpdateSp` (27, `TransType="4"`) -> `IteCzTsdKapacityUpdateSp` (3) -> `IteCzTsdUpdateDcSfcMchtrxSp` (22, index 3 = `"J"`).
5. `odvod kusů`: `IteCzTsdUpdateDcSfc34Sp` (20), kde parametr index 1 je vždy prázdný string.
6. `odvod materiálu (manuál 01140)`: `IteCzInsValidVydejMatNaVpLotOrScSp` (12) -> `IteCzTsdUpdateDcJmcSp` (16) -> `IteCzTsdProcessJobMatlTransDcSp` (6).

### Login/session a více strojů
1. Legacy flow mapuje terminál na stroj/resource přes `IteCzInsLoadModuleSp`.
2. `gvPraceNaViceVP` + `IteCzTsdValidateMultiJobDcSfcSp` řeší více VP na jednom terminálu/stroji (multi-VP).
3. V podkladech není důkaz, že by manuální workflow bylo navrženo pro paralelní aktivní práci jednoho operátora na více strojích současně v jedné session.
4. Duplicita přihlášení je ošetřována v login sekvenci (prompt + load module flow).
5. Gestima implementace používá deterministický default `vMultiJobFlag` (env `WORKSHOP_DEFAULT_MULTI_JOB_FLAG`, default `"1"`) + best-effort volání `IteCzTsdValidateMultiJobDcSfcSp`; flag lze explicitně přepsat payloadem (`multi_job_flag`), ale není odvozovaný z lokálního stacku běhů.

### Hranice jistoty
1. Jistota 100 % na úrovni klientského call-orderu a pořadí parametrů SP (ověřeno z IL).
2. Jistota není 100 % na úrovni server-side side-effectů v DB bez integračního běhu proti Infor TEST tenantu.

### Near-atomic handoff (Gestima -> Infor)
1. Lokální transakce přechází do `POSTED` až po read-after-write verifikaci v `SLDcsfcs` proti očekávaným markerům (`TransDate`, `StartTime`, `EndTime` dle typu transakce).
2. Při chybě transportu po write fázi backend spustí recovery verifikaci; pokud je očekávaný řádek v Inforu dohledatelný, transakce se uzavře jako `POSTED`, jinak `FAILED`.
3. Terminál ukončuje STOP lokálně pouze při `status=posted`; při `failed/pending/posting` zůstává operace běžící a je vidět v „Transakce k dořešení“.

### Guardrails proti regresím START/STOP (2026-03-01)
1. Server blokuje duplicitní `START/SETUP_START` stejné `Job+Suffix+Oper` pokud už existuje aktivní běh (`POSTING/POSTED`), aby druhý start nemohl implicitně „ukončit“ první běh.
2. Před write se doplňuje chybějící `wc` a `infor_item` z `SLJobRoutes` (kontext operace), aby `Mchtrx`/stop payload nešel bez routing kontextu.
3. `vUkoncitStrojFlag` se pro `STOP` řídí serverově:
   - `1` při samostatně běžící operaci,
   - `0` pokud běží další aktivní operace na stejném nebo neurčeném `WC` (konzervativní ochrana proti předčasnému zastavení stroje).
4. `IteCzTsdValidateOperNumMachineSp` běží jako checked call (hard-stop před write fází), ale `IteCzTsdValidateEmpNumMchtrxSp` je pouze best-effort: tenanty mají odlišné signatury (`@TEmpNum/@TMach`) a tento call nesmí zablokovat vlastní manuální write flow.
5. STOP strojový krok `IteCzTsdUpdateDcSfcMchtrxSp` používá kompatibilní fallback kandidáty (trans code `J/1`, `item=0`, `whse=''`, `multi_job=0`) kvůli tenant variacím (`SP chyba: 16`); pokud selže celý tento blok, zkouší se ještě kompatibilní fallback `IteCzTsdUpdateMchtrxSp` v módu `J`.
6. Oprava `StartTime/EndTime` na `SLDcsfcs` TT=4 se provádí hned po `InsWrapperDcsfcUpdateSp`, aby při následném selhání strojového kroku nezůstal labor řádek s default časem (typicky 20:00).
7. `SLDcsfcs` řádek pro časový fix se vybírá z více kandidátů (`TransDate DESC, TransNum DESC`) s preferencí wrapper-default času (`72000`) na `StartTime/EndTime`; tím se minimalizuje přepis starších historických STOP záznamů při více bězích stejné operace.
8. `EmpNum` pro write flow je normalizovaný na čistě numerickou hodnotu; pokud `infor_emp_num` ani `username` nejsou čísla, používá se fallback `"1"` (aby se do SP nikdy neposílal text typu `mistr`).
9. Read-after-write verifikace a `_fix_dcsfc_time_after_wrapper` mají fallback dotaz bez `TransDate`, pokud primární dotaz s očekávaným datem nic nevrátí; zabraňuje to falešným `FAILED` stavům při tenant odchylce data/časového pásma na `SLDcsfcs`.

## Důsledky
Pozitivní:
- zápis v Gestimě může být binárně kompatibilní s legacy terminálem,
- odstranění workaroundů a multi-variant write callů zvyšuje konzistenci dat,
- near-atomic guard snižuje riziko „zapsáno v Inforu, ale lokálně failed“.

Negativní:
- silná závislost na custom Ite*/IteCz* vrstvě,
- pro finální provozní jistotu je nutné integrační ověření runtime kontextových proměnných (`vMode`, `vPtrKapacity`, `vBatchKapacity`, `vStroj`, `vOldEmpNum`).

## Nesmíš
- míchat manuální flow se strojovým ASD auto-flow při implementaci write operací,
- měnit pořadí nebo signaturu write SP bez IL důkazu a testu,
- obcházet write SP přímým zápisem do business IDO/tabulek.

## Související dokumenty
- `docs/ADR/052-workshop-material-issue-custom-flow.md`
- `uploads/indu/industream-ido-mapping-verified.md`
- `uploads/indu/industream-ido-mapping.md` (historický broad mapping, ne source of truth pro write flow)
- `docs/ADR/archive/051-workshop-dilna-module.md` (archiv detailů, část tvrzení je nahrazena tímto ADR)
