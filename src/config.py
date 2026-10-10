import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = BASE_DIR / "reports"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = DATA_DIR / "damascus_airport.db"

# Airport Reference
AIRPORT_IATA = "DAM"
AIRPORT_ICAO = "OSDI"
AIRPORT_NAME = "Damascus International Airport"
AIRPORT_COUNTRY = "Syria"
AIRPORT_LAT = 33.415001
AIRPORT_LON = 36.515202

# Domestic Syrian Airports
SYRIAN_AIRPORT_IATAS = {"DAM", "ALP", "LTK", "KAC", "PMS"}
SYRIAN_AIRPORT_ICAOS = {"OSDI", "OSAP", "OSLK", "OSKL"}

# AviationStack Access Key from Syria Economic Monitor research
AVIATIONSTACK_KEY = os.environ.get("AVIATIONSTACK_KEY", "12925396bddce38222e47eed53e76e6c")
