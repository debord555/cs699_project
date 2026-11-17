from db import get_connection

REPORTS = {
    "Articles by status": """
        SELECT status, count(*) FROM articles GROUP BY status ORDER BY count(*) DESC
    """,
    "Articles per website (last 24 hours)": """
        SELECT s.name, count(*) FROM articles a JOIN sources s ON s.id = a.source_id
        WHERE a.scraped_at > now() - interval '24 hours'
        GROUP BY s.name ORDER BY count(*) DESC
    """,
    "Articles per location hint (last 7 days)": """
        SELECT coalesce(location_hint, '(none)'), count(*) FROM articles
        WHERE scraped_at > now() - interval '7 days'
        GROUP BY 1 ORDER BY count(*) DESC
    """,
    "Feeds that are failing": """
        SELECT url, consecutive_failures, is_active FROM feeds
        WHERE consecutive_failures > 0 ORDER BY consecutive_failures DESC
    """,
    "Most common download errors": """
        SELECT left(error, 80), count(*) FROM articles
        WHERE error IS NOT NULL GROUP BY 1 ORDER BY count(*) DESC LIMIT 10
    """,
}


def main():
    with get_connection() as conn:
        for title, sql in REPORTS.items():
            print(f"\n== {title} ==")
            rows = conn.execute(sql).fetchall()
            if not rows:
                print("  (nothing)")
            for row in rows:
                print("  " + " | ".join(str(value) for value in row))


if __name__ == "__main__":
    main()
