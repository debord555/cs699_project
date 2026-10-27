"""Location extraction worker.

Loop:
  1. Pick one unprocessed article (status 'ready', body present).
  2. Ask the LLM for the locations mentioned in its body.
  3. For each location, reuse the matching row in `locations` (case-insensitive
     name match) or create it, then link it in `article_location_map`.
  4. Mark the article 'llm_done' (or 'llm_failed' on error).
  5. If there was nothing to process, sleep and try again.

Usage:  python locate.py
"""

import json
import os
import re
import time

import requests
from dotenv import load_dotenv

from db import get_connection
from settings import LLM_MAX_BODY_CHARS, LLM_MAX_TOKENS, LLM_TIMEOUT, LOCATE_IDLE_SECONDS

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:13305/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3-8B-GGUF-Q4_K_M")

PROMPT = """List every geographic location (city, town, district, state, country, \
landmark) mentioned in the news article below.
Reply with ONLY a JSON array, no other text. Each item must be an object:
{{"name": "<place name>", "latitude": <number>, "longitude": <number>}}
Use your best estimate for the coordinates. Order items by first mention.
If there are no locations, reply with [].

Article:
{body}
/no_think"""


def next_article(conn):
    # SKIP LOCKED lets several workers run side by side without grabbing the same article
    return conn.execute(
        "SELECT id, body FROM articles "
        "WHERE status = 'ready' AND body IS NOT NULL "
        "ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED"
    ).fetchone()


def ask_llm(body):
    resp = requests.post(
        f"{LLM_BASE_URL}/chat/completions",
        json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": PROMPT.format(body=body[:LLM_MAX_BODY_CHARS])}],
            "temperature": 0,
            # stops runaway repetition loops instead of waiting for LLM_TIMEOUT
            "max_tokens": LLM_MAX_TOKENS,
        },
        timeout=LLM_TIMEOUT,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    text = re.sub(r"(?s)<think>.*?</think>", "", text)
    match = re.search(r"(?s)\[.*\]", text)
    if not match:
        raise ValueError(f"No JSON array in LLM reply: {text[:200]!r}")
    return parse_locations(json.loads(match.group(0)))


def parse_locations(items):
    locations = []
    seen = set()
    for item in items:
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        lat, lon = to_float(item.get("latitude")), to_float(item.get("longitude"))
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            lat = lon = None
        locations.append((name, lat, lon))
    return locations


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_or_create_location(conn, name, lat, lon):
    row = conn.execute(
        "SELECT id FROM locations WHERE lower(location_name) = lower(%s) ORDER BY id LIMIT 1",
        (name,),
    ).fetchone()
    if row:
        return row[0]
    return conn.execute(
        "INSERT INTO locations (location_name, latitude, longitude) VALUES (%s, %s, %s) RETURNING id",
        (name, lat, lon),
    ).fetchone()[0]


def process_one(conn):
    """Process one article. Returns False if there was nothing to do."""
    with conn.transaction():
        article = next_article(conn)
        if article is None:
            return False
        article_id, body = article

        try:
            locations = ask_llm(body)
        except Exception as e:
            conn.execute(
                "UPDATE articles SET status = 'llm_failed', error = %s WHERE id = %s",
                (str(e)[:1000], article_id),
            )
            print(f"Article {article_id}: failed ({e})")
            return True

        for order, (name, lat, lon) in enumerate(locations, start=1):
            location_id = get_or_create_location(conn, name, lat, lon)
            conn.execute(
                "INSERT INTO article_location_map (article_id, location_id, mention_order) "
                "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (article_id, location_id, order),
            )

        conn.execute(
            "UPDATE articles SET status = 'llm_done', error = NULL WHERE id = %s",
            (article_id,),
        )
        print(f"Article {article_id}: {len(locations)} location(s) {[l[0] for l in locations]}")
        return True


def main():
    with get_connection() as conn:
        while True:
            if not process_one(conn):
                time.sleep(LOCATE_IDLE_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
