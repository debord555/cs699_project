"""Location extraction worker.

Loop:
  1. Pick one unprocessed article (status 'ready', body present).
  2. Find the place names mentioned in its body with spaCy (en_core_web_trf).
  3. For each location, reuse the matching row in `locations` (case-insensitive
     name match) or create it, then link it in `article_location_map`.
  4. Mark the article 'llm_done' (or 'llm_failed' on error).
  5. If there was nothing to process, sleep and try again.

Usage:  python locate.py
"""

import re
import time
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="torch")

import spacy

from db import get_connection
from settings import LLM_MAX_BODY_CHARS, LLM_MAX_TOKENS, LLM_TIMEOUT, LOCATE_IDLE_SECONDS

# GPE: cities, districts, states, countries; LOC: rivers, regions; FAC: stadiums, markets
PLACE_LABELS = {"GPE", "LOC", "FAC"}
SUFFIXES = re.compile(r"\s+(village|district|city|town|area)$", re.I)

# loaded once at startup; takes a few seconds
nlp = spacy.load("en_core_web_trf")


def extract_places(body):
    """Return the place names mentioned in body, in order of first mention."""
    names = []
    seen = set()
    for ent in nlp(body[:LLM_MAX_BODY_CHARS]).ents:
        if ent.label_ not in PLACE_LABELS:
            continue
        name = re.sub(r"('s|-based)$", "", ent.text.strip())
        name = SUFFIXES.sub("", name).strip()
        if name.isupper() or name.islower():
            name = name.title()  # GUWAHATI / barpeta -> Guwahati / Barpeta
        if name and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names


def next_article(conn):
    # SKIP LOCKED lets several workers run side by side without grabbing the same article
    return conn.execute(
        "SELECT id, body FROM articles "
        "WHERE status = 'ready' AND body IS NOT NULL "
        "ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED"
    ).fetchone()


def get_or_create_location(conn, name):
    row = conn.execute(
        "SELECT id FROM locations WHERE lower(location_name) = lower(%s) ORDER BY id LIMIT 1",
        (name,),
    ).fetchone()
    if row:
        return row[0]
    return conn.execute(
        "INSERT INTO locations (location_name) VALUES (%s) RETURNING id",
        (name,),
    ).fetchone()[0]


def process_one(conn):
    """Process one article. Returns False if there was nothing to do."""
    with conn.transaction():
        article = next_article(conn)
        if article is None:
            return False
        article_id, body = article

        try:
            locations = extract_places(body)
        except Exception as e:
            conn.execute(
                "UPDATE articles SET status = 'llm_failed', error = %s WHERE id = %s",
                (str(e)[:1000], article_id),
            )
            print(f"Article {article_id}: failed ({e})")
            return True

        for order, name in enumerate(locations, start=1):
            location_id = get_or_create_location(conn, name)
            conn.execute(
                "INSERT INTO article_location_map (article_id, location_id, mention_order) "
                "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (article_id, location_id, order),
            )

        conn.execute(
            "UPDATE articles SET status = 'llm_done', error = NULL WHERE id = %s",
            (article_id,),
        )
        print(f"Article {article_id}: {len(locations)} location(s) {locations}")
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
