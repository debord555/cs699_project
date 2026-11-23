from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from psycopg_pool import ConnectionPool
import os
import math
from datetime import datetime, timezone, timedelta

def split_interval(start, end, n):
    step = (end - start) / n
    return [(start + i * step, start + (i + 1) * step) for i in range(n)]

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
    open=False,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()

app = FastAPI(lifespan=lifespan)

@app.get("/api/get_news_ids")
def getNews(lat_min: float, lon_min: float, lat_max: float, lon_max: float, zoom: int, per_cell: int = 5, before: datetime | None = None, q: str | None = None):
    # Cell size inferred from Leaflet's docs
    cell = 360 / 2**zoom / 4
    # Snap the box outward to cell edges so cells at the screen border are counted in full
    lat_min = math.floor(lat_min / cell) * cell
    lon_min = math.floor(lon_min / cell) * cell
    lat_max = math.ceil(lat_max / cell) * cell
    lon_max = math.ceil(lon_max / cell) * cell
    if before is None:
        before = datetime.now(timezone.utc)
    window = 7 * (2 ** max(0, zoom - 5))
    after = before - timedelta(days=window)
    # Text search: only keep articles matching the search words, if any were given.
    search = ""
    if q and q.strip():
        search = "AND a.search_tsv @@ websearch_to_tsquery('english', %(q)s)"
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
            ) t
            WHERE rn <= %(per_cell)s;
            """, {"cell": cell, "lat_min": lat_min, "lat_max": lat_max,
                  "lon_min": lon_min, "lon_max": lon_max, "per_cell": per_cell,
                  "before": before, "after": after, "q": q}).fetchall()

@app.get("/api/get_news")
def getNewsByIds(id: int):
    with pool.connection() as conn:
        return conn.execute("""
            SELECT a.id, a.title, a.url, a.published_at, a.image_url
            FROM articles a
            WHERE a.id = %(ids)s;
            """, {"ids": id}).fetchall()
