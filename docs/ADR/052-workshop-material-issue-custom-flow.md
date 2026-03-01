# ADR-052: Workshop odvod materiálu přes custom Ite*/IteCz* flow [ACCEPTED — VERIFIED]
> Revize: 2026-02-28
> Primární důkaz: `uploads/indu/industream-ido-mapping-verified.md` (Module_01140, IL)

## Kontext
Původní implementace odvodu materiálu měla nekonzistentní chování: API vracelo technický úspěch, ale business výsledek v Inforu nebyl vždy jistý. Bylo nutné sjednotit flow přesně podle legacy klienta bez workaroundů.

## Rozhodnutí
Manuální odvod materiálu v Workshopu používá deterministický sequence flow z legacy Module_01140:

1. `IteCzTsdValidateItemDcJmcSp`
2. `IteCzTsdValidateQtyDcJmcSp`
3. `IteCzTsdValidateLotDcJmcSp`
4. `IteCzInsValidVydejMatNaVpLotOrScSp` (12)
5. `IteCzTsdUpdateDcJmcSp` (16)
6. `IteCzTsdProcessJobMatlTransDcSp` (6)

`IteCzTsdProcessJobMatlTransDcSp` je v tomto ADR považován za povinný krok manuálního JMC flow, ne za volitelný workaround.

## Signatury write SP (ověřené z IL)
1. `UpdateDcJmcSp(16)`:
`["''", V(vEmpNum), "1", V(vJob), V(vSuffix), V(vOperNum), V(vItem), V(vUM), V(vCurrWhse), V(vMnozstvi), V(vLoc), V(vLot), V(vSerNumList), V(vJobLot), V(vPreaSN), RV(vInfobar)]`
2. `ProcessJobMatlTransDcSp(6)`:
`[V(vJob), V(vSuffix), V(vOperNum), V(vItem), "", RV(vInfobar)]`

## Validace úspěchu operace
Odvod je úspěšný pouze pokud write část (`UpdateDcJmcSp` i `ProcessJobMatlTransDcSp`) projde bez business chyby z Inforu.

Praktické ověření:
1. provést odvod v aplikaci,
2. potvrdit v logu průchod kroky 1–6,
3. ověřit reálný transakční efekt v Infor datech.

## Proč ne přímý write
`Job/Oper/Mat` řádky jsou referenční data. Transakční zápis musí jít přes custom SP vrstvu, která drží validační a side-effect logiku instalace.

## Důsledky
Pozitivní:
- tok je shodný s legacy klientem na úrovni call-orderu,
- menší riziko falešně pozitivního „OK“ výsledku,
- vyšší konzistence při zápisu do Inforu.

Negativní:
- závislost na custom Ite*/IteCz* SP,
- nutnost integračního ověření pro lot/serial edge scénáře.

## Nesmíš
- považovat `UpdateDcJmcSp` za jediný dostačující write krok pro tento manuální flow,
- měnit pořadí parametrů write SP bez IL důkazu,
- obcházet write flow přímým zápisem do business IDO/tabulek.
