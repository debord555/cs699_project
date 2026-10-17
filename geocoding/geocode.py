import argparse
import os

import psycopg
from dotenv import load_dotenv
from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

load_dotenv()

USER_AGENT = "NewsRadarBot/0.1 (student project; +https://github.com/debord555/cs699_project)"
COUNTRY_CODES = "in"

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


def fetch_coordinates(name, hint=None):
    """Return (latitude, longitude) for a place name, or None if Nominatim finds nothing.

    `hint` (e.g. a state like 'Bihar') narrows ambiguous names; if the hinted
    query finds nothing we retry with the bare name.
    """
    queries = [f"{name}, {hint}", name] if hint else [name]
    for query in queries:
        result = _geocode(query, country_codes=COUNTRY_CODES, exactly_one=True)
        if result:
            return result.latitude, result.longitude
    return None


def get_or_create_location(conn, name, hint=None):
    """Return the locations.id for `name`, geocoding and inserting it if it is new.

    Names Nominatim cannot find are stored with NULL coordinates so they are not
    looked up again. Network errors are raised, not cached.
    """
    name = " ".join(name.split())
    row = conn.execute(
        "SELECT id FROM locations WHERE lower(location_name) = lower(%s) LIMIT 1", (name,)
    ).fetchone()
    if row:
        return row[0]

    coords = fetch_coordinates(name, hint)
    latitude, longitude = coords if coords else (None, None)
    return conn.execute(
        "INSERT INTO locations (location_name, latitude, longitude) VALUES (%s, %s, %s) RETURNING id",
        (name, latitude, longitude),
    ).fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Geocode place names and store them in the locations table.")
    parser.add_argument("names", nargs="+", help="place names, e.g. Guwahati 'Majuli'")
    parser.add_argument("--hint", help="state/region to disambiguate, e.g. Assam")
    args = parser.parse_args()

    with get_connection() as conn:
        for name in args.names:
            try:
                location_id = get_or_create_location(conn, name, args.hint)
            except GeocoderServiceError as exc:
                print(f"{name}: geocoding failed ({exc})")
                continue
            conn.commit()
            lat, lon = conn.execute(
                "SELECT latitude, longitude FROM locations WHERE id = %s", (location_id,)
            ).fetchone()
            print(f"{name}: id={location_id} lat={lat} lon={lon}")


if __name__ == "__main__":
    main()
