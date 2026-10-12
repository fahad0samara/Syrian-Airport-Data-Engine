<USER_REQUEST>
# Syrian Airport Data Engine

## Stakeholder Briefing & Demonstration Package

**Project:** Syrian Airport Data Engine

**Focus:** Damascus International Airport (DAM / OSDI)

**Presentation type:** Project overview and live demonstration

**Data reference period:** October 2026, with important differences in coverage windows



---



# الجزء الأول: الملخص التنفيذي بالعربي



## 1. نظرة عامة



يهدف مشروع **Syrian Airport Data Engine** إلى جمع وتنظيم بيانات الطيران المتاحة عن المطارات السورية ضمن قاعدة بيانات موحدة، مع ربط المعلومات بمصادرها وتصنيفها بحسب طبيعتها ودرجة التحقق منها.



المشروع لا يقدّم نفسه كنظام رسمي لإحصاءات الطيران، بل كمنصة بحث ومراقبة تساعد على فهم حركة الطيران، واستكشاف البيانات التاريخية المتاحة، ومقارنة الرحلات المجدولة بالحركات المرصودة عندما تتوفر أدلة مناسبة.



## 2. ما الذي يقدمه المشروع؟



يتضمن النظام مجموعة من القدرات:



- تنظيم بيانات المطارات وشركات الطيران والوجهات.

- تخزين سجلات الرحلات المجدولة والحركات المرصودة.

- التمييز بين الرحلات المجدولة والحركات الفعلية المصنفة وفق الأدلة المتاحة.

- الاحتفاظ بمعلومات المصادر والأدلة المرتبطة بسجلات الرحلات.

- عرض البيانات التاريخية المتاحة وإظهار فجوات التغطية.

- توفير صفحة مستقلة باسم **Syrian Air Traffic Monitor**.

- تصفية البيانات بحسب المطار والشهر وشركة الطيران والوجهة.

- تصدير سجلات الرحلات والملخصات الشهرية بصيغ CSV وExcel.



## 3. نتائج توضيحية من بيانات المشروع



### مطار دمشق الدولي — تشرين الأول 2026



| المؤشر | القيمة | نطاق البيانات |

|---|---:|---|

| الرحلات المجدولة | 1,365 | 1–31 تشرين الأول |

| الوصول المجدول | 682 | 1–31 تشرين الأول |

| المغادرة المجدولة | 683 | 1–31 تشرين الأول |

| الحركات المرصودة عبر ADS-B التجاري | 98 | 9–10 تشرين الأول فقط |

| الوصول المرصود | 48 | 9–10 تشرين الأول |

| المغادرة المرصودة | 50 | 9–10 تشرين الأول |

| شركات الطيران ضمن بيانات المطار | 27 | وفق نطاق مجموعة البيانات |

| المسافرون | غير متاح | لا توجد أرقام موثوقة متاحة |



**ملاحظة منهجية مهمة:** عدد 98 يمثل عينة من الحركات المرصودة خلال يومين فقط، بينما 1,365 يمثل الرحلات المجدولة خلال شهر كامل. لذلك لا يصح استخدام الرقمين لحساب نسبة تنفيذ شهرية أو مقارنة مباشرة بينهما.



كما أن 27 شركة طيران تمثل شركات موجودة ضمن مجموعة البيانات، وليست بالضرورة 27 شركة نفذت حركات مرصودة خلال يومي العينة. عدد شركات الطيران المشغّلة ضمن عينة الحركات المرصودة هو 17 وفق تقرير التحليل.



### نطاق البيانات السورية



وفق تقارير التنفيذ:



- 1,572 رحلة مجدولة ضمن مجموعة البيانات السورية في تشرين الأول.

- 3 مطارات ظهرت لها بيانات ضمن نطاق العرض الشهري: دمشق وحلب ودير الزور.

- أرقام المسافرين غير متاحة في سجلات الحركة اليومية وسجلات الرحلات المعنية.



هذه المؤشرات مرتبطة بتغطية مجموعة البيانات، ولا تمثل بالضرورة إجمالي حركة الطيران في سوريا.



## 4. مصادر البيانات ومنهجية التعامل معها



يعتمد المشروع على أكثر من نوع من المصادر، مع الفصل بين طبيعة كل مصدر:



**المصادر الرسمية للمواعيد (FIDS):**

تُستخدم لعرض الرحلات المجدولة والمعلومات المنشورة عن الرحلات. لا تُعامل هذه البيانات وحدها كدليل على تنفيذ الرحلة فعلياً، كما أن الواجهات المتاحة قد تعرض جداول متجددة وليست أرشيفاً تاريخياً كاملاً.



**مصادر التتبع التجاري وبيانات ADS-B:**

تُستخدم لرصد الحركات التي تتوفر عنها سجلات تتبع وأدلة مرتبطة بها. ويعرض المشروع هذه النتائج تحت تسمية «حركات مرصودة عبر بيانات ADS-B التجارية»، وليس باعتبارها تأكيداً مستقلاً من رادار رسمي.



**واجهات البيانات التجارية:**

تُستخدم كمصادر إضافية للمقارنة والتحقق من السجلات، مع الاحتفاظ بتصنيف الأدلة وعدم افتراض أن تعدد مزودي البيانات يعني بالضرورة تعدد أجهزة الاستشعار المستقلة.



## 5. القيود المعروفة



من المهم عرض القيود بوضوح:



1. التغطية التاريخية للحركات الفعلية في مطار دمشق غير مكتملة.

2. بيانات ADS-B المرصودة المتاحة في المثال الحالي تتركز في يومي 9 و10 تشرين الأول 2026.

3. بيانات التتبع التجاري لا تمثل بالضرورة كل الرحلات أو كل الحركات الأرضية.

4. أعداد المسافرين والشحن غير متاحة بصورة موثوقة ضمن البيانات الحالية.

5. الرحلة المجدولة لا تعني بالضرورة أن الرحلة نُفذت.

6. قد تظهر سجلات مشاركة بالرمز (Codeshare) لنفس الرحلة التشغيلية، ولذلك يجب التعامل معها بعناية لتجنب العد المزدوج.

7. القيم الفارغة تعني أن البيانات غير متاحة، ولا تعني أن عدد الحركات أو المسافرين يساوي صفراً.



## 6. القيمة التي يقدمها المشروع



القيمة الأساسية للمشروع هي تحويل معلومات الطيران المتفرقة إلى بيانات منظمة وقابلة للاستكشاف والتحليل.



ويساعد ذلك على:



- تسهيل الوصول إلى بيانات المطارات والرحلات.

- فهم الفرق بين الجداول المنشورة والحركات المرصودة.

- تتبع مصدر كل معلومة.

- اكتشاف الفجوات في التغطية التاريخية.

- إعداد ملفات قابلة للتحليل باستخدام Excel وأدوات تحليل البيانات.

- توفير أساس بحثي يمكن تطويره مع تحسن توفر البيانات.



**الخلاصة:** المشروع يوفر بنية منظمة لاستكشاف بيانات الطيران السورية المتاحة، مع توضيح مصدر البيانات وحدودها، بدلاً من تقديم أرقام غير مكتملة على أنها إحصاءات رسمية شاملة.



---



# Part Two: Executive Brief in English



## 1. Overview



The **Syrian Airport Data Engine** is a data research and monitoring project designed to organize available aviation information about Syrian airports into a structured, traceable dataset.



The project is not presented as an official national aviation statistics system. Its purpose is to make fragmented aviation information easier to explore, compare, and analyze while preserving source provenance and clearly distinguishing scheduled services from observed movements.



## 2. Current Capabilities



The project provides:



- Structured airport, airline, destination, and flight records.

- Scheduled flight information and classified movement records.

- Evidence and source provenance associated with flight records.

- Historical data organization and coverage-gap visibility.

- A standalone Syrian Air Traffic Monitor.

- Filters for airport, month, airline, and destination.

- CSV and Excel exports for detailed events and monthly summaries.



## 3. Illustrative Results — Damascus, October 2026



| Metric | Result | Coverage |

|---|---:|---|

| Scheduled flights | 1,365 | October 1–31 |

| Scheduled arrivals | 682 | October 1–31 |

| Scheduled departures | 683 | October 1–31 |

| ADS-B observed movements — commercial tracking data | 98 | October 9–10 only |

| Observed arrivals | 48 | October 9–10 |

| Observed departures | 50 | October 9–10 |

| Dataset carriers | 27 | Dataset scope |

| Passengers | Unavailable | No reliable figures available |



The 98 observed movements represent a two-day observation sample, whereas the 1,365 scheduled flights cover the entire month. These figures are not directly comparable and must not be interpreted as a monthly completion rate.



The dataset includes 27 carriers within the relevant airport data scope. The observed two-day sample contains 17 operating carriers, according to the supplied analysis report.



Across the Syrian dataset, the reported October scheduled-flight total is 1,572, with data represented for Damascus, Aleppo, and Deir ez-Zor in the monthly monitor scope.



These figures describe the available dataset, not necessarily the complete national aviation activity.



## 4. Data Sources and Evidence Methodology



The project distinguishes between several source categories:



**Official Flight Information Display Systems (FIDS):** Used for published flight schedules and related information. A rolling schedule is not, by itself, proof that a flight physically operated, nor does it constitute a complete historical archive.



**Commercial tracking and ADS-B data:** Used to identify observed aircraft movements where relevant tracking evidence is available. The project labels these as movements observed through available commercial ADS-B tracking data, not as independently confirmed official radar movements.



**Commercial aviation APIs:** Used as supplementary data sources for comparison and evidence collection. Multiple commercial providers are not automatically treated as independent sensor confirmations.



## 5. Known Limitations



- Historical coverage of actual movements is incomplete.

- The currently reported ADS-B observation sample for Damascus covers October 9–10 only.

- Commercial tracking coverage may be incomplete.

- Passenger and cargo figures are not reliably available in the current dataset.

- Scheduled flights must not be treated as completed flights.

- Codeshare records require careful handling to avoid double counting.

- Missing values are retained as unknown rather than converted to zero.



## 6. Project Value



The project provides a structured foundation for aviation research by:



- Consolidating fragmented aviation information.

- Preserving source traceability.

- Separating schedules from observed movements.

- Making historical coverage gaps visible.

- Supporting data exploration and export.

- Providing reusable datasets for further analysis.



**Conclusion:** The Syrian Airport Data Engine is an aviation data research and monitoring platform that makes available information more accessible, structured, and transparent about its limitations.



---



# الجزء الثاني: مخطط العرض التقديمي — 9 شرائح



## Slide 1 — Syrian Airport Data Engine



**العنوان:** بناء مصدر منظم لاستكشاف بيانات الطيران السورية



المحتوى:

- Syrian Airport Data Engine

- Aviation Data Research & Monitoring

- التركيز على مطار دمشق الدولي

- اسم مقدم العرض وتاريخ العرض



الفكرة البصرية: لقطة من واجهة النظام أو صورة جوية لمطار دمشق.



## Slide 2 — The Problem



**العنوان:** بيانات الطيران متفرقة، والوصول إليها ليس سهلاً



المحتوى:

- مصادر متعددة وغير موحدة.

- اختلاف طبيعة البيانات بين الجداول والحركات المرصودة.

- نقص في التغطية التاريخية.

- صعوبة تتبع مصدر كل سجل.

- خطر الخلط بين الرحلات المجدولة والرحلات المنفذة.



الرسالة الأساسية: التحدي ليس جمع الأرقام فقط، بل فهم مصدرها وما الذي تثبته فعلياً.



## Slide 3 — Our Approach



**العنوان:** تحويل البيانات المتفرقة إلى سجلات منظمة وقابلة للتتبع



المحتوى:

- جمع المعلومات المتاحة.

- توحيد شكل سجلات المطارات والرحلات.

- تصنيف طبيعة السجل.

- ربط السجل بمصدره وأدلته.

- إظهار البيانات المفقودة دون افتراض قيم بديلة.



الفكرة البصرية: مخطط مبسط من المصادر إلى قاعدة البيانات ثم واجهة المراقبة والتصدير.



## Slide 4 — Data Sources & Evidence



**العنوان:** ليس كل مصدر يثبت الشيء نفسه



المحتوى:

- Official FIDS — جداول الرحلات المنشورة.

- Commercial Tracking / ADS-B — بيانات تتبع الحركات المرصودة.

- Commercial Aviation APIs — بيانات مساعدة للمقارنة.

- Evidence Provenance — مصدر كل معلومة وتصنيفها.



تنبيه ظاهر: تعدد المصادر التجارية لا يعني بالضرورة وجود أجهزة استشعار مستقلة متعددة.



## Slide 5 — Damascus Airport: October 2026



**العنوان:** مثال عملي من بيانات مطار دمشق



المحتوى:

- 1,365 رحلة مجدولة خلال الشهر.

- 682 وصولاً مجدولاً.

- 683 مغادرة مجدولة.

- 98 حركة مرصودة عبر بيانات ADS-B التجارية خلال 9–10 تشرين الأول.

- 48 وصولاً و50 مغادرة ضمن عينة اليومين.



تنبيه بصري بارز: فترتا التغطية مختلفتان؛ لا تقارن الأرقام باعتبارها إجماليات شهرية متكافئة.



## Slide 6 — Syrian Air Traffic Monitor



**العنوان:** واجهة واحدة لاستكشاف بيانات الطيران



المحتوى:

- مؤشرات الأداء الرئيسية.

- مقارنة الرحلات المجدولة حسب الشهر.

- ملخص شهري حسب المطار.

- فلاتر المطار والشهر وشركة الطيران والوجهة.

- توضيح نطاق التغطية ومصدر البيانات.



الفكرة البصرية: لقطة شاشة حقيقية من صفحة `air_traffic_monitor.html`.



## Slide 7 — Data Export & Analysis



**العنوان:** البيانات ليست محصورة داخل لوحة التحكم



المحتوى:

- تصدير سجلات الرحلات بصيغة CSV وExcel.

- تصدير الملخصات الشهرية.

- بيانات التاريخ والمطار والاتجاه والشركة والوجهة.

- تصنيف السجل ومصدره والأدلة المتاحة.

- الاحتفاظ بالقيم غير المتاحة كقيم فارغة.



الفكرة البصرية: لقطة من ملف Excel تم تصديره فعلياً.



## Slide 8 — Limitations & Data Transparency



**العنوان:** الشفافية جزء من تصميم النظام



المحتوى:

- فجوات تاريخية في الحركات الفعلية.

- تغطية ADS-B محدودة زمنياً.

- لا توجد أرقام موثوقة للمسافرين حالياً.

- الجداول لا تثبت تنفيذ الرحلات.

- البيانات الناقصة لا تعني صفراً.

- مشاركة الرمز تحتاج إلى معالجة تمنع العد المزدوج.



الرسالة الأساسية: إظهار حدود البيانات أكثر قيمة من تقديم أرقام تبدو مكتملة لكنها غير موثوقة.



## Slide 9 — Conclusion & Research Value



**العنوان:** أساس منظم لأبحاث الطيران ومراقبة البيانات



المحتوى:

- تنظيم البيانات المتاحة.

- توثيق مصادرها.

- تسهيل الوصول والتحليل والتصدير.

- توضيح الفجوات والقيود.

- بناء أساس قابل للتطوير عند توفر بيانات موثوقة إضافية.



**الخاتمة:**

Syrian Airport Data Engine turns fragmented aviation information into structured, traceable, and research-ready data.



---



# الجزء الثالث: سيناريو العرض العملي (Demo Script)



**المدة المقترحة:** 5–7 دقائق.



## المرحلة 1 — تقديم النظام (30 ثانية)



"خلونا ننتقل من فكرة المشروع إلى التطبيق العملي. الهدف من النظام هو تنظيم بيانات الطيران المتاحة وربطها بمصادرها، بحيث نقدر نستكشف الرحلات والجداول والحركات المرصودة ضمن نطاق البيانات المتوفرة."



## المرحلة 2 — فتح Syrian Air Traffic Monitor (دقيقة)



"هذه صفحة المراقبة المستقلة. صممناها حتى نقدر نستعرض البيانات التشغيلية المتاحة بشكل مباشر، من دون الحاجة إلى الدخول في تفاصيل قاعدة البيانات."



اعرض:

- مؤشرات الأداء.

- نطاق المطارات.

- الفترة الزمنية.

- التنبيهات التي توضّح نطاق التغطية.



## المرحلة 3 — استعراض بيانات مطار دمشق (دقيقة)



"خلونا نختار مطار دمشق ونشوف بيانات تشرين الأول 2026."



اعرض:

- الرحلات المجدولة: 1,365.

- الوصول المجدول: 682.

- المغادرة المجدولة: 683.



ثم وضّح:



"هذه أرقام الرحلات المجدولة على امتداد الشهر، وليست إثباتاً بأن جميع الرحلات نُفذت فعلياً."



## المرحلة 4 — استعراض الحركات المرصودة (دقيقة)



"لدينا أيضاً عينة من الحركات المرصودة عبر بيانات ADS-B التجارية خلال يومي 9 و10 تشرين الأول."



اعرض:

- 98 حركة مرصودة.

- 48 وصولاً.

- 50 مغادرة.



ثم قل:



"هذه عينة زمنية محدودة، ولا يجوز مقارنتها مباشرة بإجمالي الرحلات المجدولة للشهر. كما أننا لا نصفها بأنها تأكيد مستقل من رادار رسمي."



## المرحلة 5 — تجربة الفلاتر (دقيقة)



"يمكننا تضييق نطاق البيانات حسب المطار أو الشهر أو شركة الطيران أو الوجهة."



نفّذ:

1. اختيار مطار دمشق.

2. اختيار الشهر.

3. اختيار شركة طيران.

4. اختيار وجهة.



اشرح أن نتائج الفلاتر تعتمد على البيانات المتاحة في قاعدة البيانات.



## المرحلة 6 — تصدير البيانات (دقيقة)



"إحدى أهم نقاط النظام أن البيانات لا تبقى محصورة داخل الواجهة. يمكن تصدير سجلات الرحلات أو الملخصات الشهرية بصيغ CSV وExcel."



اعرض:

- تصدير سجلات الرحلات.

- تصدير الملخص الشهري.

- فتح ملف تم تصديره مسبقاً إذا كان جاهزاً.



اشرح أن الملفات تتضمن معلومات الرحلة والمطار والاتجاه والمصدر والتصنيف، بحسب الحقول المتاحة.



## المرحلة 7 — الخاتمة (30 ثانية)



"القيمة الأساسية للمشروع ليست في تقديم رقم واحد عن حركة الطيران، بل في تنظيم المعلومات المتاحة، وتوضيح مصدرها، والتمييز بين المجدول والمرصود، وإظهار ما نعرفه وما لا نعرفه. وهذا يعطي أساساً أكثر شفافية وقابلية للاستخدام في الأبحاث والتحليلات المستقبلية."



---



# ملاحظات مهمة قبل العرض



1. استخدم لقطات شاشة حديثة من الواجهة الفعلية، وليس تصاميم افتراضية.

2. إذا كان العرض حياً، اختبر الفلاتر والتصدير مسبقاً.

3. جهّز نسخة Excel تجريبية تم تصديرها فعلياً.

4. لا تعرض 98 من أصل 1,365 كنسبة تنفيذ.

5. لا تعرض بيانات المسافرين كصفر؛ استخدم "غير متاح".

6. لا تصف بيانات ADS-B التجارية بأنها بيانات رادار رسمي مستقل.

7. لا تصف المشروع بأنه يغطي كل حركة الطيران في سوريا.

8. لا تضف وعوداً بتوفير بيانات مستقبلية أو ربط مصادر جديدة قبل تنفيذها والتحقق منها.

9. استخدم كلمة "بيانات مجموعة المشروع" عند الحديث عن عدد الشركات أو الوجهات.

10. هذا العرض مخصص للتعريف بالمشروع وإظهار قدراته الحالية، وليس لإصدار إحصاءات وطنية رسمية.



**رسالة العرض النهائية:**



المشروع لا يحاول إخفاء نقص البيانات أو تحويلها إلى أرقام مكتملة ظاهرياً؛ بل ينظم ما هو متاح، ويحافظ على مصدره، ويجعل حدود المعرفة واضحة وقابلة للفحص.
</ADDITIONAL_METADATA>
