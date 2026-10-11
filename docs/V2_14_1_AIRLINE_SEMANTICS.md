# Syrian Airport Data Engine — Version 2.14.1
# Airline Field Semantics & Displayed Brand Distribution

## 1. Executive Summary

This audit assesses the semantic meaning of the `airline` field in the archived Damascus International Airport (`DAM` / `OSDI`) FIDS snapshot (`https://damairport.gov.sy/api/flights.php`).

The investigation confirms that the source field represents the **Displayed Airline Brand** presented to airport passengers on physical terminal monitors and the public web portal. It does **not** provide verified evidence of the underlying operating air carrier (AOC holder), wet-lease operator (ACMI), or operating aircraft equipment.

In accordance with strict aviation data governance rules:
1. All reporting terminology has been formally renamed from `Operating Airline Distribution` to **`Displayed Airline Distribution`**.
2. Original Arabic brand names and source IATA codes are strictly preserved.
3. Operating carriers are **never inferred** from flight numbers.
4. Independent airline brands are **never merged**, even if they share common corporate ownership or alliance agreements.

---

## 2. Carrier Role Classification Analysis

Aviation data models recognize distinct carrier roles for every commercial air service:

| Carrier Role Concept | Definition in Civil Aviation | Present in DAM FIDS Snapshot? | Evidentiary Basis |
| :--- | :--- | :--- | :--- |
| **Operating Carrier** | The legal entity holding the Air Operator Certificate (AOC) operating the airframe | **NO** | Zero aircraft tail registrations, zero ICAO 3-letter operator codes, zero crew filings |
| **Marketing Carrier** | The ticketing airline selling seats under commercial codeshare agreements | **PARTIAL** | Only the primary commercial marketing brand displayed on the flight board |
| **Displayed Airline Brand** | The commercial name and logo presented to travelers on airport FIDS displays | **YES (100%)** | Matches the public portal's passenger display filters (`nameAr`, `nameEn`) |
| **Wet-Lease Operator (ACMI)** | Third-party carrier providing aircraft, crew, maintenance, and insurance | **NO** | Unavailable in public FIDS feed |

### Source Schema Evidence

The snapshot contains an embedded portal configuration array (`airlines`), linking Arabic labels to passenger search filters:
```json
{
  "publicId": "75dd2e9272f4f541",
  "filter": "Syrian Airlines",
  "nameAr": "السورية للطيران",
  "nameEn": "Syrian Airlines"
}
```

The flight objects themselves populate the `airline` attribute with the Arabic string (e.g., `"طيران العربية"`, `"فلاي شام"`). This proves that the field is purely a display presentation attribute.

---

## 3. Strict Semantic Policies Implemented in V2.14.1

### Policy 1: No Operating Carrier Inference
It is common in unverified datasets to assume that because a flight begins with `G9` it is operated by Air Arabia Sharjah, or `VF` by AJet. However, commercial operations in Damascus frequently involve wet-lease operations (e.g. Dan Air operations, charter agreements, or seasonal ACMI wet-leases). In the absence of ADS-B transponder hex codes or official civil aviation authority operator filings, **no operating carrier is inferred**.

### Policy 2: No Airline Brand Merging
Brands sharing parent organizations or operating agreements are kept strictly separate:
- **Turkish Airlines** (`الخطوط التركية`, 252 flights) and **AJet** (`أناضول جت`, 180 flights) remain distinct entities.
- **Air Arabia** (`طيران العربية`, 509 flights) includes rotations with both `G9` and `3L` flight numbers; the displayed brand is preserved as published by the airport authority.
- **Flynas** (`فلاي ناس`, 382 flights) and **Flyadeal** (`فلاي إديل`, 12 flights) remain distinct Saudi carriers.

---

## 4. Displayed Airline Distribution (Reconciled to 1,982)

The 14 displayed airline brands appearing in the 1,982 flight records reconcile completely:

| Displayed Airline Brand (Arabic) | Displayed Airline Brand (English) | Source IATA | Role Classification | Operating Carrier Verified? | Total Flights | Share of Total | Arrivals | Departures | Unique Flight Nos. |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **طيران العربية** | Air Arabia | `G9` | `displayed_airline_brand` | `FALSE` | 509 | 25.68% | 256 | 253 | 12 |
| **فلاي ناس** | Flynas | `XY` | `displayed_airline_brand` | `FALSE` | 382 | 19.27% | 191 | 191 | 13 |
| **فلاي دبي** | flydubai | `FZ` | `displayed_airline_brand` | `FALSE` | 262 | 13.22% | 131 | 131 | 10 |
| **الخطوط التركية** | Turkish Airlines | `TK` | `displayed_airline_brand` | `FALSE` | 252 | 12.71% | 126 | 126 | 7 |
| **أناضول جت** | AJet | `VF` | `displayed_airline_brand` | `FALSE` | 180 | 9.08% | 90 | 90 | 5 |
| **الخطوط القطرية** | Qatar Airways | `QR` | `displayed_airline_brand` | `FALSE` | 118 | 5.95% | 59 | 59 | 2 |
| **الاتحاد** | Etihad Airways | `EY` | `displayed_airline_brand` | `FALSE` | 72 | 3.63% | 36 | 36 | 2 |
| **فلاي شام** | Fly Cham | `XH` | `displayed_airline_brand` | `FALSE` | 62 | 3.13% | 31 | 31 | 31 |
| **السورية للطيران** | Syrian Airlines | `RB` | `displayed_airline_brand` | `FALSE` | 43 | 2.17% | 22 | 21 | 29 |
| **دان أير** | Dan Air | `DN` | `displayed_airline_brand` | `FALSE` | 36 | 1.82% | 18 | 18 | 3 |
| **طيران الجزيرة** | Jazeera Airways | `J9` | `displayed_airline_brand` | `FALSE` | 30 | 1.51% | 15 | 15 | 12 |
| **الملكية الأردنية** | Royal Jordanian | `RJ` | `displayed_airline_brand` | `FALSE` | 20 | 1.01% | 10 | 10 | 8 |
| **فلاي إديل** | Flyadeal | `F3` | `displayed_airline_brand` | `FALSE` | 12 | 0.61% | 6 | 6 | 8 |
| **الأمم المتحدة** | United Nations | `UN` | `displayed_airline_brand` | `FALSE` | 4 | 0.20% | 2 | 2 | 1 |
| **TOTAL** | — | — | — | — | **1,982** | **100.00%** | **993** | **989** | — |

---

## 5. Machine-Readable Export Reference

This breakdown is permanently recorded in [`reports/v2_14_1_airline_distribution.csv`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/reports/v2_14_1_airline_distribution.csv).
All rows include the explicit columns `carrier_role_classification = 'displayed_airline_brand'` and `is_operating_carrier_verified = FALSE`.
