import time
from urllib import robotparser
from urllib.parse import urlsplit

import requests
import trafilatura
from psycopg.rows import dict_row

from db import get_connection
from extract import content_hash, detect_language, find_dateline, find_wire_agency
from settings import (DOMAIN_DELAY_SECONDS, FETCH_BATCH_SIZE, MAX_FETCH_ATTEMPTS,
                      REQUEST_TIMEOUT, USER_AGENT)

robots_rules = {}
last_visit = {}

NEW_ARTICLES_SQL = """
    SELECT id, url, title, author, image_url, fetch_attempts
    FROM articles
    WHERE status = 'new'
    ORDER BY id DESC
    LIMIT %s
"""


def website_of(url):
    parts = urlsplit(url)
    return parts.scheme + "://" + parts.netloc


def robots_allows(url):
    site = website_of(url)
    if site not in robots_rules:
        rules = robotparser.RobotFileParser()
        response = requests.get(site + "/robots.txt", headers={"User-Agent": USER_AGENT},
                                timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            rules.parse(response.text.splitlines())
        elif response.status_code in (401, 403):
            rules.disallow_all = True
        else:
            rules.allow_all = True
        robots_rules[site] = rules
    return robots_rules[site].can_fetch(USER_AGENT, url)


def wait_politely(url):
    site = website_of(url)
    if site in last_visit:
        seconds_since_last_visit = time.time() - last_visit[site]
        if seconds_since_last_visit < DOMAIN_DELAY_SECONDS:
            time.sleep(DOMAIN_DELAY_SECONDS - seconds_since_last_visit)
    last_visit[site] = time.time()


def download_page(url):
    wait_politely(url)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    page = trafilatura.bare_extraction(response.text, url=url, with_metadata=True)
    if page is None:
        raise ValueError("no article text found on the page")
    return page.as_dict()


def save_success(conn, article, page):
    text = page.get("text")
    author = article["author"] or page.get("author")
    image_url = article["image_url"] or page.get("image")
    conn.execute(
        """
        UPDATE articles
        SET body = %s, dateline = %s, author = %s, image_url = %s, language = %s,
            content_hash = %s, is_wire = %s, status = 'ready', error = NULL
        WHERE id = %s
        """,
        (text, find_dateline(text), author, image_url,
         detect_language(article["title"], text), content_hash(text),
         find_wire_agency(author, text) is not None, article["id"]),
    )


def save_failure(conn, article, error, give_up_now=False):
    attempts = article["fetch_attempts"] + 1
    if give_up_now or attempts >= MAX_FETCH_ATTEMPTS:
        new_status = "ready"
    else:
        new_status = "new"
    conn.execute(
        "UPDATE articles SET fetch_attempts = %s, error = %s, status = %s WHERE id = %s",
        (attempts, str(error)[:500], new_status, article["id"]),
    )


def fetch_new_articles():
    with get_connection() as conn:
        articles = conn.cursor(row_factory=dict_row).execute(NEW_ARTICLES_SQL, (FETCH_BATCH_SIZE,)).fetchall()
        print(f"{len(articles)} articles to fetch")

        for article in articles:
            try:
                if robots_allows(article["url"]):
                    page = download_page(article["url"])
                    save_success(conn, article, page)
                else:
                    save_failure(conn, article, "blocked by robots.txt", give_up_now=True)
            except Exception as error:
                conn.rollback()
                save_failure(conn, article, error)
            conn.commit()


if __name__ == "__main__":
    fetch_new_articles()
