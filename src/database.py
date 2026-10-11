import sqlite3
import json
from typing import Generator
from src.config import DB_PATH, SYRIAN_AIRPORTS_REGISTRY

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(drop_existing: bool = False):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        if drop_existing:
            conn.executescript("""
            DROP TABLE IF EXISTS event_evidence;
            DROP TABLE IF EXISTS historical_coverage_matrix;
            DROP TABLE IF EXISTS ingestion_runs;
            DROP TABLE IF EXISTS deduplication_audit;
            DROP TABLE IF EXISTS data_quality_audit;
            DROP TABLE IF EXISTS historical_daily_movements_2024;
            DROP TABLE IF EXISTS damascus_daily_movements;
            DROP TABLE IF EXISTS daily_airport_movements;
            DROP TABLE IF EXISTS flight_events;
            DROP TABLE IF EXISTS raw_source_records;
            DROP TABLE IF EXISTS source_registry;
            DROP TABLE IF EXISTS airports;
            """)
        else:
            # Check for column migrations on existing tables without dropping flight events
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(source_registry);")
            src_cols = [c[1] for c in cursor.fetchall()]
            if src_cols and "source_type" not in src_cols:
                cursor.execute("DROP TABLE source_registry;")

            cursor.execute("PRAGMA table_info(flight_events);")
            fe_cols = [c[1] for c in cursor.fetchall()]
            if fe_cols and "record_nature" not in fe_cols:
                cursor.execute("ALTER TABLE flight_events ADD COLUMN record_nature TEXT NOT NULL DEFAULT 'scheduled_service';")
                cursor.execute("ALTER TABLE flight_events ADD COLUMN operating_flight_number TEXT;")
                cursor.execute("ALTER TABLE flight_events ADD COLUMN operating_carrier TEXT;")
            if fe_cols and "estimated_dep_time" not in fe_cols:
                cursor.execute("ALTER TABLE flight_events ADD COLUMN estimated_dep_time TEXT;")
                cursor.execute("ALTER TABLE flight_events ADD COLUMN estimated_arr_time TEXT;")
                cursor.execute("ALTER TABLE flight_events ADD COLUMN raw_estimated_dep_time TEXT;")
                cursor.execute("ALTER TABLE flight_events ADD COLUMN raw_estimated_arr_time TEXT;")

            cursor.execute("PRAGMA table_info(event_evidence);")
            ee_cols = [c[1] for c in cursor.fetchall()]
            if ee_cols and "validity_status" not in ee_cols:
                cursor.execute("ALTER TABLE event_evidence ADD COLUMN validity_status TEXT NOT NULL DEFAULT 'valid';")
                cursor.execute("ALTER TABLE event_evidence ADD COLUMN retraction_reason TEXT;")
                cursor.execute("ALTER TABLE event_evidence ADD COLUMN superseded_by TEXT;")

        conn.executescript("""
        -- 1. Official Syrian Airports Registry
        CREATE TABLE IF NOT EXISTS airports (
            airport_id TEXT PRIMARY KEY,
            iata_code TEXT,
            icao_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            name_ar TEXT,
            city TEXT NOT NULL,
            city_ar TEXT,
            country TEXT NOT NULL,
            timezone TEXT NOT NULL DEFAULT 'Asia/Damascus',
            airport_type TEXT NOT NULL,
            classification TEXT NOT NULL,
            operational_status TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            elevation_ft INTEGER,
            runways_json TEXT,
            official_portal_url TEXT,
            api_endpoint TEXT,
            metadata_source TEXT,
            metadata_retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 2. Raw Source Ingest Records (Audit & Preservation)
        CREATE TABLE IF NOT EXISTS raw_source_records (
            raw_record_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            airport_id TEXT,
            retrieved_at_utc TIMESTAMP NOT NULL,
            query_parameters TEXT,
            source_record_id TEXT,
            raw_payload TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            source_url TEXT,
            http_status INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (airport_id) REFERENCES airports(airport_id)
        );

        CREATE INDEX IF NOT EXISTS idx_raw_source_airport ON raw_source_records(airport_id);
        CREATE INDEX IF NOT EXISTS idx_raw_source_id ON raw_source_records(source_id);

        -- 3. Canonical Flight Events (Layer A & Layer B)
        CREATE TABLE IF NOT EXISTS flight_events (
            event_id TEXT PRIMARY KEY,
            airport_id TEXT NOT NULL DEFAULT 'DAM',
            source TEXT NOT NULL,
            source_record_id TEXT,
            movement_type TEXT NOT NULL,
            airport_iata TEXT DEFAULT 'DAM',
            airport_icao TEXT DEFAULT 'OSDI',
            connected_airport_iata TEXT,
            connected_airport_icao TEXT,
            connected_airport_name TEXT,
            connected_country TEXT,
            connected_city TEXT,
            route_type TEXT,
            airline_name TEXT,
            airline_iata TEXT,
            airline_icao TEXT,
            flight_number TEXT,
            flight_date TEXT NOT NULL,
            local_operational_date TEXT,
            flight_status TEXT NOT NULL,
            scheduled_dep_time TEXT,
            estimated_dep_time TEXT,
            actual_dep_time TEXT,
            scheduled_arr_time TEXT,
            estimated_arr_time TEXT,
            actual_arr_time TEXT,
            raw_scheduled_dep_time TEXT,
            raw_estimated_dep_time TEXT,
            raw_actual_dep_time TEXT,
            raw_scheduled_arr_time TEXT,
            raw_estimated_arr_time TEXT,
            raw_actual_arr_time TEXT,
            aircraft_model TEXT,
            aircraft_registration TEXT,
            aircraft_icao24 TEXT,
            record_nature TEXT NOT NULL DEFAULT 'scheduled_service',
            operating_flight_number TEXT,
            operating_carrier TEXT,
            observed_or_derived TEXT DEFAULT 'observed',
            quality_flags TEXT,
            normalization_version TEXT DEFAULT '2.0',
            raw_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (airport_id) REFERENCES airports(airport_id)
        );

        CREATE INDEX IF NOT EXISTS idx_flight_airport ON flight_events(airport_id);
        CREATE INDEX IF NOT EXISTS idx_flight_date ON flight_events(flight_date);
        CREATE INDEX IF NOT EXISTS idx_movement_type ON flight_events(movement_type);
        CREATE INDEX IF NOT EXISTS idx_flight_status ON flight_events(flight_status);
        CREATE INDEX IF NOT EXISTS idx_airline ON flight_events(airline_name);
        CREATE INDEX IF NOT EXISTS idx_source ON flight_events(source);
        CREATE INDEX IF NOT EXISTS idx_flight_number ON flight_events(flight_number);

        -- 4. Daily Airport Movements (Independent Layer A per Airport)
        CREATE TABLE IF NOT EXISTS daily_airport_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airport_id TEXT NOT NULL,
            flight_date TEXT NOT NULL,
            arrival_count INTEGER DEFAULT 0,
            departure_count INTEGER DEFAULT 0,
            completed_movements INTEGER DEFAULT 0,
            scheduled_movements INTEGER DEFAULT 0,
            total_movements INTEGER DEFAULT 0,
            landed_count INTEGER DEFAULT 0,
            departed_count INTEGER DEFAULT 0,
            cancelled_count INTEGER DEFAULT 0,
            diverted_count INTEGER DEFAULT 0,
            scheduled_count INTEGER DEFAULT 0,
            active_count INTEGER DEFAULT 0,
            domestic_count INTEGER DEFAULT 0,
            international_count INTEGER DEFAULT 0,
            unique_aircraft_count INTEGER DEFAULT 0,
            unique_airlines_count INTEGER DEFAULT 0,
            passengers INTEGER,
            cargo REAL,
            source_id TEXT NOT NULL,
            observed_or_derived TEXT DEFAULT 'derived_from_flight_events',
            coverage_status TEXT NOT NULL DEFAULT 'observed',
            quality_flags TEXT,
            methodology_version TEXT DEFAULT '2.0',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(airport_id, flight_date),
            FOREIGN KEY (airport_id) REFERENCES airports(airport_id)
        );

        CREATE INDEX IF NOT EXISTS idx_daily_airport_date ON daily_airport_movements(airport_id, flight_date);

        -- Backward compatible view / table for Damascus specifically (Layer B Deep Dive)
        CREATE TABLE IF NOT EXISTS damascus_daily_movements (
            flight_date TEXT PRIMARY KEY,
            arrival_count INTEGER,
            departure_count INTEGER,
            completed_movements INTEGER,
            scheduled_movements INTEGER,
            total_movements INTEGER,
            landed_count INTEGER,
            departed_count INTEGER,
            cancelled_count INTEGER,
            diverted_count INTEGER,
            scheduled_count INTEGER,
            active_count INTEGER,
            domestic_count INTEGER,
            international_count INTEGER,
            unique_aircraft_count INTEGER,
            unique_airlines_count INTEGER,
            completeness_status TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 5. Multi-Airport Daily Movements (Syrian Gateways Aggregate DAM_ALP_LTK)
        -- CRITICAL: Preserved separately so combined numbers are NEVER mislabeled as Damascus-only!
        CREATE TABLE IF NOT EXISTS historical_daily_movements_2024 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_date TEXT NOT NULL,
            movement_type TEXT NOT NULL,
            scope TEXT NOT NULL DEFAULT 'DAM_ALP_LTK',
            active INTEGER DEFAULT 0,
            cancelled INTEGER DEFAULT 0,
            diverted INTEGER DEFAULT 0,
            landed INTEGER DEFAULT 0,
            scheduled INTEGER DEFAULT 0,
            unknown INTEGER DEFAULT 0,
            total_recorded_operations INTEGER DEFAULT 0,
            data_source TEXT,
            coverage_status TEXT NOT NULL DEFAULT 'observed',
            status_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(flight_date, movement_type, scope)
        );

        CREATE INDEX IF NOT EXISTS idx_hist_date ON historical_daily_movements_2024(flight_date);
        CREATE INDEX IF NOT EXISTS idx_hist_type ON historical_daily_movements_2024(movement_type);

        -- 6. Source & Provenance Registry
        CREATE TABLE IF NOT EXISTS source_registry (
            source_id TEXT PRIMARY KEY,
            provider_name TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'api',
            scope TEXT NOT NULL,
            supported_airports TEXT NOT NULL,
            date_ranges_covered TEXT,
            data_nature TEXT NOT NULL DEFAULT 'live_and_scheduled',
            source_url TEXT,
            data_type TEXT NOT NULL,
            licensing TEXT NOT NULL,
            access_status TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            last_successful_retrieval TIMESTAMP,
            last_available_event_timestamp TEXT,
            authentication_restrictions TEXT,
            known_limitations TEXT,
            freshness_indicator TEXT DEFAULT 'fresh',
            reliability_indicator TEXT DEFAULT 'high',
            notes TEXT,
            last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 7. Deduplication Audit Trail
        CREATE TABLE IF NOT EXISTS deduplication_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            canonical_event_id TEXT NOT NULL,
            airport_id TEXT NOT NULL DEFAULT 'DAM',
            flight_number TEXT NOT NULL,
            movement_type TEXT NOT NULL,
            flight_date TEXT NOT NULL,
            source_a TEXT NOT NULL,
            source_a_record_id TEXT,
            source_a_raw_time TEXT,
            source_b TEXT NOT NULL,
            source_b_record_id TEXT,
            source_b_raw_time TEXT,
            time_difference_minutes REAL,
            matching_rule TEXT NOT NULL,
            resolution_status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- 8. Data Quality & Integrity Checks Log
        CREATE TABLE IF NOT EXISTS data_quality_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            check_name TEXT NOT NULL,
            passed INTEGER NOT NULL,
            metric_value REAL,
            details TEXT
        );

        -- 9. Automated Ingestion Runs Log
        CREATE TABLE IF NOT EXISTS ingestion_runs (
            run_id TEXT PRIMARY KEY,
            run_timestamp TIMESTAMP NOT NULL,
            source_id TEXT NOT NULL,
            airport_id TEXT,
            status TEXT NOT NULL,
            records_fetched INTEGER DEFAULT 0,
            payload_hash TEXT,
            http_status INTEGER,
            error_message TEXT,
            duration_seconds REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_ingest_source ON ingestion_runs(source_id);
        CREATE INDEX IF NOT EXISTS idx_ingest_status ON ingestion_runs(status);

        -- 10. Historical Coverage Matrix (2024 to Present)
        CREATE TABLE IF NOT EXISTS historical_coverage_matrix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            airport_id TEXT NOT NULL,
            flight_date TEXT NOT NULL,
            coverage_classification TEXT NOT NULL,
            verified_movements_count INTEGER DEFAULT 0,
            commercial_records_count INTEGER DEFAULT 0,
            sources_checked TEXT,
            evidence_basis TEXT NOT NULL,
            notes TEXT,
            UNIQUE(airport_id, flight_date)
        );

        CREATE INDEX IF NOT EXISTS idx_cov_matrix_airport_date ON historical_coverage_matrix(airport_id, flight_date);
        CREATE INDEX IF NOT EXISTS idx_cov_matrix_class ON historical_coverage_matrix(coverage_classification);

        -- 11. Immutable Physical Event Evidence Ledger (Append-Only)
        CREATE TABLE IF NOT EXISTS event_evidence (
            evidence_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_record_id TEXT,
            evidence_type TEXT NOT NULL,
            observed_value TEXT NOT NULL,
            raw_timestamp TEXT,
            observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            snapshot_path TEXT,
            snapshot_sha256 TEXT,
            validity_status TEXT NOT NULL DEFAULT 'valid',
            retraction_reason TEXT,
            superseded_by TEXT,
            UNIQUE(event_id, source_name, evidence_type, observed_value)
        );

        CREATE INDEX IF NOT EXISTS idx_evidence_event ON event_evidence(event_id);
        CREATE INDEX IF NOT EXISTS idx_evidence_source ON event_evidence(source_name);
        CREATE INDEX IF NOT EXISTS idx_evidence_type ON event_evidence(evidence_type);

        CREATE TRIGGER IF NOT EXISTS trg_prevent_evidence_update
        BEFORE UPDATE ON event_evidence
        WHEN OLD.observed_value != NEW.observed_value
          OR OLD.raw_timestamp != NEW.raw_timestamp
          OR OLD.event_id != NEW.event_id
          OR OLD.evidence_type != NEW.evidence_type
          OR OLD.source_name != NEW.source_name
        BEGIN
            SELECT RAISE(ABORT, 'event_evidence ledger core observation fields are immutable: UPDATE operations on observations are strictly prohibited');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_prevent_evidence_delete
        BEFORE DELETE ON event_evidence
        BEGIN
            SELECT RAISE(ABORT, 'event_evidence ledger is append-only: DELETE operations are strictly prohibited');
        END;
        """)

        # Seed airports registry
        cursor = conn.cursor()
        for aid, ainfo in SYRIAN_AIRPORTS_REGISTRY.items():
            cursor.execute("""
            INSERT OR REPLACE INTO airports (
                airport_id, iata_code, icao_code, name, name_ar, city, city_ar,
                country, timezone, airport_type, classification, operational_status,
                latitude, longitude, elevation_ft, runways_json, official_portal_url,
                api_endpoint, metadata_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ainfo["airport_id"],
                ainfo.get("iata_code"),
                ainfo["icao_code"],
                ainfo["name"],
                ainfo.get("name_ar"),
                ainfo["city"],
                ainfo.get("city_ar"),
                ainfo["country"],
                ainfo["timezone"],
                ainfo["airport_type"],
                ainfo["classification"],
                ainfo["operational_status"],
                ainfo.get("latitude"),
                ainfo.get("longitude"),
                ainfo.get("elevation_ft"),
                json.dumps(ainfo.get("runways", [])),
                ainfo.get("official_portal_url"),
                ainfo.get("api_endpoint"),
                ainfo.get("metadata_source"),
            ))

        # Seed source registry with comprehensive operational & monitoring metadata
        sources_meta = [
            (
                "damairport_official",
                "Damascus International Airport Authority",
                "official_portal",
                "airport_specific",
                "DAM",
                "2026-09-30 to 2026-10-31",
                "scheduled_and_operational",
                "https://damairport.gov.sy/api/flights.php",
                "individual_flights",
                "Official airport public flight board",
                "available",
                "Retrieved & Verified: 1,434 flight events directly from airport operations database",
                "2026-10-10 14:45:00",
                "2026-10-31 23:00:00",
                "Public web endpoint (No auth required)",
                "Historical records prior to 2026-09-30 not hosted on public live operational board",
                "fresh",
                "authoritative",
                "Covers arrivals and departures with scheduled dates, times, airlines, routes, and operational statuses"
            ),
            (
                "alpairport_official",
                "Aleppo International Airport Authority",
                "official_portal",
                "airport_specific",
                "ALP",
                "2026-09-30 to 2026-10-11",
                "scheduled_and_operational",
                "https://alpairport.gov.sy/api/flights.php",
                "individual_flights",
                "Official airport public flight board",
                "available",
                "Retrieved & Verified: 250 flight events directly from airport operations database",
                "2026-10-10 14:45:00",
                "2026-10-11 19:00:00",
                "Public web endpoint (No auth required)",
                "Historical operational logs prior to 2026-09-30 not published on portal",
                "fresh",
                "authoritative",
                "Covers arrivals and departures for Aleppo with dates, times, airlines, and routes"
            ),
            (
                "qamishliairport_official",
                "Qamishli Airport Authority",
                "official_portal",
                "airport_specific",
                "KAC",
                "None (Portal active, records empty)",
                "scheduled",
                "https://qamishliairport.gov.sy/api/flights.php",
                "individual_flights",
                "Official airport public flight board",
                "available",
                "Verified: Portal responsive; authority currently publishes 0 flights",
                "2026-10-10 14:45:00",
                None,
                "Public web endpoint (No auth required)",
                "Authority web portal is reachable but flight board array is currently unpopulated",
                "checked_empty",
                "authoritative_zero_listed",
                "Official portal reachable; authority has not populated current operational board"
            ),
            (
                "deirezzorairport_official",
                "Deir ez-Zor Airport Authority",
                "official_portal",
                "airport_specific",
                "DEZ",
                "None (Portal active, records empty)",
                "scheduled",
                "https://deirezzorairport.gov.sy/api/flights.php",
                "individual_flights",
                "Official airport public flight board",
                "available",
                "Verified: Portal responsive; authority currently publishes 0 flights",
                "2026-10-10 14:45:00",
                None,
                "Public web endpoint (No auth required)",
                "Authority web portal is reachable but flight board array is currently unpopulated",
                "checked_empty",
                "authoritative_zero_listed",
                "Official portal reachable; authority has not populated current operational board"
            ),
            (
                "flightradar24",
                "Flightradar24 Airport Live Radar Feed",
                "terrestrial_adsb_radar",
                "airport_specific",
                "DAM, ALP, LTK, KAC, DEZ",
                "2026-10-09 to 2026-10-11 (Rolling 72h)",
                "live_and_recent_movements",
                "https://api.flightradar24.com/common/v1/airport.json",
                "individual_flights",
                "Flightradar24 proprietary / personal/research use",
                "available",
                "Retrieved & Verified: Live/recent flight records with aircraft airframe registrations, hexes, and routes",
                "2026-10-10 14:45:00",
                "2026-10-11 16:35:00",
                "Public rate-limited endpoint",
                "Public endpoint retrieves rolling active flights (historical >7 days requires paid Business subscription)",
                "fresh",
                "high_telemetry",
                "Ground ADS-B radar sensors provide physical wheels-off and wheels-down timestamps"
            ),
            (
                "aviationstack_live",
                "AviationStack Flight Tracking API",
                "commercial_api_feed",
                "airport_specific",
                "DAM",
                "2026-10-09 to 2026-10-10",
                "rolling_operational_feed",
                "https://api.aviationstack.com/v1/flights",
                "individual_flights",
                "AviationStack API terms (Free/Standard)",
                "available",
                "Retrieved & Verified: Live airport flight events with scheduled/actual timestamps and airline codes",
                "2026-10-10 14:45:00",
                "2026-10-10 23:00:00",
                "API Key required in query string",
                "Historical queries prior to rolling window blocked by tier (HTTP 403 function_access_restricted); timestamps require Asia/Damascus wall-clock localization",
                "fresh",
                "medium_commercial",
                "Provides commercial flight tracking with codeshared mappings"
            ),
            (
                "syria_economic_monitor",
                "Syria Economic Monitor (World Bank / Data Partnership)",
                "research_aggregate",
                "multi_airport",
                "DAM, ALP, LTK",
                "2024-01-01 to 2024-10-15",
                "historical_daily_aggregates",
                "https://datapartnership.org/syria-economic-monitor/notebooks/aviation/aviation_update.html",
                "daily_aggregates",
                "Open research / Creative Commons equivalent",
                "available",
                "Retrieved & Verified: 578 daily records (289 dep, 289 arr) covering 2024-01-01 to 2024-10-15 across Syrian gateways",
                "2026-10-10 14:45:00",
                "2024-10-15 00:00:00",
                "Public research dataset",
                "Preserved strictly as multi-airport gateway aggregate (DAM_ALP_LTK); individual airport breakdown not provided; 8 provider outage dates recorded as gaps",
                "historical_archive",
                "high_benchmark",
                "Authoritative historical multi-airport gateway operations baseline"
            ),
            (
                "syrian_eaip",
                "Syrian General Authority of Civil Aviation (GACA) eAIP",
                "regulatory_publication",
                "national",
                "DAM, ALP, LTK, DEZ, KAC, PMS, OMDM",
                "Static Regulatory Reference",
                "regulatory_metadata",
                "https://eaip.gaca.gov.sy/",
                "metadata_and_regulatory",
                "Official Government Aeronautical Information Publication",
                "available",
                "Retrieved & Verified: Authoritative aerodrome registry, runways, navigational specifications, and NOTAMs",
                "2026-10-10 14:45:00",
                None,
                "Public official aeronautical portal",
                "Contains static regulatory specifications and NOTAMs; does not publish individual real-time passenger flight boards",
                "authoritative_static",
                "legal_reference",
                "Authoritative legal reference for Syrian airspace structure and aerodrome identifiers"
            ),
            (
                "ourairports",
                "OurAirports Aeronautical Database",
                "geospatial_open_data",
                "national",
                "DAM, ALP, LTK, DEZ, KAC, PMS, OMDM",
                "Static Geospatial Reference",
                "geospatial_metadata",
                "https://davidmegginson.github.io/ourairports-data/airports.csv",
                "metadata",
                "Public Domain (CC0)",
                "available",
                "Retrieved & Verified: Global coordinates, elevation, runway specs",
                "2026-10-10 14:45:00",
                None,
                "Public domain download",
                "Geospatial attributes only; does not supply flight movement observations",
                "authoritative_static",
                "high_geospatial",
                "Open geospatial airport reference"
            ),
            (
                "opensky_network",
                "OpenSky Network Historical API",
                "academic_adsb_archive",
                "airport_specific",
                "OSDI, OSAP, OSLK, OSDZ, OSKL",
                "Historical Archive",
                "state_vectors",
                "https://opensky-network.org/api/flights/departure",
                "individual_flights",
                "Academic / Non-commercial",
                "blocked_institutional",
                "Blocked: Anonymous historical queries return HTTP 403 'You cannot access historical flights'",
                None,
                None,
                "Requires institutional academic researcher credentials and Trino cluster access",
                "Anonymous API queries restricted; academic research agreement required for batch extraction",
                "blocked",
                "unreachable_without_creds",
                "Requires institutional academic researcher credentials and Trino cluster access"
            ),
            (
                "flightaware_aeroapi",
                "FlightAware AeroAPI",
                "commercial_proprietary_api",
                "airport_specific",
                "DAM, ALP, LTK, DEZ, KAC",
                "Commercial Live/Historical",
                "individual_flights",
                "https://flightaware.com/commercial/aeroapi/",
                "individual_flights",
                "Commercial proprietary",
                "blocked_paywall",
                "Blocked: Historical queries older than 7 days require paid AeroAPI commercial tier ($100+/mo)",
                None,
                None,
                "Requires paid API key and commercial contract",
                "Paywalled commercial provider; historical queries blocked on free tier",
                "blocked",
                "unreachable_without_creds",
                "Commercial enterprise subscription required"
            ),
            (
                "adsb_exchange",
                "ADS-B Exchange Historical Feeds",
                "commercial_adsb_archive",
                "national",
                "Syria Airspace",
                "Commercial Historical Archive",
                "state_vectors",
                "https://globe.adsbexchange.com/",
                "state_vectors",
                "Commercial proprietary",
                "blocked_paywall",
                "Blocked: Historical REST API endpoints require RapidAPI enterprise subscription ($100-$1000/mo)",
                None,
                None,
                "RapidAPI enterprise subscription required",
                "Commercial proprietary historical feed requiring enterprise plan; web map does not permit automated scraping",
                "blocked",
                "unreachable_without_creds",
                "Commercial enterprise subscription required"
            )
        ]

        for s in sources_meta:
            cursor.execute("""
            INSERT OR REPLACE INTO source_registry (
                source_id, provider_name, source_type, scope, supported_airports,
                date_ranges_covered, data_nature, source_url, data_type, licensing,
                access_status, verification_status, last_successful_retrieval,
                last_available_event_timestamp, authentication_restrictions,
                known_limitations, freshness_indicator, reliability_indicator, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, s)

        conn.commit()
        migrate_database(conn)

def migrate_database(conn: sqlite3.Connection):
    """
    Non-destructively ensures event_evidence table exists and seeds initial
    immutable evidence records for all pre-existing verified physical movements.
    """
    import hashlib
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS event_evidence (
        evidence_id TEXT PRIMARY KEY,
        event_id TEXT NOT NULL,
        source_name TEXT NOT NULL,
        source_record_id TEXT,
        evidence_type TEXT NOT NULL,
        observed_value TEXT NOT NULL,
        raw_timestamp TEXT,
        observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        snapshot_path TEXT,
        snapshot_sha256 TEXT,
        validity_status TEXT NOT NULL DEFAULT 'valid',
        retraction_reason TEXT,
        superseded_by TEXT,
        UNIQUE(event_id, source_name, evidence_type, observed_value)
    );
    CREATE INDEX IF NOT EXISTS idx_evidence_event ON event_evidence(event_id);
    CREATE INDEX IF NOT EXISTS idx_evidence_source ON event_evidence(source_name);
    CREATE INDEX IF NOT EXISTS idx_evidence_type ON event_evidence(evidence_type);

    CREATE TRIGGER IF NOT EXISTS trg_prevent_evidence_update
    BEFORE UPDATE ON event_evidence
    WHEN OLD.observed_value != NEW.observed_value
      OR OLD.raw_timestamp != NEW.raw_timestamp
      OR OLD.event_id != NEW.event_id
      OR OLD.evidence_type != NEW.evidence_type
      OR OLD.source_name != NEW.source_name
    BEGIN
        SELECT RAISE(ABORT, 'event_evidence ledger core observation fields are immutable: UPDATE operations on observations are strictly prohibited');
    END;

    CREATE TRIGGER IF NOT EXISTS trg_prevent_evidence_delete
    BEFORE DELETE ON event_evidence
    BEGIN
        SELECT RAISE(ABORT, 'event_evidence ledger is append-only: DELETE operations are strictly prohibited');
    END;
    """)

    # Check if event_evidence is already populated
    cursor.execute("SELECT count(*) FROM event_evidence;")
    cnt = cursor.fetchone()[0]
    if cnt == 0:
        cursor.execute("SELECT * FROM flight_events WHERE record_nature='physical_movement';")
        col_names = [d[0] for d in cursor.description]
        phys_rows = [dict(zip(col_names, row)) for row in cursor.fetchall()]

        from src.normalizer import determine_evidence_source
        insert_sql = """
        INSERT OR IGNORE INTO event_evidence (
            evidence_id, event_id, source_name, source_record_id, evidence_type,
            observed_value, raw_timestamp, snapshot_path, snapshot_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        for r in phys_rows:
            eid = r["event_id"]
            src = r.get("source") or "unknown"
            srec = r.get("source_record_id")

            if r.get("actual_arr_time"):
                raw_ts = r.get("raw_actual_arr_time")
                disc_src = determine_evidence_source(src, raw_ts)
                etype = "adsb_touchdown" if disc_src == "flightradar24" else "commercial_touchdown"
                val = r["actual_arr_time"]
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|{etype}|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(insert_sql, (ev_id, eid, disc_src, srec, etype, val, raw_ts, None, None))

            if r.get("actual_dep_time"):
                raw_ts = r.get("raw_actual_dep_time")
                disc_src = determine_evidence_source(src, raw_ts)
                etype = "adsb_takeoff" if disc_src == "flightradar24" else "commercial_takeoff"
                val = r["actual_dep_time"]
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|{etype}|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(insert_sql, (ev_id, eid, disc_src, srec, etype, val, raw_ts, None, None))

            if r.get("aircraft_registration"):
                disc_src = "flightradar24" if "flightradar24" in src else ("aviationstack" if "aviationstack" in src else src.split("+")[0])
                val = str(r["aircraft_registration"]).strip().upper()
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|aircraft_registration|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(insert_sql, (ev_id, eid, disc_src, srec, "aircraft_registration", val, None, None, None))

            if r.get("aircraft_icao24"):
                disc_src = "flightradar24" if "flightradar24" in src else ("aviationstack" if "aviationstack" in src else src.split("+")[0])
                val = str(r["aircraft_icao24"]).strip().upper()
                ev_id = "ev_" + hashlib.sha256(f"{eid}|{disc_src}|aircraft_icao24|{val}".encode("utf-8")).hexdigest()[:16]
                cursor.execute(insert_sql, (ev_id, eid, disc_src, srec, "aircraft_icao24", val, None, None, None))

        conn.commit()

if __name__ == '__main__':
    init_db()
    print(f"Initialized database at: {DB_PATH}")
