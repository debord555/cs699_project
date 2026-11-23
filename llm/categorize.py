"""Article category worker (CPU).

Loop:
  1. Pick a batch of uncategorized articles (category_status 'new', body present).
  2. Embed title + summary + start of body with a small sentence-embedding model.
  3. Compare each article with every category's example headlines
     (category_anchors.py) and keep the closest category, plus any other within
     CATEGORY_MARGIN of it. If even the closest is below CATEGORY_MIN_SCORE,
     link 'Other' instead.
  4. Mark the articles 'done' (or 'failed' on error).
  5. If there was nothing to process, sleep and try again.

Usage:  python categorize.py
"""

import time

import torch
from transformers import AutoModel, AutoTokenizer

from category_anchors import ANCHORS
from db import get_connection
from settings import (
    CATEGORIZE_IDLE_SECONDS,
    CATEGORY_BATCH_SIZE,
    CATEGORY_MARGIN,
    CATEGORY_MAX_LABELS,
    CATEGORY_MIN_SCORE,
    CATEGORY_MODEL,
    CATEGORY_TEXT_CHARS,
)

FALLBACK = "Other"

torch.set_grad_enabled(False)
tokenizer = AutoTokenizer.from_pretrained(CATEGORY_MODEL)
model = AutoModel.from_pretrained(CATEGORY_MODEL).eval()  # stays on the CPU


def embed(texts, max_tokens):
    """Return one unit-length vector per text (bge models use the [CLS] token)."""
    batch = tokenizer(texts, padding=True, truncation=True, max_length=max_tokens, return_tensors="pt")
    vectors = model(**batch).last_hidden_state[:, 0]
    return torch.nn.functional.normalize(vectors, dim=-1)


def load_categories(conn):
    """Return ({name: id} for every category, [names with examples], matrix of their vectors)."""
    ids = dict(conn.execute("SELECT name, id FROM categories").fetchall())
    missing = [name for name in ids if name != FALLBACK and name not in ANCHORS]
    if missing:
        print(f"No example headlines for {missing}; they will never be assigned")
    names = [name for name in ANCHORS if name in ids]
    centroids = torch.stack([embed(ANCHORS[name], 64).mean(dim=0) for name in names])
    return ids, names, torch.nn.functional.normalize(centroids, dim=-1)


def pick(scores, names):
    """Return [(name, score)] for one article's row of similarity scores, best first."""
    ranked = sorted(zip(names, scores.tolist()), key=lambda pair: pair[1], reverse=True)
    best = ranked[0][1]
    if best < CATEGORY_MIN_SCORE:
        return [(FALLBACK, None)]
    return [(name, score) for name, score in ranked[:CATEGORY_MAX_LABELS] if score >= best - CATEGORY_MARGIN]


def next_batch(conn):
    # SKIP LOCKED lets several workers run side by side without grabbing the same articles
    return conn.execute(
        "SELECT id, title, summary, body FROM articles "
        "WHERE category_status = 'new' AND body IS NOT NULL "
        "ORDER BY id LIMIT %s FOR UPDATE SKIP LOCKED",
        (CATEGORY_BATCH_SIZE,),
    ).fetchall()


def process_batch(conn, ids, names, centroids):
    """Process one batch. Returns False if there was nothing to do."""
    with conn.transaction():
        articles = next_batch(conn)
        if not articles:
            return False
        article_ids = [article[0] for article in articles]

        try:
            texts = [
                "\n".join(part for part in (title, summary, body[:CATEGORY_TEXT_CHARS]) if part)
                for _, title, summary, body in articles
            ]
            scores = embed(texts, 256) @ centroids.T
        except Exception as e:
            conn.execute(
                "UPDATE articles SET category_status = 'failed', error = %s WHERE id = ANY(%s)",
                (str(e)[:1000], article_ids),
            )
            print(f"Articles {article_ids[0]}-{article_ids[-1]}: failed ({e})")
            return True

        rows = []
        for article_id, row in zip(article_ids, scores):
            matches = pick(row, names)
            rows += [(article_id, ids[name], score) for name, score in matches]
            print(f"Article {article_id}: " + ", ".join(
                name if score is None else f"{name} ({score:.2f})" for name, score in matches
            ))

        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO article_category_map (article_id, category_id, score) "
                "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                rows,
            )
        conn.execute(
            "UPDATE articles SET category_status = 'done' WHERE id = ANY(%s)",
            (article_ids,),
        )
        return True


def main():
    with get_connection() as conn:
        ids, names, centroids = load_categories(conn)
        while True:
            if not process_batch(conn, ids, names, centroids):
                time.sleep(CATEGORIZE_IDLE_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
