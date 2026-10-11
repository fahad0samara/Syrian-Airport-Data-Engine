# توثيق مصادر البيانات والاستعلامات التحليلية
## Syrian Airport Data Engine — Senior Data Analyst Reference Document
### الإصدار المحدث وفق المراجعة التحليلية المستقلة (V2.20.12 Final Audit)

> **تنبيه منهجي وحوكمة البيانات:**
> جميع الاستعلامات الواردة في هذا المستند نُفّذت حصراً بوضع القراءة فقط (`mode=ro`) على قاعدة البيانات التشغيلية الرسمية للمشروع:
> `data/damascus_airport.db`
> البصمة المشفرة الأصلية الثابتة: `c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b` (SHA-256).
> لم يتم إجراء أي تعديل، حذف، أو إدخال على جداول الإنتاج.

---

### 1. الاستعلامات التأسيسية لحجم البيانات وتوزيع المطارات

#### 1.1 إجمالي الأحداث التشغيلية حسب المطار
* **الهدف التحليلي:** حصر عدد الرحلات الإجمالي الموثق في النظام وتوزيعه الجغرافي.
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    airport_id, 
    COUNT(*) AS total_events
FROM flight_events
GROUP BY airport_id
ORDER BY total_events DESC;
```
* **النتائج المطابقة في التقرير:**
  - `DAM` (مطار دمشق الدولي): 1,563 سجلاً (85.41%)
  - `ALP` (مطار حلب الدولي): 261 سجلاً (14.26%)
  - `DEZ` (مطار دير الزور): 6 سجلات (0.33%)
  - **الإجمالي الكلي:** 1,830 سجلاً (100.00%)

#### 1.2 تصنيف طبيعة السجل (Record Nature) عبر المطارات
* **الهدف التحليلي:** التمييز الصارم بين الحركة الفعلية المرصودة عبر أدلة الرصد الراداري (ADS-B والتتبع التجاري)، والخدمات المجدولة، والرحلات التسويقية المشتركة، دون أي ادعاء بوجود مستشعرات أرضية على المدرج.
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    airport_id, 
    record_nature, 
    COUNT(*) AS count
FROM flight_events
GROUP BY airport_id, record_nature
ORDER BY airport_id, count DESC;
```
* **النتائج المطابقة في التقرير:**
  - `DAM`:
    * `scheduled_service`: 1,428 (714 وصول + 714 مغادرة)
    * `physical_movement`: 98 (48 وصول + 50 مغادرة)
    * `marketing_codeshare`: 34 (18 وصول + 16 مغادرة)
    * `unverified_movement`: 3 (2 وصول + 1 مغادرة)
    * **مجموع دمشق:** 1,563 سجلاً
  - `ALP`:
    * `scheduled_service`: 229
    * `physical_movement`: 32
    * **مجموع حلب:** 261 سجلاً
  - `DEZ`:
    * `scheduled_service`: 5
    * `physical_movement`: 1
    * **مجموع دير الزور:** 6 سجلات
  - **إجمالي الحركات الفعلية على مستوى القطر:** 131 حركة (98 + 32 + 1)
  - **إجمالي الخدمات المجدولة على مستوى القطر:** 1,662 خدمة (1,428 + 229 + 5)

#### 1.3 اتجاه الحركة الجوية وتوضيح مقام الإجمالي في دمشق
* **الهدف التحليلي:** إيضاح أساس رقم 782 وصولاً و 781 مغادرة بدمشق وفصل المجدول عن الفعلي.
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    airport_id, 
    record_nature,
    movement_type, 
    COUNT(*) AS count
FROM flight_events
WHERE airport_id = 'DAM'
GROUP BY record_nature, movement_type
ORDER BY record_nature, movement_type;
```
* **النتائج:**
  - `physical_movement`: 48 وصولاً | 50 مغادرة (المجموع: 98)
  - `scheduled_service`: 714 وصولاً | 714 مغادرة (المجموع: 1,428)
  - `marketing_codeshare`: 18 وصولاً | 16 مغادرة (المجموع: 34)
  - `unverified_movement`: 2 وصولاً | 1 مغادرة (المجموع: 3)
  - **الإجمالي الكلي لسجلات دمشق:** 782 وصولاً | 781 مغادرة (المجموع: 1,563)
  - **تنبيه إحصائي:** تشكل الخدمات المجدولة 91.36% من الوصول و 91.42% من المغادرة، وبالتالي فإن 782/781 تعبر عن إجمالي السجلات وليس عن هبوط وإقلاع مادي على المدرج.

---

### 2. استعلامات التحليل المتعمق لمطار دمشق الدولي (DAM Deep Dive)

#### 2.1 حالات الرحلات التشغيلية (Flight Status Distribution)
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    flight_status, 
    COUNT(*) AS count
FROM flight_events
WHERE airport_id = 'DAM'
GROUP BY flight_status
ORDER BY count DESC;
```
* **النتائج:**
  - `scheduled`: 1,403 (89.76%)
  - `landed`: 71 (4.54%)
  - `departed`: 50 (3.20%)
  - `active`: 23 (1.47%)
  - `unknown`: 10 (0.64%)
  - `cancelled`: 4 (0.26%)
  - `diverted`: 2 (0.13%)

#### 2.2 كبرى شركات الطيران تسويقاً في الجداول المجدولة (Marketing Airlines)
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    airline, 
    COUNT(*) AS count
FROM flight_events
WHERE airport_id = 'DAM' AND airline IS NOT NULL
GROUP BY airline
ORDER BY count DESC
LIMIT 10;
```
* **النتائج:**
  1. `Air Arabia`: 258
  2. `Flynas`: 214
  3. `Royal Jordanian`: 148
  4. `flydubai`: 130
  5. `Turkish Airlines`: 128
  6. `Fly Cham`: 123
  7. `Syrian Airlines`: 103 (شاملة السورية للطيران)
  8. `AJet`: 91
  9. `Jazeera Airways`: 72
  10. `Qatar Airways`: 68

#### 2.3 المشغلون الفعليون للحركات المؤكدة رادارياً (Operating Carriers - 98 Movements)
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    COALESCE(operating_carrier, airline) AS resolved_carrier, 
    COUNT(*) AS count
FROM flight_events
WHERE airport_id = 'DAM' AND record_nature = 'physical_movement'
GROUP BY resolved_carrier
ORDER BY count DESC;
```
* **النتائج:**
  1. `Air Arabia`: 14
  2. `Fly Cham`: 13
  3. `Syrian Airlines`: 12 (11 + 1 Syrian Air)
  4. `Royal Jordanian`: 10
  5. `flydubai`: 8
  6. `Turkish Airlines`: 8
  7. `Flynas`: 9 (8 + 1 flynas)
  8. `Flyadeal`: 6
  9. `Jazeera Airways`: 5
  10. `Qatar Airways`: 4
  11. `Kuwait Airline`: 4
  12. مشغلون آخرون (LEAV, Etihad, AJet, Dan Air): 5

#### 2.4 أبرز المسارات والوجهات المرتبطة بمطار دمشق بالتجميع الصريح برمز IATA
* **الهدف التحليلي:** التجميع الدقيق برمز IATA الصرف للمطار المقابل، وفصل الرحلات التشغيلية والمجدولة عن رحلات المشاركة بالرمز (Codeshares).
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    connected_airport_iata AS iata,
    COUNT(*) AS total_records,
    SUM(CASE WHEN record_nature != 'marketing_codeshare' THEN 1 ELSE 0 END) AS operational_and_scheduled,
    SUM(CASE WHEN record_nature = 'marketing_codeshare' THEN 1 ELSE 0 END) AS marketing_codeshare
FROM flight_events
WHERE airport_id = 'DAM'
GROUP BY connected_airport_iata
ORDER BY total_records DESC
LIMIT 10;
```
* **النتائج المحققة:**
  1. `SHJ` (مطار الشارقة الدولي): 229 (229 تشغيلية ومجدولة + 0 كودشير)
  2. `KWI` (مطار الكويت الدولي): 166 (166 تشغيلية ومجدولة + 0 كودشير)
  3. `DXB` (مطار دبي الدولي): 165 (157 تشغيلية ومجدولة + 8 كودشير)
  4. `AMM` (مطار الملكة علياء - عمّان): 160 (148 تشغيلية ومجدولة + 12 كودشير)
  5. `RUH` (مطار الملك خالد - الرياض): 158 (148 تشغيلية ومجدولة + 10 كودشير)
  6. `IST` (مطار إسطنبول الرئيسي): 143 (143 تشغيلية ومجدولة + 0 كودشير)
  7. `AUH` (مطار زايد الدولي - أبوظبي): 108 (108 تشغيلية ومجدولة + 0 كودشير)
  8. `SAW` (مطار صبيحة كوكجن - إسطنبول): 88 (88 تشغيلية ومجدولة + 0 كودشير)
  9. `JED` (مطار الملك عبد العزيز - جدة): 84 (82 تشغيلية ومجدولة + 2 كودشير)
  10. `DOH` (مطار حمد الدولي - الدوحة): 70 (70 تشغيلية ومجدولة + 0 كودشير)

#### 2.5 تصنيف الرحلات (دولية مقابل داخلية ومقام النسبة)
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
-- إجمالي سجلات دمشق
SELECT 
    route_type, 
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / 1563, 2) AS percentage
FROM flight_events
WHERE airport_id = 'DAM'
GROUP BY route_type;

-- الحركات الفعلية المرصودة بدمشق فقط
SELECT 
    route_type, 
    COUNT(*) AS count
FROM flight_events
WHERE airport_id = 'DAM' AND record_nature = 'physical_movement'
GROUP BY route_type;
```
* **النتائج:**
  - لإجمالي سجلات دمشق (1,563 سجلاً):
    * `international`: 1,555 سجلاً (99.49% = 1,555 / 1,563)
    * `domestic`: 8 سجلات (0.51% = 8 / 1,563)
  - للحركات الفعلية المرصودة فقط (98 حركة):
    * `international`: 98 حركة (100.00% = 98 / 98)
    * `domestic`: 0 حركة (0.00%)

#### 2.6 تحليل الطرازات وتوزيع عائلة Airbus A320 والمقام الإحصائي
* **الهدف التحليلي:** التمييز بين الطراز الأساسي والعائلة الموسعة، والإفصاح عن نسبة السجلات غير المحددة (NULL).
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    COUNT(*) AS total_dam_records,
    SUM(CASE WHEN aircraft_model IS NOT NULL THEN 1 ELSE 0 END) AS populated_models,
    SUM(CASE WHEN aircraft_model IS NULL THEN 1 ELSE 0 END) AS null_models,
    SUM(CASE WHEN aircraft_model IN ('320', 'Airbus A320-214', 'Airbus A320-232', 'Airbus A320-233', 'Airbus A320-212', 'Airbus A320-251N', 'Airbus A320-271N') THEN 1 ELSE 0 END) AS a320_base,
    SUM(CASE WHEN aircraft_model IN ('320', 'Airbus A320-214', 'Airbus A320-232', 'Airbus A320-233', 'Airbus A320-212', 'Airbus A320-251N', 'Airbus A320-271N', '32N', '32Q', 'A20N', '32S', 'Airbus A321-231') THEN 1 ELSE 0 END) AS a320_family_expanded
FROM flight_events
WHERE airport_id = 'DAM';
```
* **النتائج:**
  - إجمالي سجلات دمشق: 1,563 سجلاً.
  - السجلات محددة الطراز: 215 سجلاً فقط (13.75%).
  - السجلات غير محددة الطراز (`NULL`): 1,348 سجلاً (86.25%).
  - طراز `A320` الأساسي: 146 رحلة:
    * كنسبة من السجلات محددة الطراز: 146 / 215 = **67.91%**
  - عائلة `A320` الموسعة (بما فيها 32N, 32Q, A20N): 163 رحلة:
    * كنسبة من السجلات محددة الطراز: 163 / 215 = **75.81%**
  - عائلة `A320` الموسعة كنسبة من إجمالي كافة سجلات دمشق: 163 / 1,563 = **10.43%**

#### 2.7 تسجيلات الطائرات الأكثر رصداً على مدرج دمشق (98 حركة فعلية)
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    aircraft_registration, 
    operating_carrier,
    aircraft_model,
    COUNT(*) AS count
FROM flight_events
WHERE airport_id = 'DAM' 
  AND record_nature = 'physical_movement' 
  AND aircraft_registration IS NOT NULL
GROUP BY aircraft_registration
ORDER BY count DESC
LIMIT 7;
```
* **النتائج:**
  1. `YK-BAC` (أجنحة الشام - A320): 6 حركات
  2. `YK-AKG` (السورية للطيران - A320): 5 حركات
  3. `YK-BAA` (أجنحة الشام - A320): 4 حركات
  4. `YK-AKI` (السورية للطيران - A320): 4 حركات
  5. `JY-REG` (الملكية الأردنية - E195-E2): 4 حركات
  6. `A6-AUE` (العربية للطيران - A320): 4 حركات
  7. `YR-JUL` (Dan Air / عقد تشغيل): 3 حركات

---

### 3. استعلامات الجودة، الاكتمال، وأدلة الإثبات (Quality & Provenance)

#### 3.1 اكتمال الحقول ونسب القيم المفقودة في مطار دمشق
* **الجدول المستهدف:** `flight_events`
* **الاستعلام (SQL):**
```sql
SELECT 
    COUNT(*) AS total,
    SUM(CASE WHEN actual_movement_time IS NULL THEN 1 ELSE 0 END) AS missing_actual_time,
    SUM(CASE WHEN scheduled_movement_time IS NULL THEN 1 ELSE 0 END) AS missing_scheduled_time,
    SUM(CASE WHEN aircraft_model IS NULL THEN 1 ELSE 0 END) AS missing_model,
    SUM(CASE WHEN aircraft_registration IS NULL THEN 1 ELSE 0 END) AS missing_registration,
    SUM(CASE WHEN connected_airport_iata IS NULL THEN 1 ELSE 0 END) AS missing_connected_airport
FROM flight_events
WHERE airport_id = 'DAM';
```
* **النتائج:**
  - `total`: 1,563
  - `missing_actual_time`: 1,465 (93.73%) — *متوفر فقط للحركات الـ 98 المؤكدة رادارياً*
  - `missing_scheduled_time`: 0 (0.00%) — *مكتمل بنسبة 100% لجميع الرحلات المجدولة*
  - `missing_model`: 1,348 (86.25%) — *محدد فقط لـ 215 رحلة*
  - `missing_registration`: 1,465 (93.73%) — *محدد فقط لـ 98 رحلة فعلية*
  - `missing_connected_airport`: 0 (0.00%) — *مكتمل بنسبة 100% لجميع الرحلات*

#### 3.2 سجل أدلة الإثبات التشغيلية (Event Evidence Registry)
* **الجدول المستهدف:** `event_evidence` (وليس `flight_evidence`)
* **الاستعلام (SQL):**
```sql
-- إجمالي أدلة الإثبات
SELECT COUNT(*) AS total_evidence FROM event_evidence;

-- توزيع الأدلة حسب المصدر
SELECT 
    source_name, 
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM event_evidence), 1) AS pct
FROM event_evidence
GROUP BY source_name
ORDER BY count DESC;

-- توزيع الأدلة حسب النوع الفني
SELECT 
    evidence_type, 
    COUNT(*) AS count
FROM event_evidence
GROUP BY evidence_type
ORDER BY count DESC;
```
* **النتائج:**
  - إجمالي الأدلة: 1,508 أدلة
  - حسب المصدر:
    * `flightradar24`: 619 (41.0%)
    * `damairport_official+aviationstack+flightradar24`: 439 (29.1%)
    * `alpairport_official+flightradar24`: 154 (10.2%)
    * `aviationstack+flightradar24`: 147 (9.7%)
    * `aviationstack`: 114 (7.6%)
    * مصادر أخرى مدمجة: 35 (2.4%)
  - حسب النوع الفني:
    * `adsb_takeoff`: 414
    * `adsb_touchdown`: 354
    * `aircraft_icao24`: 350
    * `aircraft_registration`: 313
    * `commercial_takeoff` / `touchdown`: 77

#### 3.3 الفحوصات الآلية التسعة في جدول تدقيق الجودة (Data Quality Audit)
* **الجدول المستهدف:** `data_quality_audit` (وليس `quality_audit`)
* **الاستعلام (SQL):**
```sql
SELECT 
    id, 
    check_name, 
    passed, 
    metric_value, 
    details
FROM data_quality_audit
ORDER BY id ASC;
```
* **النتائج المعتمدة:**
  1. `airport_identifiers_validity`: اجتاز بنجاح (1,830 سجلاً تتبع معرفات المطارات السورية المعتمدة).
  2. `no_synthetic_zeros_on_missing_dates`: اجتاز بنجاح (لا توجد أصفار مصطنعة في تواريخ انقطاع التغطية).
  3. `no_speculative_passenger_or_cargo_estimates`: اجتاز بنجاح (منع تام لتوليد أرقام تقديرية للمسافرين أو الشحن).
  4. `flight_status_taxonomy_validity`: اجتاز بنجاح (سلامة الحالات: scheduled, landed, departed, active, cancelled, diverted, unknown).
  5. `route_classification_integrity`: اجتاز بنجاح (تطابق تصنيف الرحلات دولية/داخلية مع السجل الإقليمي).
  6. `deduplication_uniqueness`: اجتاز بنجاح (فرادة السجلات لكل مطار ونوع حركة ورقم رحلة وساعة).
  7. `timestamp_iso8601_utc_compliance`: اجتاز بنجاح (توافق تام مع توقيت UTC ومعيار ISO 8601).
  8. `multi_airport_scope_isolation`: اجتاز بنجاح (عزل نطاق السلسلة التاريخية DAM_ALP_LTK ومنع تجزئتها لدمشق).
  9. `damascus_layer_b_separation`: اجتاز بنجاح (عزل طبقة مطار دمشق العميقة بواقع 1,563 سجلاً دون تلويث).
* **التنبيه الجوهري:** تقيس هذه الفحوصات **سلامة البنية وحوكمة البيانات وقواعد النزاهة**، ولا تعني أن الرصد الراداري كان مكتملاً على مدار العام.

---

### 4. استعلامات السلسلة الزمنية التاريخية للبنك الدولي (World Bank 2024 Series)

#### 4.1 النطاق والمؤشرات العامة للسلسلة الإقليمية
* **الجدول المستهدف:** `historical_daily_movements_2024`
* **الأعمدة الفعلية:** `flight_date`, `movement_type`, `scope`, `total_recorded_operations`
* **الاستعلام (SQL):**
```sql
SELECT 
    COUNT(*) AS total_records,
    MIN(flight_date) AS min_date,
    MAX(flight_date) AS max_date,
    COUNT(DISTINCT flight_date) AS distinct_days,
    SUM(total_recorded_operations) AS total_recorded_operations
FROM historical_daily_movements_2024;
```
* **النتائج:**
  - `total_records`: 578 سجلاً اتجاهياً (289 وصول + 289 إقلاع)
  - `min_date`: `2024-01-01`
  - `max_date`: `2024-10-15`
  - `distinct_days`: 289 يوماً متتالياً
  - `total_recorded_operations`: 8,800 حركة جوية مجمعة

#### 4.2 التوزيع الشهري لحركات عام 2024 المجمعة
* **الجدول المستهدف:** `historical_daily_movements_2024`
* **الاستعلام (SQL):**
```sql
SELECT 
    SUBSTR(flight_date, 1, 7) AS year_month,
    COUNT(*) AS records_count,
    SUM(total_recorded_operations) AS total_monthly_ops,
    ROUND(SUM(total_recorded_operations) * 1.0 / COUNT(*), 2) AS avg_daily_directional_ops
FROM historical_daily_movements_2024
GROUP BY year_month
ORDER BY year_month;
```
* **النتائج:**
  - `2024-01`: 62 سجلاً | 678 حركة (معدل 10.94 يومياً بالاتجاه)
  - `2024-02`: 58 سجلاً | 675 حركة (معدل 11.64 يومياً بالاتجاه)
  - `2024-03`: 62 سجلاً | 685 حركة (معدل 11.05 يومياً بالاتجاه)
  - `2024-04`: 60 سجلاً | 920 حركة (معدل 15.33 يومياً بالاتجاه)
  - `2024-05`: 62 سجلاً | 1,091 حركة (معدل 17.60 يومياً بالاتجاه)
  - `2024-06`: 60 سجلاً | 962 حركة (معدل 16.03 يومياً بالاتجاه)
  - `2024-07`: 62 سجلاً | 1,143 حركة (معدل 18.44 يومياً بالاتجاه)
  - `2024-08`: 62 سجلاً | 1,168 حركة (معدل 18.84 يومياً بالاتجاه)
  - `2024-09`: 60 سجلاً | 1,007 حركة (معدل 16.78 يومياً بالاتجاه)
  - `2024-10` (15 يوماً فقط): 30 سجلاً | 471 حركة (معدل 15.70 يومياً بالاتجاه)
* **تنبيه إحصائي:** يغطي شهر تشرين الأول/أكتوبر 15 يوماً فقط، ومعدله اليومي (15.70) طبيعي ومتسق مع أيلول. شهرا تشرين الثاني وكانون الأول 2024 مفقودان بنسبة 100% في مصدر البنك الدولي.

#### 4.3 التحقق من النطاق الإقليمي للسلسلة التاريخية
* **الجدول المستهدف:** `historical_daily_movements_2024`
* **الاستعلام (SQL):**
```sql
SELECT DISTINCT scope 
FROM historical_daily_movements_2024;
```
* **النتيجة:**
  - القيمة الثابتة هي: `'DAM_ALP_LTK'`
  - **ملاحظة حوكمة البيانات الصارمة:** يُحظر قطيعاً تجزئة هذا الرقم أو استنتاج حصة مطار دمشق الدولي منه بنسب تقريبية أو افتراضية لعدم توفر تفصيل مطاري فردي في البيانات الأصلية للبنك الدولي.

---

### 5. التحقق من سلامة البصمات وتكامل البيانات (Integrity Check)

* **التحقق التشفيري المباشر:**
```powershell
Get-FileHash data/damascus_airport.db -Algorithm SHA256
```
* **النتيجة المحققة والثابتة:**
  `C512FD2952976F923010C42DA19505D803E3FF96930F713F53284EA74568E28B`
* جميع فحوصات الجودة الآلية التسعة في جدول `data_quality_audit` مسجلة بنسبة نجاح 100% (`passed = 1`).
