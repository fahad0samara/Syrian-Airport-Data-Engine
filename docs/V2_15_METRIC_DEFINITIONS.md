# Syrian Airport Data Engine — Version 2.15
# Analytics Metric Definitions & Mathematical Formulas

## 1. Overview

This document provides formal mathematical definitions, SQL formulations, and data interpretation rules for all metrics exposed by the Archived FIDS Analytics Layer.

---

## 2. Daily Schedule Metrics

Calculated for each calendar date $d \in [\text{2026-07-05}, \text{2026-09-09}]$ (67 dates):

### Total Scheduled Records ($N_d$)
The count of all flight objects published in the airport timetable for date $d$:
$$N_d = \sum_{r \in R_d} 1$$
$$\text{SQL: } \texttt{COUNT(*)}$$

### Directional Breakdown
- **Arrival Records ($A_d$)**:
  $$A_d = \sum_{r \in R_d} \mathbf{1}_{\{\text{movement\_type} = \text{'arrival'}\}}$$
- **Departure Records ($D_d$)**:
  $$D_d = \sum_{r \in R_d} \mathbf{1}_{\{\text{movement\_type} = \text{'departure'}\}}$$
- Constraint: $A_d + D_d = N_d$.

### Schedule Variety
- **Unique Displayed Flight Numbers**:
  $$F_d = |\bigcup_{r \in R_d} \{\text{flight\_number}\}|$$
- **Unique Displayed Airline Brands**:
  $$B_d = |\bigcup_{r \in R_d} \{\text{airline\_name\_en}\}|$$

### Status Segregation
- **Scheduled Status Count**: $\sum \mathbf{1}_{\{\text{displayed\_status} = \text{'scheduled'}\}}$
- **Other Status Count**: $\sum \mathbf{1}_{\{\text{displayed\_status} \neq \text{'scheduled'}\}}$ (Exactly 1 record on `2026-07-06` with status `'arrived'`).

---

## 3. Displayed Airline Distribution Metrics

Calculated per displayed airline brand $b \in B$ (14 unique commercial brands):

### Brand Flight Volume ($N_b$)
$$N_b = \sum_{r \in R} \mathbf{1}_{\{\text{airline\_name\_en} = b\}}$$

### Percentage Share of Total Scheduled Records ($P_b$)
$$P_b = \left( \frac{N_b}{N_{\text{total}}} \right) \times 100\% = \left( \frac{N_b}{1,982} \right) \times 100\%$$

### Directional Split
- **Arrivals ($A_b$)**: Scheduled inbound services displaying brand $b$.
- **Departures ($D_b$)**: Scheduled outbound services displaying brand $b$.

### Operational Frequencies
- **Active Calendar Days ($K_b$)**:
  $$K_b = |\{ \text{scheduled\_date} \mid \exists r \in R \text{ s.t. } \text{airline}(r) = b \}|$$
- **Daily Frequency (Active Days)**:
  $$\text{Freq}_{\text{active}} = \frac{N_b}{K_b}$$
- **Daily Frequency (Full 67-Day Horizon)**:
  $$\text{Freq}_{67} = \frac{N_b}{67}$$

> **SEMANTIC RULE**: This metric is strictly labeled **Displayed Airline Distribution**. It must never be labeled *Operating Airline Distribution*, as the source data reflects passenger-facing brands rather than certified AOC holders.

---

## 4. Destination and Route Analysis Metrics

Routes are analyzed by origin-destination IATA pairs $(O, D)$ and direction $M \in \{\text{arrival}, \text{departure}\}$:

- For DAM Departures: $O = \text{'DAM'}$, $D \in \{\text{Destination Airports}\}$.
- For DAM Arrivals: $O \in \{\text{Origin Airports}\}$, $D = \text{'DAM'}$.

### Route Flight Volume
$$N_{(O, D, M)} = \sum_{r \in R} \mathbf{1}_{\{\text{origin} = O \land \text{destination} = D \land \text{movement} = M\}}$$

### Unique Flight Numbers on Route
$$F_{(O, D, M)} = |\{ \text{flight\_number} \mid r \in R \text{ on route } (O, D, M) \}|$$

### Distinct Operating Brands on Route
$$B_{(O, D, M)} = |\{ \text{airline\_name\_en} \mid r \in R \text{ on route } (O, D, M) \}|$$

---

## 5. Hourly Schedule Distribution Metrics

Hourly aggregation partitions scheduled records into 24 discrete one-hour bins based on the **original local Damascus wall-clock time** (`scheduled_time`, `Asia/Damascus` / `UTC+3`):

$$\text{HourBin}(h) = \{ r \in R \mid \lfloor \text{scheduled\_time}(r) \rfloor = h \}, \quad h \in [0, 23]$$

- Bin $h$ spans $[h\text{:00}, h\text{:59}]$.
- Grouping is executed directly on the string prefix `SUBSTR(scheduled_time, 1, 2)`.
- **Prohibition**: Original times are never converted to UTC before grouping, preserving the true local operational profile of Damascus International Airport.

---

## 6. Weekly Pattern Metrics

### Average Records per Calendar Day ($\mu_{\text{daily}}$)
$$\mu_{\text{daily}} = \frac{\sum_{d=1}^{67} N_d}{67} = \frac{1,982}{67} \approx 29.58\text{ flights/day}$$

### Average Directional Volumes
- Average Daily Arrivals: $\frac{993}{67} \approx 14.82\text{ arrivals/day}$
- Average Daily Departures: $\frac{989}{67} \approx 14.76\text{ departures/day}$

### Weekday Distribution ($W_j$)
For weekday $j \in \{0=\text{Monday}, \dots, 6=\text{Sunday}\}$:
$$\text{Average Flights}(j) = \frac{\sum_{d \in \text{Days}(j)} N_d}{|\text{Days}(j)|}$$

---

## 7. Duplicate Candidate Classification

Candidate pair identity:
- Record 1: UUID `e5ada70d-5245-46d4-b043-bf469c1d104f`, `G9 376`, `13:55`, `2026-07-08`, DAM $\rightarrow$ SHJ.
- Record 2: UUID `2d2a0935-da5e-42c4-ad15-e10b4e2291ee`, `376`, `13:55`, `2026-07-08`, DAM $\rightarrow$ SHJ.

### Classification: `possible_prefix_variant_duplicate`
Defined as two records sharing the same date, time slot, route pair, and displayed airline brand, where one entry contains the standard IATA carrier code prefix (`G9`) and the other contains only the numerical portion (`376`).

### Review Status: `requires_manual_review`
Indicates that while evidence strongly suggests a clerical duplicate in the source system, both records are preserved unaltered in the database to prevent unverified data destruction.
