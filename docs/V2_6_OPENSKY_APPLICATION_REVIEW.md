# Syrian Airport Data Engine — Version 2.6
# OpenSky Application Comprehensive Review & Readiness Assessment

**Document Identifier**: `docs/V2_6_OPENSKY_APPLICATION_REVIEW.md`  
**Target Aerodrome**: Damascus International Airport (`DAM` / `OSDI`)  
**Audit Date**: 2026-10-11  
**Target Standard**: Architectural Governance & Pre-Submission Review Gate  
**Status**: COMPLETE PRE-SUBMISSION AUDIT (Submission Strictly Frozen)  

---

## 1. Executive Assessment & Readiness Verdict

### Readiness Verdict: **APPLICATION PACKAGE 100% READY FOR USER REVIEW**

The technical, methodological, and scientific components of the OpenSky Network historical research application package have been fully drafted, cross-checked, and codified in:
1. [`docs/V2_6_OPENSKY_ACCESS_REQUIREMENTS.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_6_OPENSKY_ACCESS_REQUIREMENTS.md)
2. [`docs/V2_6_OPENSKY_RESEARCH_PROPOSAL.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_6_OPENSKY_RESEARCH_PROPOSAL.md)
3. [`docs/V2_6_OPENSKY_PILOT_QUERY_DESIGN.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_6_OPENSKY_PILOT_QUERY_DESIGN.md)
4. [`docs/V2_6_OPENSKY_ELIGIBILITY_CHECKLIST.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_6_OPENSKY_ELIGIBILITY_CHECKLIST.md)

### Governance Status: **STRICTLY ON HOLD (NO OUTBOUND CONTACT)**
In accordance with mandatory safety rules, **no account has been created, no email has been sent, and no application has been submitted to OpenSky**. The application package is delivered in draft form for personal review, institutional detail entry, and formal user sign-off.

---

## 2. Verified Eligibility Requirements

The following requirements have been verified against official OpenSky Network terms and policies:

| Verified Requirement | Evidentiary Basis | Operational Safeguard in Application |
| :--- | :--- | :--- |
| **Non-Commercial Nature** | OpenSky grants historical Trino access strictly for non-commercial academic research. | The research proposal explicitly disclaims commercial use, operational monetization, and product integration. |
| **Research Project Scope** | Applications must define specific aviation research questions and bounding parameters. | Proposal defines 6 specific research questions, target aerodrome (OSDI), exact temporal bounds (2024–2026), and spatial coordinates. |
| **Cluster Etiquette & Safeguards**| Applications must show technical understanding of Trino partition filtering. | Query design enforces single-day time partitions and spatial bounding boxes to prevent full-table cluster scans. |
| **Mandatory Citation Commitment** | OpenSky terms require citing Schäfer et al. (IPSN 2014) in all published outputs. | Formal commitment to cite the foundational paper is integrated into the application text. |
| **Data Protection & Storage** | Raw telemetry cannot be redistributed in bulk public software repositories. | Data will be held in isolated local storage (`data/historical_sample_review/opensky/`); only derived statistical tables may be published. |

---

## 3. Unresolved Eligibility Questions

Before the application can be submitted, the following institutional prerequisites must be resolved:

1. **Applicant Institutional Standing**:
   - *Status*: **UNRESOLVED / PENDING USER INFORMATION**.
   - *Issue*: OpenSky Network policy reserves Trino historical access for researchers affiliated with **accredited universities, research institutes, or civil aviation authorities**. Independent private hobbyists without institutional standing are routinely directed to the 30-day REST API.
   - *Resolution Path*: The user must confirm whether they possess an active affiliation with an eligible institution (e.g. university faculty, PhD/graduate researcher, or research institute staff).
2. **Institutional Email Address**:
   - *Status*: **UNRESOLVED / PENDING USER INFORMATION**.
   - *Issue*: OpenSky requires an institutional email domain to verify identity and expedite application approval. Applications submitted via generic public domains (`@gmail.com`, `@yahoo.com`) face high rejection rates.
   - *Resolution Path*: The user must provide an active institutional email address.
3. **OpenSky Registered Account**:
   - *Status*: **UNRESOLVED / NOT YET CREATED**.
   - *Issue*: To submit a Trino access request via the portal (`https://opensky-network.org/my-opensky/request-data`), the user must possess an active user account.
   - *Resolution Path*: The user must personally create a standard user account on `opensky-network.org` using their institutional email when ready.

---

## 4. Required Information from the User

To finalize the draft application text in [`docs/V2_6_OPENSKY_RESEARCH_PROPOSAL.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_6_OPENSKY_RESEARCH_PROPOSAL.md), the user must replace the following placeholders:

| Placeholder Variable | Required Information from User | Example Entry |
| :--- | :--- | :--- |
| `[USER_FULL_NAME]` | Full legal name of applicant / Principal Investigator | *Dr. John Doe / Eng. Sarah Smith* |
| `[USER_TITLE]` | Academic or professional title | *Assistant Professor / Research Fellow / Graduate Researcher* |
| `[USER_INSTITUTION_NAME]` | Name of accredited university, institute, or research organization | *Department of Aviation Technology, University of ...* |
| `[USER_INSTITUTIONAL_EMAIL]` | Official institutional email address | *john.doe@university.edu / researcher@institution.org* |
| `[USER_OPENSKY_USERNAME]` | Username of user's personal OpenSky Network account | *johndoe_research* |
| `[USER_INSTITUTION_ADDRESS]` | Official physical postal address of the institution | *Campus Box 1234, City, Country* |
| `[FACULTY_SPONSOR_NAME]` | Faculty supervisor / department chair (if student/fellow) | *Prof. Robert Johnson (or N/A)* |

---

## 5. Potential Licensing & Operational Restrictions

1. **Creative Commons Attribution-NonCommercial (CC BY-NC 4.0)**:
   - Data obtained via Trino is licensed strictly for non-commercial purposes.
   - Any future commercial monetization of the Syrian Airport Data Engine would require negotiating a commercial license with OpenSky.
2. **Operational Integration Prohibition**:
   - Section 3 of OpenSky Terms of Use states that integrating OpenSky feeds into automated production systems, live operational dashboards, or real-time flight monitoring requires a separate commercial operational license, even for non-profits.
   - The Syrian Airport Data Engine must retain OpenSky data strictly as an **offline historical analytical archive**, not as an automated real-time daemon.
3. **No Bulk Raw Redistribution**:
   - Raw CSV/Parquet extracts cannot be checked into a public GitHub repository. Only derivative summary statistics, trajectory graphs, and daily aggregate counts may be made public.

---

## 6. Technical Feasibility & Coverage Risks

1. **Terrestrial Receiver Deficit at Damascus**:
   - Terrestrial receiver coverage in Syria is historically sparse. While high-altitude transits (FL250+) are captured by border receivers in Lebanon, Jordan, and Cyprus, line-of-sight signal loss typically occurs below 3,500–4,500 ft MSL over Damascus.
   - *Risk*: OpenSky data will yield predominantly **Tier 3 (Approach Candidate)** and **Tier 4 (Departure Candidate)** trajectories rather than confirmed runway touchdowns.
2. **Overflight Signal Contamination**:
   - The Damascus VOR sits beneath dense international airways. Without strict spatial-altitude filtering, high-altitude flights will contaminate airport metrics.
   - *Mitigation*: The pilot query design in `docs/V2_6_OPENSKY_PILOT_QUERY_DESIGN.md` enforces a 4-zone horizontal and 4-band vertical filter to segregate overflights.
3. **Trino Cluster Resource Limits**:
   - Trino queries exceeding cluster memory limits (e.g. attempting to scan full-year tables without single-day time partition filters) will fail.
   - *Mitigation*: The project enforces single-day time window queries.

---

## 7. Strategic Recommendations & Next Actions

1. **Personal Review**:
   Project leadership should review [`docs/V2_6_OPENSKY_RESEARCH_PROPOSAL.md`](file:///c:/Users/fahad/OneDrive/Desktop/syria%20damascus%20airport/docs/V2_6_OPENSKY_RESEARCH_PROPOSAL.md) and confirm whether the research questions, scope, and technical design accurately reflect research objectives.
2. **Institutional Alignment**:
   Determine whether an eligible academic or institutional email is available to submit the application.
3. **Hold Outbound Action**:
   Do not submit the application or contact OpenSky until explicit user authorization is provided.
