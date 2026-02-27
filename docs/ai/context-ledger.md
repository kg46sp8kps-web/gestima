# AI Context Ledger

Tento soubor drží persistentní kontext mezi úkoly.
Aktualizuj po každém netriviálním tasku.

## Aktivní cíl

- Zpevnit dilensky terminal proti chybnemu vykazovani: blokace hotovych operaci, skryti dokoncenych operaci z fronty a striktni zdroj fronty/operaci pouze z rozvrhu (`IteCzTsdJbrDetails`) bez fallbacku na `SLJobRoutes`.

## Poslední rozhodnutí

- Date: 2026-02-27
- Decision: `DrawingImportService` podporuje dva zdroje v jednom poli `DRAWINGS_SHARE_PATH`: lokalni cesta a `ssh://user@host:port/path`.
- Why: Umoznuje stejny import workflow v macOS dev i Linux produkci bez SMB mountu; admin UI i API zustaly beze zmen.

- Date: 2026-02-27
- Decision: Vykon importu kresli presne statistiky (`files_created`, `links_created`, `parts_updated`, `skipped`) per soubor, ne jen per slozka.
- Why: Puvodni implementation nadhodnocovala/zkreslovala vysledek a komplikovala audit importu.

- Date: 2026-02-27
- Decision: Aktivní AI governance je sjednocena na Codex flow (`AGENTS.md`) s guardy (`docs-guard`, `quality-gate`, PR template, CI trend report).
- Why: Zajišťuje konzistentní proces, kontrolovaný růst dokumentace a měřitelný trend kvality.

- Date: 2026-02-27
- Decision: Fronta práce se načítá primárně z `IteCzTsdJbrDetails` s fallbackem na `SLJobRoutes`.
- Why: RE analýza potvrzuje `IteCzTsdJbrDetails` jako zdroj plan queue (včetně `OpDatumSt/OpDatumSp`), fallback drží kompatibilitu na instancích bez tohoto IDO.

- Date: 2026-02-27
- Decision: START/SETUP flow jde přes `IteCzTsdUpdateDcSfcWrapperSp` + `IteCzTsdUpdateMchtrxSp`; STOP flow preferuje `IteCzInsWrapperDcsfcUpdateSp` a fallbackuje na Wrapper stop, vždy s uzavřením stroje přes `IteCzTsdUpdateDcSfcMchtrxSp`.
- Why: Odpovídá reverse-engineering sekvenci z InduStream, ale zároveň je implementován bezpečný fallback pro odlišné signature mezi Infor instalacemi.

- Date: 2026-02-27
- Decision: UI timer drží plný kontext běžící práce (`job/suffix/oper/item/wc`) a STOP používá tento snapshot místo aktuálně vybrané položky.
- Why: Zabraňuje chybnému odvodu při změně výběru v tabulce během běžící práce.

- Date: 2026-02-27
- Decision: Fronta práce/plánované časy se berou ze `SLJobRoutes` (`DerStartDate`, `DerEndDate`, fallback `JshStartDate`, `JshEndDate`) místo `IteCzTsdJbrDetails`.
- Why: Read-only metadata probe na TEST Inforu potvrdil, že `IteCzTsdJbrDetails` v této instanci neobsahuje `Job/Suffix`, takže nelze stabilně sestavit frontu; `SLJobRoutes` obsahuje job i plánované termíny.

- Date: 2026-02-27
- Decision: Materiály operace se mapují z kombinace polí `MaterialBd/*Bd` a fallbacku `Item`, `DerItemDescription`, `MatlQty`, `QtyIssued`.
- Why: V TEST metadatech `TotCons/Qty/BatchCons` neexistují, ale `*Bd` bývají často `NULL`; fallback na `Item/MatlQty` zajišťuje, že panel materiálů vrací použitelná data.

- Date: 2026-02-27
- Decision: STOP flow je přepnut na `WrapperSp` (labor) + `Mchtrx` s trans type `J` (machine stop), s fallbackem na plnou signaturu `IteCzTsdUpdateDcSfcMchtrxSp`.
- Why: Probe signatur v TESTu odhalil přesné pořadí parametrů; původní zkrácené volání `DCSFC_MCHTRX` padalo na chybějících parametrech a shazovalo transakce do `failed`.

- Date: 2026-02-27
- Decision: Modul `work-materials` byl sloučen do `work-ops`; tile je přejmenovaný na `Technologie` a materiálové zadávání běží přes collapsible sekci uvnitř stejného panelu.
- Why: Uživatel požadoval jeden sjednocený tile místo rozdělení Operace/Materiál při zachování funkčnosti zadávání materiálu.

- Date: 2026-02-27
- Decision: V přehledu materiálů byl odstraněn detailní dropdown/expand řádek pro vazby operací; vazby zůstávají viditelné přímo v řádku materiálu.
- Why: Data byla vizuálně roztahaná a dropdown nepřinášel hodnotu pro primární workflow.

- Date: 2026-02-27
- Decision: `TileWorkMaterials` běží pouze jako embedded sekce v „Technologie“ a byl z něj odstraněn redundantní unsupported-item guard; embedded styl tabulky/ribbonu byl sjednocen s vizuálem operací.
- Why: Po sloučení panelů byl guard nedosažitelný a UI působilo nekonzistentně vůči tabulce operací.

- Date: 2026-02-27
- Decision: Materiálová logika byla plně zploštěna přímo do `TileWorkOps.vue` a samostatný soubor `TileWorkMaterials.vue` byl odstraněn.
- Why: Eliminace mrtvého/duplicitního FE surface a jednodušší údržba jednoho sjednoceného tile „Technologie“.

- Date: 2026-02-27
- Decision: Collapsible „Materiál“ byl přesunut nad tabulku operací (první sekce panelu) a vazby materiál-operace jsou upravitelné inline přímo v řádku materiálu (add/unlink bez detail dropdownu).
- Why: Lepší pracovní tok podle požadavku uživatele a zachování kompaktního zobrazení.

- Date: 2026-02-27
- Decision: Vizuál materiálové tabulky byl dorovnán k tabulce operací, včetně odstranění odlišného hover podbarvení řádků.
- Why: Sjednocení UI v rámci jednoho tile „Technologie“.

- Date: 2026-02-27
- Decision: Sekce `Operace` získala vlastní collapsible hlavičku a výchozí stav obou sekcí (`Materiál` + `Operace`) je otevřeno.
- Why: Požadavek na jednotné prostředí s konzistentním chováním obou částí.

- Date: 2026-02-27
- Decision: Vazby materiál-operace jsou editovatelné inline (add/unlink) přímo ve sloupci `Operace` u materiálového řádku.
- Why: Zachování kompaktního zobrazení při zachování možnosti úpravy navázaných operací.

- Date: 2026-02-27
- Decision: V materiálové tabulce bylo odstraněno zobrazení `Tvar`; zůstávají pouze rozměry. Uzamčené rozměry se renderují ve stejné velikosti jako input pole.
- Why: Požadavek na čistší tabulku bez redundantní informace o tvaru a jednotný vizuál dimenzí.

- Date: 2026-02-27
- Decision: Vazba materiálu na operaci je UI-limitovaná na jednu operaci přes single dropdown (`Bez operace` / konkrétní operace).
- Why: Workflow vyžaduje jednoznačné přiřazení materiálu k jedné operaci namísto multi-vazeb.

- Date: 2026-02-27
- Decision: Výběr operace u materiálu je realizovaný jako editable combobox (`OperationCombobox`) se stejným UX patternem jako `WcCombobox`.
- Why: Uživatel potřebuje ruční psaní/filtrování při výběru operace, ne statický select.

- Date: 2026-02-27
- Decision: Pozadí sekcí `Materiál` a `Operace` bylo sjednoceno na `surface` styl s hover `var(--b1)` analogicky k tabulkové části v listu položek.
- Why: Vizuální konzistence napříč panely a čitelnější oddělení sekcí od gradientního pozadí.

- Date: 2026-02-27
- Decision: Validace preodvodu kusu bezi centralne v `post_transaction_to_infor`: mimo pilu se transakce zablokuje, na pile je preodvod povolen pouze pro prvni operaci.
- Why: Uzivatelsky pozadavek je povolit "vice kusu" jen pro prvni reznou operaci, aby dalsi operace zustaly striktně proti planu.

- Date: 2026-02-27
- Decision: Pri povolenem preodvodu na pile se po uspesnem odvodu automaticky navysuje `SLJobs.QtyReleased` pres `/json/updaterequest` (Action=2 update).
- Why: TEST Infor prostredi ma blokovane `PUT /json/{ido}/updateitem`; `updaterequest` je overena funkcni cesta pro update existujiciho radku.

- Date: 2026-02-27
- Decision: Workshop Operation panel zobrazuje planovane casy (`OpDatumSt/OpDatumSp`) i lokalni stop-form policy hint (pila vs. standard operace) a FE predvaliduje zjevny overrun mimo pilu.
- Why: Operator vidi plan a pravidla hned pri odvodu; snizuje se pocet neplatnych stop pokusu.

- Date: 2026-02-27
- Decision: Fronta `/workshop/queue` je scoped pouze na `SLJobRoutes` s `Type='J'` a `JobStat='R'`; data z primarniho rozvrhoveho IDO (`IteCzTsdJbrDetails`) se berou jen pro operace, ktere existuji v released scope.
- Why: Uzivatel potrebuje videt pouze uvolnene VP; primarni rozvrh muze obsahovat i nereleased/odlisne radky.

- Date: 2026-02-27
- Decision: Pri merge fronty se planovane casy/qty/descriptive pole doplnuji z `SLJobRoutes`, pokud v primarnim rozvrhovem zdroji chybi.
- Why: V praxi byly v UI prazdne hodnoty `Plan od/Plan do`, i kdyz `SLJobRoutes` je obsahoval.

- Date: 2026-02-27
- Decision: FE formatovani casu ve fronte vraci surovou hodnotu, pokud parser `Date` selze, misto tvrdeho `—`.
- Why: Infor muze vracet lokalni/string format, ktery JS parser neumi; lepsi je hodnotu ukazat nez schovat.

- Date: 2026-02-27
- Decision: Dokoncenost operace se vyhodnocuje kombinaci stavoveho textu (`State/StateAsd` marker) a mnozstevniho pravidla (`QtyComplete + QtyScrapped >= JobQtyReleased`), a tyto operace se z fronty filtruji.
- Why: Uzivatel nechce videt ani obsluhovat uz uzavrene operace; ciste mnozstevni kontrola nemusi stacit na vsechny instalace.

- Date: 2026-02-27
- Decision: Pred postem transakce se vzdy overuje, ze cilova operace neni dokoncena; pri poruseni je transakce oznacena jako `failed` se srozumitelnou hlaskou.
- Why: Hard-stop prevence proti vykazovani do uzavrenych operaci je business kriticka.

- Date: 2026-02-27
- Decision: Qty validace pro overrun pracuje s celkovym vykazem `hotove + zmetky` (ne pouze hotove), stejna logika je i ve FE STOP formulari.
- Why: Zabraňuje obejití limitu pres pole zmetku a odpovida realnemu odvodu kusu.

- Date: 2026-02-27
- Decision: Queue table row key byl rozšířen (`Job/Suffix/Oper/OpDatumSt/StateAsd/index`) a aktivni radek se urcuje referencne.
- Why: Infor muze vratit vice planovanych radku pro stejnou operaci (napr. setup/production bloky); puvodni key je kolaboval do jednoho vizualniho radku.

- Date: 2026-02-27
- Decision: Fallback na `SLJobRoutes` byl odstraněn jak ve fronte (`fetch_wc_queue`), tak v detailu operací (`fetch_job_operations`); při nedostupném `IteCzTsdJbrDetails` endpoint vrací chybu.
- Why: Fallback vracel operace mimo skutečný rozvrh (včetně dokončených), což je business-kriticky nebezpečné; preferována je fail-fast strategie před tichou nekonzistencí dat.

## Otevřené body

- Ověřit na reálném TEST Inforu, že `Mchtrx(H/J)` se skutečně propisuje do strojního běhu pro konkrétní WC/stroj (včetně varianty s `TMach`).
- Doplnit explicitní mapování `TMach` (a případně `IdMachine/ResId`) z výběru pracoviště/loginu, pokud Infor vyžaduje přesný identifikátor stroje.
- Rozšířit workshop UI o přímé zobrazení výkresů/dokumentace pro vybranou operaci.
- Zvážit navázání/odebírání operací na materiál přes lehký modal (bez inline dropdownu), pokud se tato úprava ukáže v praxi potřebná.
- Doplnit multi-page parser pro PDF vykresy (dnes primarne page 0) a deterministic fallback pro cteni razitka/materialu.
- Dopsat integracni testy pro SSH drawing import (status/preview/execute) se stub serverem.
- Otestovat na TEST Inforu edge-case: preodvod na pile u operace, ktera neni prvni (musi byt tvrde zablokovan backendem).
- Zvážit parametrizaci policy dle WC/operace do admin konfigurace (misto hardcoded prefixu `PS/PILA/SAW`).
- Ověřit na TEST Inforu konkrétní případ `21VP06/077`, že operace 5 na `PSv/PSV` po nasazení strict source zmizí z fronty i detailu operací.

## Další krok

- Provest E2E TEST scenar na dilne: overit, ze dokoncene operace nejsou ve fronte, ze post do dokoncene operace je blokovan, a rozhodnout UX policy pro dvojite radky stejne operace (ponechat oba vs. sloucit do jednoho summary radku).
- Provest rychly smoke test workshop endpointu proti TEST Inforu: `/workshop/queue` a `/workshop/operations` musi vratit pouze JBR rozvrh a pri vypadku JBR selhat s 502 (bez fallback dat).

- Date: 2026-02-27
- Decision: V technologickém tile byly odstraněny placeholder texty z inputů (parse input a časy operací) a potvrzeno, že `OperationCombobox` placeholder atribut nepoužívá.
- Why: Uživatel explicitně požadoval prostředí bez placeholder textu v těchto polích.

- Date: 2026-02-27
- Decision: Detail řádku operace (`Navázaný materiál`) už není placeholder; renderuje reálné navázané materiály z `materialItems.operations` včetně krátkého kódu (`materialShortRef`) a názvu.
- Why: Uživatel potřebuje okamžitě vidět vazbu materiál↔operace i v rozbaleném detailu operace.
