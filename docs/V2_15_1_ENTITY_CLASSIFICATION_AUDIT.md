# Syrian Airport Data Engine — Version 2.15.1
# Displayed Entity Classification & Airline vs. Organization Audit

## 1. Executive Summary

This audit establishes the rigorous classification of all 14 commercial and organizational entities appearing in the 1,982 records of the archived Damascus International Airport (DAM / OSDI) FIDS snapshot (`2026-07-05` to `2026-09-09`).

A critical mandate of Version 2.15.1 is eliminating misleading terminology—such as `Operating Airline Distribution` or `Operating Brands`—and replacing it universally with **`Displayed Airline / Organization Distribution`**.

Furthermore, this audit separates commercial passenger airlines from non-airline international bodies, specifically identifying and isolating the **United Nations (UN)** as a `humanitarian_organization`.

---

## 2. Terminology Standardization

### 2.1 Why "Operating Airline" Is Prohibited
In international aviation data engineering, an "Operating Carrier" refers strictly to the holder of the Air Operator Certificate (AOC) whose crew, airframe, and technical certificate conduct the flight.
Public airport flight information display systems (FIDS) display **commercial brand names** intended for passenger navigation:
- Code-shares often display the marketing carrier rather than the operating wet-lease carrier.
- Humanitarian or diplomatic entities display their organizational title rather than the chartered air carrier.
- Labeling FIDS entities as "Operating Airlines" produces false claims regarding certified Syrian market entry.

### 2.2 Standard Terminology Invariant
All reports, user interfaces, database documentation, and API schemas MUST employ:
- **`Displayed Airline / Organization Distribution`** (Primary metric label).
- **`Displayed Airline Brand`** (For commercial carriers).
- **`Humanitarian Organization`** (For non-commercial intergovernmental bodies).

---

## 3. Comprehensive Entity Census (14 Entities)

The staging database contains exactly 14 distinct entity identities:

| Arabic Name | English Display Name | IATA Code | Entity Classification | Scheduled Records | Share % | Arrivals | Departures | Distinct Flight Numbers | Active Days |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **طيران العربية** | **Air Arabia** | G9 | `commercial_airline_brand` | **509** | 25.68% | 256 | 253 | 12 | 67 |
| **فلاي ناس** | **Flynas** | XY | `commercial_airline_brand` | **382** | 19.27% | 191 | 191 | 13 | 63 |
| **فلاي دبي** | **flydubai** | FZ | `commercial_airline_brand` | **262** | 13.22% | 131 | 131 | 10 | 63 |
| **الخطوط التركية** | **Turkish Airlines** | TK | `commercial_airline_brand` | **252** | 12.71% | 126 | 126 | 7 | 63 |
| **أناضول جت** | **AJet** | VF | `commercial_airline_brand` | **180** | 9.08% | 90 | 90 | 5 | 63 |
| **الخطوط القطرية** | **Qatar Airways** | QR | `commercial_airline_brand` | **118** | 5.95% | 59 | 59 | 2 | 59 |
| **الاتحاد** | **Etihad Airways** | EY | `commercial_airline_brand` | **72** | 3.63% | 36 | 36 | 2 | 36 |
| **فلاي شام** | **Fly Cham** | XH | `commercial_airline_brand` | **62** | 3.13% | 31 | 31 | 31 | 6 |
| **السورية للطيران** | **Syrian Airlines** | RB | `commercial_airline_brand` | **43** | 2.17% | 22 | 21 | 29 | 5 |
| **دان أير** | **Dan Air** | DN | `commercial_airline_brand` | **36** | 1.82% | 18 | 18 | 3 | 18 |
| **طيران الجزيرة** | **Jazeera Airways** | J9 | `commercial_airline_brand` | **30** | 1.51% | 15 | 15 | 12 | 5 |
| **الملكية الأردنية** | **Royal Jordanian** | RJ | `commercial_airline_brand` | **20** | 1.01% | 10 | 10 | 8 | 5 |
| **فلاي إديل** | **Flyadeal** | F3 | `commercial_airline_brand` | **12** | 0.61% | 6 | 6 | 8 | 4 |
| **الأمم المتحدة** | **United Nations** | UN | `humanitarian_organization` | **4** | **0.20%** | **2** | **2** | **1** | **2** |
| **TOTAL** | — | — | — | **1,982** | **100.00%** | **993** | **989** | — | — |

*Source: Derived from `reports/v2_15_1_entity_reconciliation.csv`.*

---

## 4. Deep-Dive: Humanitarian Organization (United Nations)

The entity **United Nations** (الامم المتحدة, IATA code `UN`) accounts for exactly 4 scheduled records across the dataset:
- **Flight Identifier**: `UNO 501` (normalized to `UN501` / `UNO 501`).
- **Route**: Amman Queen Alia (AMM) $\leftrightarrow$ Damascus International (DAM).
- **Recorded Dates**:
  - `2026-07-06`: Arrival at 11:30 local; Departure at 12:30 local.
  - `2026-07-08`: Arrival at 11:30 local; Departure at 12:30 local.
- **Displayed Status**: `scheduled` (all 4 records).
- **Physical Movement Evidence**: `0` (archived timetable schedule; no radar or telemetry proof).

### Analytical Significance
United Nations Humanitarian Air Service (UNHAS) flights do not offer commercial public ticket sales and are operated for diplomatic, humanitarian aid, and peacekeeping personnel. Classifying the UN alongside commercial passenger airlines distorts market share, average daily frequencies, and commercial market recovery metrics. It is permanently isolated under `entity_classification: humanitarian_organization`.

---

## 5. Commercial Concentration Analysis

Excluding the United Nations, the 13 commercial passenger airline brands represent **1,978 records (99.80%)**:

1. **Top Tier (Gulf & Regional LCCs)**:
   - **Air Arabia** (509 flights, 25.68%): Operates daily flights across all 67 days connecting DAM with Sharjah (SHJ) and Abu Dhabi (AUH).
   - **Flynas** (382 flights, 19.27%): High-frequency Saudi connectivity (Riyadh RUH, Jeddah JED).
   - **flydubai** (262 flights, 13.22%): Daily rotations into Dubai International (DXB).
2. **Turkish Corridor**:
   - **Turkish Airlines** (252 flights, 12.71%) and **AJet** (180 flights, 9.08%) together account for 432 flights (21.79%), providing major transit capacity via Istanbul (IST) and Sabiha Gökçen (SAW).
3. **Syrian Carriers**:
   - **Fly Cham** (62 flights, 3.13%) and **Syrian Airlines** (43 flights, 2.17%) together represent only 105 flights (5.30%) of the scheduled records in this dataset, reflecting heavy concentration of foreign carrier capacity in the archived timetable snapshot.
