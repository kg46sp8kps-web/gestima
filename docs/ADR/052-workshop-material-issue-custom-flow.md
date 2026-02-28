# ADR-052: Workshop Odvod Materiálu přes custom Ite*/IteCz* workflow [ACCEPTED — TUNING IN PROGRESS]

## Kontext
V dílně bylo potřeba zprovoznit spolehlivý odvod materiálu z workflow operace. Původní implementace vracela API "úspěch", ale nevznikal reálný materiálový pohyb v Inforu (resp. vznikaly duplicitní řádky bez efektivního odvodu).

Důležité upřesnění: procedury se jménem `Ite*` / `IteCz*` nejsou standardní Infor baseline, ale custom vrstva třetí strany nad Infor instalací.

## Rozhodnutí
Pro odvod materiálu v Workshop modulu se používá explicitní custom tok vytěžený z původní aplikace (`InduStream.Forms.Std.dll`, `Module_01140`) a mapovaný do backendu Gestima.

Finální write tok:
1. `IteCzTsdValidateItemDcJmcSp`
2. `IteCzTsdValidateQtyDcJmcSp`
3. `IteCzTsdValidateLotDcJmcSp`
4. `IteCzInsValidVydejMatNaVpLotOrScSp`
5. `IteCzTsdUpdateDcJmcSp` (finální transakční zápis)

`IteCzTsdProcessJobMatlTransDcSp` není v tomto rozhodnutí považován za hlavní write krok pro aktuální instalaci/workflow 01140.

## Proč ne přímý write z Job/Oper/Mat dat
`Job/Oper/Mat` data slouží primárně jako referenční/plánovací vstup. Samotný odvod je transakce, která potřebuje business logiku custom vrstvy:
- validace stavu operace,
- kontrola množství,
- lot/serial podmínky,
- vazby na session/context,
- side‑effects mimo jednu tabulku.

Přímý zápis na základě načtených řádků není ekvivalentní tomuto transakčnímu workflow.

## Implementace (Gestima)
- `app/services/workshop_service.py`
  - přidána konstanta: `_WRITE_SP_INS_VALID_VYDEJ_MAT`
  - přidány build funkce kandidátů:
    - `_build_ins_valid_vydej_mat_candidates(...)`
    - `_build_update_dcjmc_candidates(...)`
  - `post_material_issue(...)` používá nový sequence flow podle bodů 1–5
  - výchozí skladový kontext: `Whse=MAIN`, `Loc=PRIJEM`, lot default prázdný, pokud není požadován

- `tests/test_workshop_service.py`
  - test toku přes `INS_VALID` + `UPDATE_DCJMC`
  - test odmítnutí nenulového `ReturnValue` na `INS_VALID`
  - test odmítnutí nenulového `ReturnValue` na `UPDATE_DCJMC`

## Validace a úspěch operace
API odvod je považován za úspěšný pouze pokud finální write krok (`IteCzTsdUpdateDcJmcSp`) projde bez Infor chyby.

Praktické ověření:
1. v aplikaci provést odvod materiálu,
2. v logu potvrdit průchod kroků 1–5,
3. v Infor ověřit skutečný vznik materiálové transakce (ne pouze změnu/duplikaci řádku v job material view).

## Pozorování z incidentu
Byl detekován stav, kdy volání vracela technicky "OK", ale nevznikl odpovídající pohyb v Infor transakcích. Tento ADR proto explicitně odděluje:
- "SP odpověděla bez HTTP chyby" vs.
- "business transakce je skutečně zaúčtována".

## Alternativy
1. Použít pouze `IteCzTsdProcessJobMatlTransDcSp` jako finální write
- zamítnuto pro aktuální instalaci: vracelo nekonzistentní výsledek

2. Přímý write do business IDO/tabulek bez custom SP
- zamítnuto: obchází business pravidla custom vrstvy, vysoké riziko nekonzistence

3. Standardní Infor flow bez custom Ite* vrstvy
- odloženo: může být cílem budoucí migrace, ale není kompatibilní drop-in pro současnou instalaci

## Důsledky
Pozitivní:
- odvod je sladěn s reálným tokem původní aplikace,
- menší riziko falešně pozitivního "úspěchu",
- lepší reprodukovatelnost při troubleshootingu.

Negativní:
- závislost na custom procedurách třetí strany,
- vyšší citlivost na rozdíly parametrů mezi instalacemi/verzemi,
- potřeba průběžného ladění mappingu lot/serial/session scénářů.

## Nesmíš
- považovat pouhé načtení `Job/Oper/Mat` dat za dostatečný podklad pro přímý write,
- měnit pořadí argumentů custom SP bez reálné verifikace v Infor,
- označit odvod jako hotový bez potvrzení transakčního výsledku v Infor datech.

## Otevřené body (další tuning)
- lot/serial edge cases (preassigned serials),
- přesné mapování některých kontextových proměnných (`vJobLot`, `vPreaSN`, session) pro specifické provozy,
- jednotné diagnostické logování "business success" vs. "transport success".
