# Infor IDO → Gestima Field Mapping

> Analýza 22. 2. 2026 — Live data z Infor CloudSuite Industrial (SyteLine)
> API: `https://util90110.kovorybka.cz/IDORequestService/MGRestService.svc`
> Config: LIVE

## Stav: Co už importujeme vs co je dostupné

| IDO | Polí celkem | Importujeme | % využití |
|-----|-------------|-------------|-----------|
| SLItems (díly) | 552 (396 std + 47 Ryb + 109 Der) | 6 polí | 1.1% |
| SLItems (materiály) | 552 | 2 pole (!!) | 0.4% |
| SLCustomers | 320 (285 std + 35 Der) | 0 | 0% |
| SLVendors | 266 (229 std + 37 Der) | 0 | 0% |
| SLJobs | 371 (296 std + 2 Ryb + 73 Der) | 0 (přes SLJobRoutes) | 0% |
| SLCoItems (objednávky) | 610 (429 std + 37 Ryb + 144 Der) | 0 | 0% |
| SLPoItems (nákup) | 359 (285 std + 74 Der) | jen pro purchase prices | <1% |
| SLShipments | 193 (178 std + 15 Der) | 0 | 0% |

---

## 1. SLItems → Part (díly)

### Aktuálně importováno (6 polí)
```
Item           → article_number
Description    → name
DrawingNbr     → drawing_number
Revision       → customer_revision
RybTridaNazev1 → status (Nabídka/Aktivní)
FamilyCode     → (filtr: "Výrobek")
```

### Doporučeno přidat — Priorita NYNÍ

| Infor pole | Typ | Gestima pole (nové) | Proč |
|------------|-----|---------------------|------|
| **MatlType** | String | `item_type` | M=manufactured, P=purchased — základ pro rozlišení |
| **UM** | String | `uom` | Jednotka měření (EA, KG, M) — nutné pro objednávky |
| **UnitWeight** | Decimal | `weight_kg` | Hmotnost kusu — pro expedici, kalkulace |
| **UnitCost** | Decimal | `unit_cost` | Aktuální nákladová cena z Inforu |
| **ProdType** | String | `prod_type` | Typ výroby (J=job, R=repetitive, blank=purchased) |
| **Stat** | String | (mapovat na `status`) | A=active, O=obsolete, AI=active inhibit |
| **LeadTime** | Decimal | `lead_time_days` | Průběžná doba výroby (dny) |
| **ExpLeadTime** | Decimal | `exp_lead_time_days` | Očekávaná průběžná doba (plánovací) |
| **ProductCode** | String | `product_code` | Kód výrobku (pro účetnictví/statistiky) |
| **Buyer** | String | `buyer` | Nákupčí (pro materiály) |
| **RecordDate** | DateTime | (delta sync — už používáme) | — |

### Doporučeno přidat — Priorita BRZY

| Infor pole | Typ | Gestima pole (nové) | Proč |
|------------|-----|---------------------|------|
| **LotTracked** | Boolean | `lot_tracked` | Sledování šarží |
| **SerialTracked** | Boolean | `serial_tracked` | Sledování sériových čísel |
| **TaxCode1** | String | `tax_code` | DPH kód — nutné pro fakturaci |
| **CommCode** | String | `customs_code` | Celní kód (Intrastat/export) |
| **Country** | String | `country_of_origin` | Země původu |
| **CostMethod** | String | `cost_method` | Metoda oceňování (A=average, S=standard, L=LIFO, F=FIFO) |
| **AbcCode** | String | `abc_code` | ABC klasifikace (A/B/C) |

### Custom pole (Ryb*) — specifické pro Kovorybka

| Infor pole | Gestima využití |
|------------|-----------------|
| **RybTridaNazev1** | Už importujeme → status |
| **RybCustName** | Jméno zákazníka na položce |
| **RybCustNum** | Číslo zákazníka → vazba Partner |
| **RybCustEndUser** | Koncový uživatel |
| **RybMatNormaKod** | Kód normy materiálu |
| **RybMatNormaNazev1-7** | Názvy norem materiálu (více variant) |
| **RybDwgExists** | Existuje výkres? (boolean check) |
| **RybDrawOK** | Výkres schválen? |
| **RybMatOK** | Materiál schválen? |
| **RybBalListOK** | Balicí list schválen? |
| **RybKooNote** | Kooperační poznámka |
| **RybKooValue** | Kooperační hodnota |
| **RybPackCustMain** | Hlavní zákaznické balení |
| **RybDatPoslTran** | Datum poslední transakce |

### Inventory pole (stav skladu) — z SLItems

| Infor pole | Popis | Potřeba |
|------------|-------|---------|
| **iwvQtyOnHand** | Ks na skladě | NYNÍ — zobrazit v UI |
| **iwvQtyAllocCo** | Rezervováno pro objednávky | NYNÍ |
| **iwvQtyOrdered** | Objednáno (čeká na příjem) | NYNÍ |
| **iwvQtyWip** | V rozpracované výrobě | NYNÍ |
| **iwvQtyRsvdCo** | Rezervováno pro zákazníky | BRZY |
| **iwvQtySoldYtd** | Prodáno letos | STATISTIKA |
| **iwvQtyPurYtd** | Nakoupeno letos | STATISTIKA |
| **ITWHQtyOnHand** | Qty on hand (jiný view) | alternativa k iwv* |

### Cenová pole — z SLItems

| Infor pole | Popis | Potřeba |
|------------|-------|---------|
| **UnitCost** | Celkový unit cost | NYNÍ |
| **MatlCost** | Materiálový náklad | NYNÍ |
| **LbrCost** | Přímá práce | NYNÍ |
| **FovhdCost** | Fixní režie | BRZY |
| **VovhdCost** | Variabilní režie | BRZY |
| **OutCost** | Kooperace | BRZY |
| **CurUCost** | Aktuální unit cost | NYNÍ |
| **AvgUCost** | Průměrný unit cost | STATISTIKA |
| **LstUCost** | Poslední unit cost | STATISTIKA |
| **PriUnitPrice1-6** | Cenové hladiny 1-6 | BUDOUCÍ (pricing) |

---

## 2. SLItems → MaterialItem (materiály)

### Aktuálně importováno (2 pole !!)
```
Item           → code (parsujeme rozměry z Item kódu)
Description    → name (parsujeme tvar, normu, rozměry)
```
*Všechno ostatní (rozměry, tvar, norma, dodavatel) se parsuje regexem z Item/Description!*

### Doporučeno přidat — Priorita NYNÍ

| Infor pole | Typ | Gestima pole | Proč |
|------------|-----|-------------|------|
| **UM** | String | `uom` | Jednotka (KG, M, EA) — kritické pro výpočty |
| **UnitWeight** | Decimal | `unit_weight` | Váha jednotky |
| **Density** | Decimal | (porovnat s naší hustotou) | Hustota z Inforu |
| **UnitCost** | Decimal | `unit_cost` | Nákupní cena |
| **CurMatlCost** | Decimal | `current_material_cost` | Aktuální materiálový náklad |
| **VenVendNum** | String | `primary_vendor_num` | Primární dodavatel → FK na Partner |
| **Stat** | String | `infor_status` | Status v Inforu |
| **iwvQtyOnHand** | Decimal | `stock_available` (vylepšit!) | AKTUÁLNÍ stav skladu (ne jen text) |
| **ReorderPoint** | Decimal | `reorder_point` | Bod objednání |
| **LotSize** | Decimal | `lot_size` | Objednací dávka |
| **LeadTime** | Decimal | `lead_time_days` | Dodací lhůta od dodavatele |
| **itmuf_ite_cz_norma** | String | `norms` (vylepšit) | CZ norma z Inforu (už parsujeme, ale toto je autoritativní) |
| **itmuf_ite_cz_jakost** | String | `grade` | Jakost (CZ specifické) |

### Rozměrová pole v SLItems

| Infor pole | Popis | Relevance |
|------------|-------|-----------|
| **HeightLinearDimension** | Výška | Můžeme porovnat s parserem |
| **WidthLinearDimension** | Šířka | Můžeme porovnat s parserem |
| **LengthLinearDimension** | Délka | Standard length |
| **LinearDimensionUM** | Jednotka rozměrů | mm/cm/m |
| **BulkMass** | Hmotnost volně ložená | Specifické |
| **Area** | Plocha | Specifické |

---

## 3. SLCustomers → Partner (zákazníci)

### Aktuálně: 0 sync, manuální zadávání

### Doporučeno přidat — Priorita NYNÍ

| Infor pole | Typ | Gestima pole | Proč |
|------------|-----|-------------|------|
| **CustNum** | String(7) | `infor_cust_num` | Klíč pro vazbu Infor ↔ Gestima |
| **Name** | String(60) | `company_name` | Název firmy |
| **Addr_1, Addr_2** | String | `street` | Adresa (spojit) |
| **City** | String | `city` | Město |
| **State** | String | `state` (nové) | Stát/region |
| **Zip** | String | `postal_code` | PSČ |
| **Country** | String | `country` | Země |
| **Phone_1** | String | `phone` | Telefon |
| **FaxNum** | String | `fax` (nové) | Fax (stále se používá v průmyslu) |
| **Contact_1** | String | `contact_person` | Kontaktní osoba |
| **CustomerEmailAddr** | String | `email` | Email |
| **InternetUrl** | String | `website` (nové) | Web |
| **CurrCode** | String(3) | `currency` (nové) | Měna (CZK/EUR/USD) — KRITICKÉ |
| **TermsCode** | String | `payment_terms` (nové) | Platební podmínky |
| **CreditLimit** | Decimal | `credit_limit` (nové) | Kreditní limit |
| **CreditHold** | Boolean | `credit_hold` (nové) | Blokace kreditu |
| **TaxRegNum1** | String | `dic` | DIČ/VAT ID |
| **TaxCode1** | String | `tax_code` (nové) | DPH kód |
| **Slsman** | String | `sales_person` (nové) | Obchodník |
| **Delterm** | String | `delivery_terms` (nové) | Dodací podmínky (Incoterms) |
| **ShipCode** | String | `ship_code` (nové) | Kód dopravy |
| **Pricecode** | String | `price_code` (nové) | Cenová skupina |
| **CustType** | String | `customer_type` (nové) | Typ zákazníka |
| **LangCode** | String | `language` (nové) | Jazyk komunikace |
| **Stat** | (derived?) | (status) | Status zákazníka |
| **BankCode** | String | `bank_code` (nové) | Kód banky |
| **BankAcctNo** | String | `bank_account` (nové) | Číslo účtu |

### Doporučeno přidat — Priorita BRZY

| Infor pole | Typ | Gestima pole | Proč |
|------------|-----|-------------|------|
| **Contact_2, Contact_3** | String | (více kontaktů) | CRM základ |
| **Phone_2, Phone_3** | String | (další telefony) | CRM |
| **SalesYtd** | Decimal | `sales_ytd` | Obrat YTD (statistika) |
| **SalesLstYr** | Decimal | `sales_last_year` | Obrat minulý rok |
| **LastInv** | Date | `last_invoice_date` | Datum posl. faktury |
| **AvgDaysOs** | Decimal | `avg_days_outstanding` | Průměrná splatnost |
| **OrderCreditLimit** | Decimal | `order_credit_limit` | Limit na objednávky |
| **ShipPartial** | Boolean | `allow_partial_ship` | Povolit částečnou expedici |
| **ShipEarly** | Boolean | `allow_early_ship` | Povolit předčasnou expedici |
| **Consolidate** | Boolean | `consolidate_invoices` | Konsolidace faktur |
| **InvFreq** | String | `invoice_frequency` | Frekvence fakturace |
| **CorpCust** | Boolean | `is_corporate` | Korporátní zákazník |
| **TerritoryCode** | String | `territory` | Obchodní teritorium |

---

## 4. SLVendors → Partner (dodavatelé)

### Aktuálně: 0 sync

### Doporučeno přidat — Priorita NYNÍ

| Infor pole | Typ | Gestima pole | Proč |
|------------|-----|-------------|------|
| **VendNum** | String(7) | `infor_vend_num` | Klíč pro vazbu |
| **Name** | String(60) | `company_name` | Název |
| **VadAddr_1, VadAddr_2** | String | `street` | Adresa |
| **VadCity** | String | `city` | Město |
| **VadState** | String | `state` | Stát |
| **VadZip** | String | `postal_code` | PSČ |
| **VadCountry** | String | `country` | Země |
| **Phone** | String | `phone` | Telefon |
| **Contact** | String | `contact_person` | Kontakt |
| **ExternalEmailAddr** | String | `email` | Email |
| **CurrCode** | String(3) | `currency` | Měna |
| **TermsCode** | String | `payment_terms` | Platební podmínky |
| **TaxRegNum1** | String | `dic` | DIČ |
| **TaxCode1** | String | `tax_code` | DPH kód |
| **Delterm** | String | `delivery_terms` | Dodací podmínky |
| **Category** | String | `vendor_category` (nové) | Kategorie dodavatele |
| **Stat** | String | (status) | Status |
| **Buyer** | String | `buyer` (nové) | Přidělený nákupčí |
| **PurchYtd** | Decimal | `purchases_ytd` | Nákupy YTD |
| **PurchLstYr** | Decimal | `purchases_last_year` | Nákupy min. rok |

---

## 5. SLCoItems → Objednávky (BUDOUCÍ)

### Klíčová pole pro budoucí import zakázek

| Infor pole | Popis | Priorita |
|------------|-------|----------|
| **CoNum** | Číslo objednávky | ZÁKLAD |
| **CoLine** | Řádek objednávky | ZÁKLAD |
| **Item** | Položka | ZÁKLAD |
| **Description** | Popis | ZÁKLAD |
| **QtyOrdered** | Objednané množství | ZÁKLAD |
| **QtyShipped** | Expedované množství | ZÁKLAD |
| **Price** | Cena | ZÁKLAD |
| **DueDate** | Požadovaný termín | ZÁKLAD |
| **PromiseDate** | Slíbený termín | ZÁKLAD |
| **Stat** | Status řádku | ZÁKLAD |
| **CustNum** | Zákazník | ZÁKLAD |
| **CustPo** | Zákaznická objednávka | ZÁKLAD |
| **CoOrderDate** | Datum objednávky | ZÁKLAD |
| **Job** | Výrobní příkaz | VAZBA na SLJobs |
| **Cost** | Náklad | KALKULACE |
| **Margin** | Marže | KALKULACE |
| **MarginPercent** | Marže % | KALKULACE |
| **TaxCode1** | DPH | FAKTURACE |
| **Delterm** | Dodací podmínky | LOGISTIKA |
| **ShipDate** | Datum expedice | LOGISTIKA |

### Custom Ryb* pole na SLCoItems

| Pole | Popis |
|------|-------|
| **RybAktivWf** | Aktivní workflow |
| **Ryb0-6 Bit/Date/User** | 7 workflow checkpointů (bit=hotovo, date=kdy, user=kdo) |
| **coiuf_ite_cz_ryb_cislo_obj** | CZ číslo objednávky |
| **coiuf_ite_cz_ryb_pozice** | Pozice |
| **coiuf_ite_cz_ryb_confirm_date** | Datum potvrzení |
| **coiuf_ite_cz_ryb_deadline_date** | Deadline |
| **coiuf_ite_cz_ryb_stat** | CZ status |
| **coiuf_ite_cz_ryb_protocol_required** | Vyžadován protokol |

---

## 6. SLJobs → Výrobní příkazy (rozšíření stávajícího syncu)

### Aktuálně importujeme přes SLJobRoutes (operace) — NE přímo SLJobs

### Klíčová pole z SLJobs pro budoucí import

| Infor pole | Popis | Priorita |
|------------|-------|----------|
| **Job** | Číslo VP | ZÁKLAD |
| **Suffix** | Suffix VP | ZÁKLAD |
| **Item** | Položka | ZÁKLAD |
| **Stat** | Status (R=released, S=started, C=complete) | ZÁKLAD |
| **Type** | Typ (S=standard, R=rework) | ZÁKLAD |
| **QtyReleased** | Uvolněné množství | ZÁKLAD |
| **QtyComplete** | Dokončené množství | ZÁKLAD |
| **QtyScrapped** | Zmetky | KVALITA |
| **CustNum** | Zákazník (pokud job-to-order) | VAZBA |
| **OrdNum** | Číslo objednávky | VAZBA |
| **OrdLine** | Řádek objednávky | VAZBA |
| **JobDate** | Datum VP | PLÁNOVÁNÍ |
| **JschStartDate** | Plánovaný start | PLÁNOVÁNÍ |
| **JschEndDate** | Plánovaný konec | PLÁNOVÁNÍ |
| **WipTotal** | WIP celkem | ÚČETNICTVÍ |
| **WipMatlTotal** | WIP materiál | ÚČETNICTVÍ |
| **WipLbrTotal** | WIP práce | ÚČETNICTVÍ |

---

## 7. SLPoItems → Nákupní objednávky (rozšíření)

### Aktuálně: jen pro purchase price analysis

### Klíčová pole pro kompletní nákupní cyklus

| Infor pole | Popis | Priorita |
|------------|-------|----------|
| **PoNum** | Číslo PO | ZÁKLAD |
| **PoLine** | Řádek PO | ZÁKLAD |
| **Item** | Položka | ZÁKLAD |
| **QtyOrdered** | Objednáno | ZÁKLAD |
| **QtyReceived** | Přijato | ZÁKLAD |
| **ItemCost** | Cena za jednotku | ZÁKLAD |
| **DueDate** | Požadovaný termín | ZÁKLAD |
| **PoVendNum** | Dodavatel | VAZBA |
| **Stat** | Status | ZÁKLAD |
| **RcvdDate** | Datum příjmu | LOGISTIKA |

---

## 8. SLShipments → Expedice (BUDOUCÍ)

| Infor pole | Popis | Priorita |
|------------|-------|----------|
| **ShipmentId** | ID zásilky | ZÁKLAD |
| **CustNum** | Zákazník | ZÁKLAD |
| **ShipDate** | Datum expedice | ZÁKLAD |
| **Status** | Status | ZÁKLAD |
| **TrackingNumber** | Číslo sledování | LOGISTIKA |
| **CarrierName** | Dopravce | LOGISTIKA |
| **Weight** | Hmotnost | LOGISTIKA |
| **QtyPackages** | Počet balíků | LOGISTIKA |

---

## Shrnutí: Co přidat NYNÍ (v dalším sprintu)

### Nová pole v modelech:

**Part** (+8 polí):
- `item_type` (M/P), `uom`, `weight_kg`, `unit_cost`, `prod_type`
- `lead_time_days`, `product_code`, `infor_item_id` (pro cross-ref)

**MaterialItem** (+6 polí):
- `uom`, `unit_cost`, `primary_vendor_num`, `reorder_point`
- `lot_size`, `lead_time_days`

**Partner** (+14 polí):
- `infor_cust_num`, `infor_vend_num` (Infor reference keys)
- `currency`, `payment_terms`, `credit_limit`, `credit_hold`
- `tax_code`, `delivery_terms`, `ship_code`, `price_code`
- `sales_person`, `customer_type`, `fax`, `website`

### Nové sync kroky:
1. **customers** — SLCustomers → Partner (is_customer=true)
2. **vendors** — SLVendors → Partner (is_supplier=true)

### Rozšířené sync kroky:
1. **parts** — přidat MatlType, UM, UnitWeight, UnitCost, ProdType, Stat, LeadTime
2. **materials** — přidat UM, UnitCost, VenVendNum, iwvQtyOnHand, ReorderPoint, Density

### Celkem: ~28 nových polí + 2 nové sync kroky
