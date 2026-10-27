
import os
import time

import psycopg
from dotenv import load_dotenv
from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

load_dotenv()

USER_AGENT = "NewsRadarBot/0.1 (student project; +https://github.com/debord555/cs699_project)"
COUNTRY_CODES = "in"
IDLE_SECONDS = 10  # wait when no location needs geocoding
SERVICE_ERROR_SECONDS = 60  # wait when Nominatim is unreachable or refusing requests

# Nominatim usage policy: at most 1 request per second
_geolocator = Nominatim(user_agent=USER_AGENT, timeout=10)
_geocode = RateLimiter(
    _geolocator.geocode, min_delay_seconds=1, max_retries=2, error_wait_seconds=5, swallow_exceptions=False
)


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "newsradar"),
        user=os.getenv("DB_USER", "newsradar"),
        password=os.getenv("DB_PASSWORD"),
    )


def fetch_coordinates(name):
    result = _geocode(name, country_codes=COUNTRY_CODES, exactly_one=True)
    if result:
        return result.latitude, result.longitude
    return None


def next_location(conn):
    return conn.execute(
        "SELECT id, location_name FROM locations "
        "WHERE not_found IS NOT TRUE AND (latitude IS NULL OR longitude IS NULL) "
        "ORDER BY id LIMIT 1 FOR UPDATE"
    ).fetchone()


def process_one(conn):
    with conn.transaction():
        row = next_location(conn)
        if row is None:
            return False
        location_id, name = row

        name = " ".join((name or "").split())
        coords = fetch_coordinates(name) if name else None
        if coords:
            conn.execute(
                "UPDATE locations SET latitude = %s, longitude = %s, not_found = FALSE WHERE id = %s",
                (coords[0], coords[1], location_id),
            )
            print(f"Location {location_id} {name!r}: {coords[0]}, {coords[1]}")
        else:
            conn.execute("UPDATE locations SET not_found = TRUE WHERE id = %s", (location_id,))
            print(f"Location {location_id} {name!r}: not found")
        return True


def main():
    with get_connection() as conn:
        while True:
            try:
                if not process_one(conn):
                    time.sleep(IDLE_SECONDS)
            except GeocoderServiceError as e:
                print(f"Geocoding service error ({e}); retrying in {SERVICE_ERROR_SECONDS}s")
                time.sleep(SERVICE_ERROR_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
