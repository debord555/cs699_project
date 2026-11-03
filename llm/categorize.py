"""Article category worker.

Loop:
  1. Pick one uncategorized article (category_status 'new', body present).
  2. Score its title + summary + start of body against every category with a
     zero-shot NLI model (runs on the GPU when there is one).
  3. Link every category scoring at least CATEGORY_THRESHOLD in
     `article_category_map`; if none does, link 'Other'.
  4. Mark the article 'done' (or 'failed' on error).
  5. If there was nothing to process, sleep and try again.

Usage:  python categorize.py
"""

import time

import torch
from transformers import pipeline

from db import get_connection
from settings import (
    CATEGORIZE_IDLE_SECONDS,
    CATEGORY_MODEL,
    CATEGORY_TEXT_CHARS,
    CATEGORY_THRESHOLD,
    GPU_MEMORY_GB,
)

FALLBACK = "Other"

if torch.cuda.is_available():
    total_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    torch.cuda.set_per_process_memory_fraction(min(1.0, GPU_MEMORY_GB / total_gb))
    classifier = pipeline("zero-shot-classification", model=CATEGORY_MODEL, device=0, dtype=torch.float16)
else:
    print("No CUDA GPU found, running on CPU (slow)")
    classifier = pipeline("zero-shot-classification", model=CATEGORY_MODEL)


def load_categories(conn):
    """Return {name: id} for every row in `categories`."""
    return dict(conn.execute("SELECT name, id FROM categories").fetchall())


def classify(title, summary, body, labels):
    """Return [(label, score)] for labels scoring at least the threshold, best first."""
    text = "\n".join(part for part in (title, summary, (body or "")[:CATEGORY_TEXT_CHARS]) if part)
    result = classifier(
        text,
        candidate_labels=labels,
        hypothesis_template="This news article is about {}.",
        multi_label=True,
    )
    return [
        (label, score)
        for label, score in zip(result["labels"], result["scores"])
        if score >= CATEGORY_THRESHOLD
    ]


def next_article(conn):
    # SKIP LOCKED lets several workers run side by side without grabbing the same article
    return conn.execute(
        "SELECT id, title, summary, body FROM articles "
        "WHERE category_status = 'new' AND body IS NOT NULL "
        "ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED"
    ).fetchone()


def process_one(conn, categories):
    """Process one article. Returns False if there was nothing to do."""
    with conn.transaction():
        article = next_article(conn)
        if article is None:
            return False
        article_id, title, summary, body = article

        try:
            labels = [name for name in categories if name != FALLBACK]
            matches = classify(title, summary, body, labels)
        except Exception as e:
            conn.execute(
                "UPDATE articles SET category_status = 'failed', error = %s WHERE id = %s",
                (str(e)[:1000], article_id),
            )
            print(f"Article {article_id}: failed ({e})")
            return True

        if not matches:
            matches = [(FALLBACK, None)]

        for name, score in matches:
            conn.execute(
                "INSERT INTO article_category_map (article_id, category_id, score) "
                "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (article_id, categories[name], score),
            )

        conn.execute(
            "UPDATE articles SET category_status = 'done' WHERE id = %s",
            (article_id,),
        )
        print(f"Article {article_id}: " + ", ".join(
            name if score is None else f"{name} ({score:.2f})" for name, score in matches
        ))
        return True


def main():
    with get_connection() as conn:
        categories = load_categories(conn)
        while True:
            if not process_one(conn, categories):
                time.sleep(CATEGORIZE_IDLE_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
