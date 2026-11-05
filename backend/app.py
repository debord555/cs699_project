from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from psycopg_pool import ConnectionPool
import os
import math

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
def getNews(lat_min: float, lon_min: float, lat_max: float, lon_max: float, zoom: int, per_cell: int = 5):
    # Cell size inferred from Leaflet's docs
    cell = 360 / 2**zoom / 4
    # Snap the box outward to cell edges so cells at the screen border are counted in full
    lat_min = math.floor(lat_min / cell) * cell
    lon_min = math.floor(lon_min / cell) * cell
    lat_max = math.ceil(lat_max / cell) * cell
    lon_max = math.ceil(lon_max / cell) * cell
    with pool.connection() as conn:
        return conn.execute("""
            SELECT id, latitude, longitude FROM (
                SELECT a.id, l.latitude, l.longitude,
                       ROW_NUMBER() OVER (
                           PARTITION BY floor(l.latitude / %(cell)s), floor(l.longitude / %(cell)s)
                           ORDER BY al.mention_order ASC, a.published_at DESC, a.id
                       ) AS rn
                FROM locations l
                JOIN article_location_map al ON l.id = al.location_id
                JOIN articles a ON a.id = al.article_id
                WHERE l.latitude >= %(lat_min)s AND l.latitude < %(lat_max)s
                    AND l.longitude >= %(lon_min)s AND l.longitude < %(lon_max)s
            ) t
            WHERE rn <= %(per_cell)s;
            """, {"cell": cell, "lat_min": lat_min, "lat_max": lat_max,
                  "lon_min": lon_min, "lon_max": lon_max, "per_cell": per_cell}).fetchall()

