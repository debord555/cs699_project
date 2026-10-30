from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from psycopg_pool import ConnectionPool
import os

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
def getNews(lat_min: float, lon_min: float, lat_max: float, lon_max: float):
    with pool.connection() as conn:
        rows = conn.execute("""
        SELECT a.id
        FROM locations l, article_location_map al, articles a
        WHERE l.id = al.location_id AND a.id = al.article_id
            AND l.latitude >= %s AND l.longitude >= %s AND l.latitude <= %s AND l.longitude <= %s
        ORDER BY a.published_at DESC;
        """, (lat_min, lon_min, lat_max, lon_max)).fetchall()
    return rows
