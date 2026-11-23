import atexit
from dotenv import load_dotenv
from flask import Flask, abort, request
from psycopg_pool import ConnectionPool
import os
import math
from datetime import datetime, timezone, timedelta

load_dotenv()
pool = ConnectionPool(
    kwargs={
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME", "newsradar"),
        "user": os.getenv("DB_USER", "newsradar"),
        "password": os.getenv("DB_PASSWORD"),
    },
    min_size=1,
    max_size=10,
    open=True,
)

# Close the database connections when the server stops
atexit.register(pool.close)

app = Flask(__name__)

def parse_before(text):
    # The "before" date from the URL, such as 2026-11-01T00:00:00Z, or now if not given
    if not text:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        abort(400, "before must be a date and time such as 2026-11-01T00:00:00Z")

@app.get("/api/get_news_ids")
def getNews():

    lat_min = request.args.get("lat_min", type=float)
    lon_min = request.args.get("lon_min", type=float)
    lat_max = request.args.get("lat_max", type=float)
    lon_max = request.args.get("lon_max", type=float)
    zoom = request.args.get("zoom", type=int)

    if None in (lat_min, lon_min, lat_max, lon_max, zoom):
        abort(400, "lat_min, lon_min, lat_max, lon_max and zoom are required numbers")

    per_cell = request.args.get("per_cell", default=5, type=int)
    before = parse_before(request.args.get("before"))
    q = request.args.get("q")

    category = request.args.getlist("category", type=int)

    # Cell size inferred from Leaflet's docs
    cell = 360 / 2**zoom / 4

    # Snap the box outward to cell edges so cells at the screen border are counted in full
    lat_min = math.floor(lat_min / cell) * cell
    lon_min = math.floor(lon_min / cell) * cell
    lat_max = math.ceil(lat_max / cell) * cell
    lon_max = math.ceil(lon_max / cell) * cell

    window = 7 * (2 ** max(0, zoom - 5))
    after = before - timedelta(days=window)

    # Text search: only keep articles matching the search words, if any were given.
    search = ""
    if q and q.strip():
        search = "AND a.search_tsv @@ websearch_to_tsquery('english', %(q)s)"

    # Category filter: only keep articles that have at least one of the chosen categories.
    # The URL lists them as ?category=1&category=4
    category_filter = ""
    if category:
        category_filter = """AND EXISTS (SELECT 1 FROM article_category_map ac
                                         WHERE ac.article_id = a.id
                                           AND ac.category_id = ANY(%(category)s))"""
        
    with pool.connection() as conn:
        return conn.execute(f"""
            SELECT id, latitude, longitude, location_id FROM (
                SELECT a.id, l.latitude, l.longitude, l.id AS location_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY floor(l.latitude / %(cell)s), floor(l.longitude / %(cell)s)
                           ORDER BY al.mention_order ASC, a.published_at DESC, a.id
                       ) AS rn
                FROM locations l
                JOIN article_location_map al ON l.id = al.location_id
                JOIN articles a ON a.id = al.article_id
                WHERE point(l.longitude, l.latitude) <@ box(point(%(lon_min)s, %(lat_min)s),
                                            point(%(lon_max)s, %(lat_max)s))
                    AND l.latitude >= %(lat_min)s AND l.latitude < %(lat_max)s
                    AND l.longitude >= %(lon_min)s AND l.longitude < %(lon_max)s
                    AND a.published_at < %(before)s AND a.published_at > %(after)s
                    {search}
                    {category_filter}
            ) t
            WHERE rn <= %(per_cell)s;
            """, {"cell": cell, "lat_min": lat_min, "lat_max": lat_max,
                  "lon_min": lon_min, "lon_max": lon_max, "per_cell": per_cell,
                  "before": before, "after": after, "q": q,
                  "category": category}).fetchall()

@app.get("/api/categories")
def getCategories():
    # Every category as [id, name], for the filter checkboxes in the sidebar
    with pool.connection() as conn:
        return conn.execute("SELECT id, name FROM categories ORDER BY id;").fetchall()

@app.get("/api/get_news")
def getNewsByIds():
    id = request.args.get("id", type=int)
    if id is None:
        abort(400, "id is required and must be a number")
    with pool.connection() as conn:
        rows = conn.execute("""
            SELECT a.id, a.title, a.url, a.published_at, a.image_url
            FROM articles a
            WHERE a.id = %(ids)s;
            """, {"ids": id}).fetchall()
        
    result = []
    for article_id, title, url, published_at, image_url in rows:
        if published_at is not None:
            published_at = published_at.isoformat()
        result.append([article_id, title, url, published_at, image_url])
    return result

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
