# config.py — city list, thresholds, DB path

import os

# ─── Database ─────────────────────────────────────────────────────────────────
DB_PATH = os.environ.get("PULSE_DB", "pulse.db")

# ─── Cities ───────────────────────────────────────────────────────────────────
CITIES = [
    {"name": "New York",   "country": "US",  "latitude": 40.7128,  "longitude": -74.0060,  "timezone": "America/New_York"},
    {"name": "London",     "country": "GB",  "latitude": 51.5074,  "longitude": -0.1278,   "timezone": "Europe/London"},
    {"name": "Hyderabad",  "country": "IN",  "latitude": 17.3850,  "longitude": 78.4867,   "timezone": "Asia/Kolkata"},
    {"name": "Singapore",  "country": "SG",  "latitude": 1.3521,   "longitude": 103.8198,  "timezone": "Asia/Singapore"},
    {"name": "Cairo",      "country": "EG",  "latitude": 30.0444,  "longitude": 31.2357,   "timezone": "Africa/Cairo"},
    {"name": "Reykjavik",  "country": "IS",  "latitude": 64.1355,  "longitude": -21.8954,  "timezone": "Atlantic/Reykjavik"},
    {"name": "Sydney",     "country": "AU",  "latitude": -33.8688, "longitude": 151.2093,  "timezone": "Australia/Sydney"},
    {"name": "São Paulo",  "country": "BR",  "latitude": -23.5505, "longitude": -46.6333,  "timezone": "America/Sao_Paulo"},
]

# ─── Scheduler ────────────────────────────────────────────────────────────────
SCHEDULE_INTERVAL_HOURS = 1

# ─── API ──────────────────────────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000

# ─── Open-Meteo ───────────────────────────────────────────────────────────────
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL  = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS  = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"

# ─── Transform thresholds ─────────────────────────────────────────────────────
TEMP_MIN_C         = -90.0   # world record low is −89.2°C
TEMP_MAX_C         =  60.0   # world record high is 56.7°C
HUMIDITY_MIN_PCT   =   0.0
HUMIDITY_MAX_PCT   = 100.0
FUTURE_SKEW_HOURS  =   1     # reject timestamps more than this far in the future

# ─── Anomaly detection ────────────────────────────────────────────────────────
ANOMALY_Z_THRESHOLD = 2.5
ANOMALY_WINDOW_DAYS = 30
