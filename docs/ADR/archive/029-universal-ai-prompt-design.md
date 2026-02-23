# ADR-029: Universal AI Prompt Design for Quote Parsing

**Status:** Implementovano
**Date:** 2026-02-02
**Souvisi s:** ADR-028

---

## Context

Puvodni prompt v `quote_request_parser.py` (ADR-028) byl specificiky pro cestinu — obsahoval hardcoded "KOVO RYBKA s.r.o.", ceske popisky poli a konkretni format RFQ "P17992". Pozadavek: prompt musi fungovat pro libovolny jazyk, zemi a format B2B poptavky bez udrzby.

---

## Decision

Nahradit keyword-matching prompty **semantickym porozumenim** — document layout je universalni, textu pouzity jazyk neni.

### Principy

**1. Role-based identifikace (ne string-matching)**
- ZAKAZNIK = ten, kdo poptavku POSILÁ (kupujici)
- DODAVATEL = ten, kdo dokument VYTVARI (prodavajici, ignorovat)
- Prostorove clue: header/footer zona = dodavatel, telo dokumentu = zakaznik
- Frekvencni clue: firma se 3+ vyskyty = dodavatel

**2. Vicejazycne vzory (jazyk-agnosticke)**
- Business ID: evropske VAT (`CZ12345678`, `DE123456789`), US EIN, UK Company No., asijske formaty
- RFQ cisla: `RFQ`, `P`, `Q`, `REQ`, `報價`, `見積`, `Nr.`, `#` — vsechny varianty
- Data: ISO, europsky (`15.03.2026`), US (`03/15/2026`), asijsky (`2026年3月15日`)

**3. Pozicni parsovani tabulky (ne nazvy sloupcu)**
- LEVA 30% = identifikatory (article_number)
- STREDNI 40% = popisy (name)
- PRAVA 30% = mnozstvi (quantity)

**4. Confidence scoring s rubrikou**
- 0.95-1.00: jasne, bez nejednoznacnosti
- 0.80-0.94: citelne, mensi nejednoznacnost
- 0.50-0.79: castecne nejasne nebo odvozene
- 0.00-0.49: hadani nebo velmi nejiste

**5. Anti-patterns sekce (explicitni zapovedi AI)**
- NIKDY neextrahovat dodavatele jako zakaznika
- NIKDY slucovat duplicitni article_numbers
- NIKDY vymyslet nebo auto-opravovat data
- NIKDY ignorovat dodaci adresy

### Zmena promptu

Soubor: `app/services/quote_request_parser.py`
- `QUOTE_REQUEST_PROMPT`: 147 radku -> 335 radku strukturovanych jako 7 pravidel
- Odstraneny vsechny ceske hardcoded priklady
- Pridany 3 genericke priklady (anglicky, cinsky, nemecky)

---

## Key Files

- `app/services/quote_request_parser.py` — jediny upraveny soubor (promenna `QUOTE_REQUEST_PROMPT`)

---

## Consequences

- Prompt funguje pro libovolny jazyk bez modifikace
- Zadne hardcoded nazvy firem ani klicova slova k aktualizaci
- Prompt je o 188 radku delsi → mirne vyssi tokenove naklady
- Potreba regresniho testovani na ceskych PDF po nasazeni
- Semanticky pristup je narocnejsi na debugging pri selhanich

---

## Alternatives Rejected

- **Fine-tuned model** — vyzaduje 100+ labeled PDF, drahy na udrzbu
- **Multi-stage parsing** — 3x API calls = 3x naklady
- **Jazykove-specificke prompty** — N promptu pro N jazyku, neudrzovatelne
