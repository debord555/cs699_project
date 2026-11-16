from datetime import datetime, timezone

import feedparser
import requests
from psycopg.rows import dict_row

from db import get_connection
from google_news import real_link
from load_sources import get_or_create_source
from normalize import clean_html, domain_of, is_junk, normalize_url, url_hash
from settings import MAX_FEED_FAILURES, REQUEST_TIMEOUT, USER_AGENT

GOOGLE_NEWS_LIMIT = 25

FEEDS_DUE_SQL = """
    SELECT feeds.id, feeds.url, feeds.kind, feeds.source_id,
           feeds.location_hint, feeds.category_hint,
           feeds.etag, feeds.last_modified, feeds.consecutive_failures
    FROM feeds
    JOIN sources ON sources.id = feeds.source_id
    WHERE feeds.is_active
      AND sources.is_active
      AND (feeds.last_polled_at IS NULL
           OR feeds.last_polled_at < now() - feeds.poll_minutes * interval '1 minute')
"""

SAVE_ARTICLE_SQL = """
    INSERT INTO articles (url, url_hash, source_id, feed_id, title, summary, author,
                          image_url, published_at, source_tags, location_hint, category_hint)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (url_hash) DO NOTHING
"""


def published_time(entry):
    t = entry.get("published_parsed")
    if t is None:
        return None
    return datetime(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec, tzinfo=timezone.utc)


def image_of(entry):
    for media in entry.get("media_content", []):
        if media.get("url"):
            return media["url"]
    return None


def tags_of(entry):
    tags = [tag.get("term") for tag in entry.get("tags", []) if tag.get("term")]
    return tags or None


def title_already_saved(conn, title):
    return conn.execute("SELECT 1 FROM articles WHERE title = %s", (title,)).fetchone() is not None


def save_article(conn, feed, entry):
    title = clean_html(entry.get("title"))
    link = entry.get("link")
    if not title or not link:
        return False

    source_id = feed["source_id"]

    if feed["kind"] == "google_news":
        publisher = entry.get("source", {})
        publisher_name = publisher.get("title")
        publisher_site = publisher.get("href")
        if not publisher_name or not publisher_site:
            return False
        title = title.removesuffix(" - " + publisher_name).strip()
        if title_already_saved(conn, title):
            return False
        link = real_link(link)
        if link is None:
            return False
        source_id = get_or_create_source(conn, publisher_name, domain_of(publisher_site))

    url = normalize_url(link)
    if is_junk(url, title):
        return False

    result = conn.execute(SAVE_ARTICLE_SQL, (
        url, url_hash(url), source_id, feed["id"], title,
        clean_html(entry.get("summary")), entry.get("author"), image_of(entry),
        published_time(entry), tags_of(entry),
        feed["location_hint"], feed["category_hint"],
    ))
    return result.rowcount == 1


def record_success(conn, feed, etag, last_modified):
    conn.execute(
        "UPDATE feeds SET last_polled_at = now(), consecutive_failures = 0, "
        "etag = %s, last_modified = %s WHERE id = %s",
        (etag, last_modified, feed["id"]),
    )


def record_failure(conn, feed):
    failures = feed["consecutive_failures"] + 1
    still_active = failures < MAX_FEED_FAILURES
    conn.execute(
        "UPDATE feeds SET last_polled_at = now(), consecutive_failures = %s, is_active = %s WHERE id = %s",
        (failures, still_active, feed["id"]),
    )


def download_feed(feed):
    headers = {"User-Agent": USER_AGENT}
    if feed["etag"]:
        headers["If-None-Match"] = feed["etag"]
    if feed["last_modified"]:
        headers["If-Modified-Since"] = feed["last_modified"]
    return requests.get(feed["url"], headers=headers, timeout=REQUEST_TIMEOUT)


def poll_feed(conn, feed):
    try:
        response = download_feed(feed)

        if response.status_code == 304:
            record_success(conn, feed, feed["etag"], feed["last_modified"])
            conn.commit()
            print(f"{feed['url']}: no change since last time")
            return

        response.raise_for_status()
        entries = feedparser.parse(response.content).entries
        if feed["kind"] == "google_news":
            entries = entries[:GOOGLE_NEWS_LIMIT]

        new_count = 0
        for entry in entries:
            if save_article(conn, feed, entry):
                new_count += 1

        record_success(conn, feed, response.headers.get("ETag"), response.headers.get("Last-Modified"))
        conn.commit()
        print(f"{feed['url']}: {new_count} new articles")
    except Exception as error:
        conn.rollback()
        record_failure(conn, feed)
        conn.commit()
        print(f"{feed['url']}: failed ({error})")


def poll_all_feeds():
    with get_connection() as conn:
        feeds = conn.cursor(row_factory=dict_row).execute(FEEDS_DUE_SQL).fetchall()
        print(f"{len(feeds)} feeds due")
        for feed in feeds:
            poll_feed(conn, feed)


if __name__ == "__main__":
    poll_all_feeds()
