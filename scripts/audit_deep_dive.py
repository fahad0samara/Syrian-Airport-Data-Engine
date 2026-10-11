import sqlite3
import pandas as pd
import json

conn = sqlite3.connect("data/damascus_airport.db")
c = conn.cursor()

print("=== 1. DEDUPLICATION AUDIT TABLE ===")
c.execute("SELECT matching_rule, resolution_status, count(*) FROM deduplication_audit GROUP BY matching_rule, resolution_status")
for r in c.fetchall():
    print(f"  {r[0]} | {r[1]} | {r[2]}")

c.execute("SELECT event_id, count(*) FROM flight_events GROUP BY event_id HAVING count(*) > 1")
dups = c.fetchall()
print(f"\nDuplicate event_ids in flight_events table: {len(dups)}")

df_merged = pd.read_sql_query("SELECT * FROM deduplication_audit WHERE resolution_status = 'MERGED_VERIFIED'", conn)
print(f"\nMerged verified records: {len(df_merged)}")
print("Source combinations in verified merges:")
print(df_merged.groupby(["source_a", "source_b"]).size())

print("\nAirport breakdown in verified merges:")
print(df_merged.groupby("airport_id").size())

print("\nMovement type breakdown in verified merges:")
print(df_merged.groupby("movement_type").size())

print("\nTime difference summary (minutes) for merged records:")
print(df_merged["time_difference_minutes"].describe())

df_amb = pd.read_sql_query("SELECT * FROM deduplication_audit WHERE resolution_status = 'AMBIGUOUS_KEPT_SEPARATE'", conn)
print(f"\nFlagged ambiguous records: {len(df_amb)}")
for idx, row in df_amb.head(5).iterrows():
    print(f"  {row['airport_id']} {row['flight_number']} {row['flight_date']} {row['movement_type']}: diff={row['time_difference_minutes']}m | {row['source_a']}({row['source_a_raw_time']}) vs {row['source_b']}({row['source_b_raw_time']})")

df_dist = pd.read_sql_query("SELECT * FROM deduplication_audit WHERE resolution_status = 'SPLIT_DISTINCT_LEG'", conn)
print(f"\nDistinct separate operations: {len(df_dist)}")
for idx, row in df_dist.head(5).iterrows():
    print(f"  {row['airport_id']} {row['flight_number']} {row['flight_date']} {row['movement_type']}: diff={row['time_difference_minutes']}m | {row['source_a']}({row['source_a_raw_time']}) vs {row['source_b']}({row['source_b_raw_time']})")

print("\n=== 2. EVENT RECONCILIATION ===")
# Raw records count by source
raw_source_counts = {
    "damairport_official": 1434,
    "alpairport_official": 250,
    "deirezzorairport_official": 0,
    "qamishliairport_official": 0,
    "flightradar24_dam": 106 + 107, # 213
    "flightradar24_alp": 34 + 33,   # 67
    "flightradar24_dez": 3 + 3,     # 6
    "aviationstack_dam": 90 + 92,   # 182
}
total_raw = sum(raw_source_counts.values())
print(f"Total raw records collected across all sources: {total_raw}")
for src, cnt in raw_source_counts.items():
    print(f"  {src}: {cnt}")

# Explain reconciliation:
# Total raw ingested: 2,152
# Total merged away: 191
# Total canonical events remaining: 2,152 - 191 = 1,961!
print(f"\nReconciliation Math:")
print(f"  Total Raw Records: {total_raw}")
print(f"  Minus Verified Merges: {len(df_merged)}")
print(f"  Equals Canonical Flight Events: {total_raw - len(df_merged)} (Database count: 1961)")

print("\n=== 3. FLIGHT STATUS BREAKDOWN ACROSS DATES ===")
c.execute("""
SELECT 
    CASE 
        WHEN flight_date > '2026-10-10' THEN 'future (> 2026-10-10)'
        ELSE 'past_or_current (<= 2026-10-10)'
    END as period,
    flight_status,
    count(*)
FROM flight_events
GROUP BY period, flight_status
ORDER BY period, count(*) desc
""")
for r in c.fetchall():
    print(f"  {r[0]} | {r[1]} | {r[2]}")

print("\n=== 4. DAMASCUS FLIGHTS BY DATE AND STATUS ===")
c.execute("""
SELECT flight_date, 
       sum(case when flight_status = 'scheduled' then 1 else 0 end) as scheduled,
       sum(case when flight_status = 'landed' then 1 else 0 end) as landed,
       sum(case when flight_status = 'active' then 1 else 0 end) as active,
       sum(case when flight_status = 'cancelled' then 1 else 0 end) as cancelled,
       sum(case when flight_status = 'diverted' then 1 else 0 end) as diverted,
       sum(case when flight_status = 'unknown' then 1 else 0 end) as unknown,
       count(*) as total
FROM flight_events
WHERE airport_id = 'DAM'
GROUP BY flight_date
ORDER BY flight_date
""")
for r in c.fetchall():
    print(f"  {r[0]}: total={r[7]}, sched={r[1]}, landed={r[2]}, active={r[3]}, canc={r[4]}, div={r[5]}, unk={r[6]}")

print("\n=== 5. CHECK 2024 MISSING DATES IN HISTORICAL TABLE ===")
c.execute("""
SELECT count(*), coverage_status FROM historical_daily_movements_2024 GROUP BY coverage_status
""")
for r in c.fetchall():
    print(f"  Coverage status '{r[1]}': {r[0]} rows")

c.execute("""
SELECT flight_date, movement_type, active, landed, scheduled, total_recorded_operations, coverage_status, status_note 
FROM historical_daily_movements_2024 
WHERE total_recorded_operations = 0
ORDER BY flight_date
""")
print("\nZero-operation rows in 2024 historical table (8 calendar dates, 15 rows total):")
for r in c.fetchall():
    print(f"  {r[0]} | {r[1]} | total={r[5]} | status={r[6]} | note={r[7]}")

print("\n=== 6. RECORD-LEVEL RELATIONSHIPS & INTRA-SOURCE DUPLICATES ===")
c.execute("""
SELECT canonical_event_id, airport_id, flight_number, movement_type, flight_date, source_a, source_b, time_difference_minutes, matching_rule
FROM deduplication_audit
WHERE source_a = source_b
""")
intra = c.fetchall()
print(f"Intra-source merges found: {len(intra)}")
for r in intra:
    print(f"  {r}")

# Check false merges
c.execute("""
SELECT count(*) FROM deduplication_audit 
WHERE resolution_status = 'MERGED_VERIFIED' 
  AND time_difference_minutes > 60
""")
print(f"Merges with time difference > 60 min: {c.fetchone()[0]}")

# Check if any arrival was ever merged with a departure
c.execute("""
SELECT count(*) FROM deduplication_audit
WHERE resolution_status = 'MERGED_VERIFIED'
  AND canonical_event_id IN (
      SELECT event_id FROM flight_events WHERE movement_type = 'arrival'
  )
  AND canonical_event_id IN (
      SELECT event_id FROM flight_events WHERE movement_type = 'departure'
  )
""")
print(f"Cross-direction merges (arrival + departure merged): {c.fetchone()[0]}")
