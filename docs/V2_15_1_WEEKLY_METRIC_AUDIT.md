# Syrian Airport Data Engine — Version 2.15.1
# Weekly Metric Verification & Mathematical Reconciliation Audit

## 1. Executive Summary

This report establishes the verified weekday patterns across the 67 consecutive calendar days of the archived Damascus International Airport (DAM / OSDI) FIDS snapshot (`2026-07-05` through `2026-09-09`).

It audits the calculation of weekday averages, verifies the distribution of day occurrences, and provides rigorous mathematical reconciliation proving that the weighted weekday average reconciles with zero discrepancy to the overall daily flight average of **29.5821 flights/day**.

---

## 2. Weekday Census & Occurrence Breakdown

The 67-day temporal window starts on **Sunday, July 5, 2026** and concludes on **Wednesday, September 9, 2026**.

Because the window comprises 9 complete 7-day cycles (63 days) plus 4 additional days:
- **Sunday, Monday, Tuesday, and Wednesday** each occur **10 times**.
- **Thursday, Friday, and Saturday** each occur **9 times**.
- Total calendar days: $10 + 10 + 10 + 9 + 9 + 9 + 10 = 67$.

### Verified Weekday Reconciliation Table

| Weekday Index | Weekday Name | Occurrences | Total Records | Average Records/Day | Min Daily Count | Max Daily Count | Arrival Records | Departure Records |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0 | **Monday** | 10 | 295 | **29.50** | 2 | 69 | 149 | 146 |
| 1 | **Tuesday** | 10 | 286 | **28.60** | 2 | 60 | 143 | 143 |
| 2 | **Wednesday** | 10 | 287 | **28.70** | 2 | 63 | 144 | 143 |
| 3 | **Thursday** | 9 | 290 | **32.22** | 26 | 68 | 145 | 145 |
| 4 | **Friday** | 9 | 270 | **30.00** | 28 | 32 | 135 | 135 |
| 5 | **Saturday** | 9 | 232 | **25.78** | 24 | 26 | 116 | 116 |
| 6 | **Sunday** | 10 | 322 | **32.20** | 2 | 64 | 161 | 161 |
| **TOTAL** | — | **67** | **1,982** | — | **2** | **69** | **993** | **989** |

*Source: Derived from `reports/v2_15_1_weekday_reconciliation.csv`.*

---

## 3. Mathematical Reconciliation of Daily vs. Weekday Averages

### 3.1 Overall Daily Average
The dataset contains 1,982 total records across 67 days:
$$\mu_{\text{daily}} = \frac{1,982}{67} \approx 29.5820895522388 \dots \approx 29.5821$$

### 3.2 Weighted Weekday Average
Weighting each weekday's average flight volume by its actual occurrence count:
$$\text{Weighted Total} = \sum_{w=0}^{6} (\bar{x}_w \times N_w)$$
$$\text{Weighted Total} = (29.50 \times 10) + (28.60 \times 10) + (28.70 \times 10) + (32.2222 \dots \times 9) + (30.00 \times 9) + (25.7777 \dots \times 9) + (32.20 \times 10)$$
$$\text{Weighted Total} = 295.0 + 286.0 + 287.0 + 290.0 + 270.0 + 232.0 + 322.0 = 1,982.0$$

Dividing by total days (67):
$$\mu_{\text{weighted}} = \frac{1,982.0}{67} = 29.5820895522388 \dots = 29.5821$$

$$\text{Discrepancy} = |\mu_{\text{daily}} - \mu_{\text{weighted}}| = 0.00000000$$

### 3.3 Explanation of the Unweighted Discrepancy
If an analyst simply takes the unweighted arithmetic mean of the seven weekday averages:
$$\mu_{\text{unweighted}} = \frac{29.50 + 28.60 + 28.70 + 32.2222 + 30.00 + 25.7778 + 32.20}{7} = \frac{206.00}{7} \approx 29.4286$$

The unweighted average ($29.4286$) is $0.1535$ lower than the true daily average ($29.5821$). This occurs because:
1. Thursday, Friday, and Saturday occurred only 9 times, whereas the higher-volume days (Sunday with 10 occurrences and Monday through Wednesday) had 10 occurrences.
2. Saturday had the lowest average schedule volume (25.78 flights/day). In an unweighted mean, Saturday is given $\frac{1}{7}$ ($14.29\%$) weight, whereas in the 67-day calendar it represents only $\frac{9}{67}$ ($13.43\%$) of the actual days.
3. Therefore, all production dashboards and reports MUST present the weighted weekday average or explain the calendar-boundary weighting to prevent confusion.

---

## 4. Operational Schedule Insights

1. **Busiest Scheduled Weekdays**:
   - **Thursday** (32.22 flights/day): Heaviest weekday traffic, driven by weekend leisure and business rotations into Gulf hubs (Sharjah, Dubai, Doha, Riyadh).
   - **Sunday** (32.20 flights/day): Start of regional business week and major international transit schedule.
2. **Quietest Scheduled Weekday**:
   - **Saturday** (25.78 flights/day): Consistently low variation (min 24, max 26), reflecting reduced scheduled flights into European and regional routes.
3. **Mid-Week Steady State**:
   - Tuesday (28.60) and Wednesday (28.70) exhibit almost identical operating rhythms and balanced arrival/departure parity (143/143 on Tuesday, 144/143 on Wednesday).
