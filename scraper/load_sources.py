from pathlib import Path

import yaml

from db import get_connection
from google_news import search_url

SOURCES_FILE = Path(__file__).parent / "sources.yaml"


def get_or_create_source(conn, name, domain, region_scope=None, language="en"):
    row = conn.execute("SELECT id FROM sources WHERE domain = %s", (domain,)).fetchone()
    if row:
        return row[0]
    row = conn.execute(
        "INSERT INTO sources (name, domain, region_scope, language) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (name, domain, region_scope, language),
    ).fetchone()
    return row[0]


def add_feed(conn, source_id, url, kind="rss", location_hint=None, category_hint=None, poll_minutes=30):
    conn.execute(
        "INSERT INTO feeds (source_id, url, kind, location_hint, category_hint, poll_minutes) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (url) DO NOTHING",
        (source_id, url, kind, location_hint, category_hint, poll_minutes),
    )


def load_sources():
    with open(SOURCES_FILE, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with get_connection() as conn:
        for site in config["sources"]:
            source_id = get_or_create_source(
                conn, site["name"], site["domain"], site.get("region_scope"), site.get("language", "en")
            )
            for feed in site["feeds"]:
                add_feed(conn, source_id, feed["url"],
                         location_hint=feed.get("location_hint"),
                         category_hint=feed.get("category_hint"))
            print(f"Loaded {site['name']} ({len(site['feeds'])} feeds)")

        google = config.get("google_news")
        if google:
            source_id = get_or_create_source(conn, "Google News", "news.google.com", "India")
            for place in google["places"]:
                add_feed(conn, source_id, search_url(place), kind="google_news",
                         location_hint=place, poll_minutes=google["poll_minutes"])
            print(f"Loaded Google News ({len(google['places'])} places)")


if __name__ == "__main__":
    load_sources()
