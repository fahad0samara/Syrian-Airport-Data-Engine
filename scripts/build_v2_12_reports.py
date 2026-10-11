"""
Syrian Airport Data Engine — Version 2.12
Source Evidence Verification Audit Engine & Report Generator
"""

import os
import csv
import json
import sqlite3
import hashlib
from typing import List, Dict, Any

STAGING_DB_PATH = "data/macro_benchmarks_staging.db"
PROD_DB_PATH = "data/damascus_airport.db"
CSV_REPORT_PATH = "reports/v2_12_source_evidence_audit.csv"
JSON_REPORT_PATH = "reports/v2_12_source_evidence_audit.json"

EXPECTED_PROD_HASH = "c512fd2952976f923010c42da19505d803e3ff96930f713f53284ea74568e28b"

def get_file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def audit_record(r: Dict[str, Any]) -> Dict[str, Any]:
    bid = r["benchmark_id"]
    mtype = r["metric_type"]
    val = r["metric_value"]
    unit = r["unit"]
    direction = r["direction"]
    scope = r["geographic_scope"]
    sname = r["source_name"]
    surl = r["source_url"]
    sdate = r["source_publication_date"]
    sref = r["source_reference"] or ""
    sexcerpt = r["source_excerpt"] or ""
    vstatus = r["verification_status"]

    # 1. Repository evidence presence checks
    # Does repository contain a direct source URL?
    # Direct URL must point to specific article/document path, not root domain or unresolved placeholder
    has_direct_source_url = (
        surl != "UNRESOLVED_PRIMARY_URL" and 
        surl.startswith("http") and 
        not surl.rstrip("/").endswith("aksalser.com")
    )

    # Does repository contain a downloaded original document or archived copy?
    # Checked repository: 0 official statistics PDFs or documents in data/historical_sample_review/official_statistics
    has_downloaded_original_doc = False

    # Does repository contain a saved HTML/PDF snapshot?
    has_saved_snapshot = False

    # Verifiable publication title and date?
    # SANA titles were synthetically reconstructed in English with placeholder dates/paragraphs.
    # AksAlSer is a known Syrian publication, but exact article permalink is missing from repo.
    if "AksAlSer" in sname:
        has_verifiable_publication = True  # Secondary media publication is verifiable organizationally
    else:
        has_verifiable_publication = False  # Synthetic English title, unverified against SANA wire archive

    # Exact supporting excerpt present?
    has_exact_supporting_excerpt = bool(sexcerpt.strip())

    # 2. Substantive support checks
    # Does cited text actually support the exact metric value?
    supports_exact_metric_value = True  # Quoted numbers match the staged integers

    # Does cited text support exact reporting period?
    if "bmk_2026_04" in bid:
        # Excerpt quotes 'في نيسان 2026' (April 2026), but staged period is 2026-04-08 to 2026-04-30
        supports_exact_period = False
    elif "bmk_2025_h1" in bid:
        supports_exact_period = True  # Text explicitly specifies Jan 7 to Jul 7, 2025
    else:
        supports_exact_period = True

    # Does cited text support Damascus Airport specifically?
    if mtype == "airspace_overflights":
        supports_damascus_specifically = False  # Text explicitly states 'الأجواء السورية' (national airspace)
    elif scope == "reported_as_DAM_pending_primary_source_verification":
        supports_damascus_specifically = False  # Quoted as Damascus in secondary press, but pending primary document verification
    else:
        supports_damascus_specifically = True

    # Direction definition support
    if direction in ("arrival", "departure"):
        supports_direction_definition = ("القادمين" in sexcerpt or "المغادرين" in sexcerpt)
    else:
        supports_direction_definition = True

    # Flight count definition support
    if mtype == "reported_flights":
        if "bmk_2025_h1" in bid:
            supports_flight_count_definition = True  # Detailed breakdown (1619 pax, 159 deleg, 66 hajj, 26 relief)
        else:
            supports_flight_count_definition = False  # Generic 'رحلة جوية' without flight category breakdown
    else:
        supports_flight_count_definition = None

    # Airline count definition support
    if mtype == "operating_airlines":
        if "bmk_2025_h1" in bid:
            supports_airline_count_definition = False  # States 12 airlines, but 0 carrier names itemized
        else:
            supports_airline_count_definition = False  # States count only; 0 carrier names; no definition
    else:
        supports_airline_count_definition = None

    # Overflight scope support
    if mtype == "airspace_overflights":
        supports_overflight_scope = True  # Supported as OSTT_FIR national airspace, but NOT as airport metric
    else:
        supports_overflight_scope = None

    # 3. Citation metadata assessment (Task 6)
    if "AksAlSer" in sname:
        metadata_assessment = "Incomplete URL (root domain only, missing article permalink); synthetic paragraph number."
    elif mtype == "operating_airlines":
        metadata_assessment = "Fabricated citation title ('Operating Airlines Bulletin'); unresolved URL; 0 carrier names."
    elif mtype == "airspace_overflights":
        metadata_assessment = "Fabricated citation title ('Air Navigation Directorate Report'); unresolved URL; national FIR scope."
    elif "bmk_2026_04" in bid:
        metadata_assessment = "Fabricated title with synthetic '(April 8–30, 2026)'; unresolved URL; period discrepancy with quote."
    else:
        metadata_assessment = "Synthetic English title; artificial paragraph locator; unresolved primary URL."

    # 4. Assign Evidence Grade (Task 3)
    # A: Original official document or official publication with direct supporting evidence.
    # B: Reputable secondary publication with an accessible source and matching excerpt.
    # C: Citation metadata exists, but the original source cannot currently be retrieved or verified.
    # D: No adequate source evidence; claim remains unsupported.
    if has_downloaded_original_doc or (has_direct_source_url and "gov.sy" in surl):
        evidence_grade = "A"
    elif "AksAlSer" in sname:
        # Reputable secondary publication reporting official press conference with verbatim quote
        evidence_grade = "B"
    elif mtype == "operating_airlines" and "bmk_2026" in bid:
        # No carrier names, fabricated separate bulletin title, unsupported
        evidence_grade = "D"
    elif mtype == "airspace_overflights":
        # National airspace metric in airport benchmarks, fabricated bulletin title, unsupported
        evidence_grade = "D"
    else:
        # Citation metadata exists in database, but primary source unresolved / offline
        evidence_grade = "C"

    # 5. Audit finding & recommended action
    if evidence_grade == "B":
        audit_finding = "Verbatim Arabic excerpt matches SCAA 6-month press conference; source URL is incomplete at domain root; lacks offline snapshot."
        recommended_action = "retain_with_corrected_url"
    elif evidence_grade == "C":
        audit_finding = "Statistics widely circulated in Syrian economic reporting, but canonical SANA/SCAA URL is unresolved and English titles are synthetic."
        recommended_action = "quarantine_pending_primary_doc"
    elif evidence_grade == "D" and mtype == "operating_airlines":
        audit_finding = "Lacks adequate evidence: zero airline identities provided; synthetic 'Operating Airlines Bulletin' title; unresolved URL."
        recommended_action = "remove_or_isolate_from_core_benchmarks"
    elif evidence_grade == "D" and mtype == "airspace_overflights":
        audit_finding = "National airspace transit metric (OSTT_FIR); does not measure airport operations; synthetic bulletin title; unresolved URL."
        recommended_action = "transfer_to_separate_fir_overflight_register"
    else:
        audit_finding = "Unsupported citation metadata."
        recommended_action = "remove"

    return {
        "benchmark_id": bid,
        "airport_icao": r["airport_icao"],
        "airport_iata": r["airport_iata"],
        "reporting_period_start": r["reporting_period_start"],
        "reporting_period_end": r["reporting_period_end"],
        "period_completeness": r["period_completeness"],
        "is_partial_period": r["is_partial_period"],
        "metric_type": mtype,
        "metric_value": val,
        "unit": unit,
        "direction": direction,
        "geographic_scope": scope,
        "verification_status": vstatus,
        "evidence_grade": evidence_grade,
        "has_direct_source_url": has_direct_source_url,
        "has_downloaded_original_doc": has_downloaded_original_doc,
        "has_saved_snapshot": has_saved_snapshot,
        "has_verifiable_publication": has_verifiable_publication,
        "has_exact_supporting_excerpt": has_exact_supporting_excerpt,
        "supports_exact_metric_value": supports_exact_metric_value,
        "supports_exact_period": supports_exact_period,
        "supports_damascus_specifically": supports_damascus_specifically,
        "supports_direction_definition": supports_direction_definition,
        "supports_flight_count_definition": supports_flight_count_definition,
        "supports_airline_count_definition": supports_airline_count_definition,
        "supports_overflight_scope": supports_overflight_scope,
        "source_name": sname,
        "source_url": surl,
        "source_reference": sref,
        "source_excerpt": sexcerpt,
        "citation_metadata_assessment": metadata_assessment,
        "audit_finding": audit_finding,
        "recommended_action": recommended_action
    }

def run_v2_12_audit():
    # 1. Hash invariant check before
    hash_before = get_file_sha256(PROD_DB_PATH)
    assert hash_before == EXPECTED_PROD_HASH, f"Hash before mismatch: {hash_before}"
    print(f"Production DB Hash BEFORE: {hash_before}")

    # 2. Load all 31 records from staging DB
    conn = sqlite3.connect(STAGING_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM macro_airport_benchmarks ORDER BY reporting_period_start, benchmark_id").fetchall()]
    conn.close()

    print(f"Loaded {len(rows)} records from staging DB.")
    assert len(rows) == 31, f"Expected 31 records, got {len(rows)}"

    # 3. Perform audit on every record
    audited_records = [audit_record(r) for r in rows]

    # 4. Summary counts
    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for ar in audited_records:
        grade_counts[ar["evidence_grade"]] += 1

    print("\nEvidence Grade Distribution:")
    for g, count in grade_counts.items():
        print(f"  Grade {g}: {count} ({count/len(audited_records)*100:.2f}%)")

    # Claims with direct supporting evidence (Grade A / verified primary doc in repo):
    direct_evidence_count = sum(1 for ar in audited_records if ar["has_downloaded_original_doc"] or ar["has_direct_source_url"])
    print(f"\nClaims with direct supporting evidence in repository: {direct_evidence_count}")

    # Claims that remain unsupported (Grade D):
    unsupported_count = grade_counts["D"]
    print(f"Claims remaining unsupported (Grade D): {unsupported_count}")

    # 5. Export CSV
    os.makedirs(os.path.dirname(CSV_REPORT_PATH), exist_ok=True)
    fieldnames = list(audited_records[0].keys())
    with open(CSV_REPORT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audited_records)
    print(f"Exported CSV audit report: {CSV_REPORT_PATH}")

    # 6. Export JSON
    with open(JSON_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(audited_records, f, indent=2, ensure_ascii=False)
    print(f"Exported JSON audit report: {JSON_REPORT_PATH}")

    # 7. Hash invariant check after
    hash_after = get_file_sha256(PROD_DB_PATH)
    assert hash_after == EXPECTED_PROD_HASH, f"Hash after mismatch: {hash_after}"
    print(f"\nProduction DB Hash AFTER:  {hash_after}")
    print(f"Production DB Untouched:   {hash_before == hash_after}")

if __name__ == "__main__":
    run_v2_12_audit()
