# NewsRadar scraper

Collects Indian news from RSS feeds and Google News searches into PostgreSQL.

## Files

| File | Job |
| --- | --- |
| `sources.yaml` | The list of news websites, their RSS feeds, and Google News places |
| `load_sources.py` | Copies `sources.yaml` into the `sources` and `feeds` tables |
| `google_news.py` | Builds Google News search links and finds the real article link |
| `poller.py` | Reads the feeds that are due and saves new articles with status `new` |
| `extract.py` | Finds the dateline, wire agency, language and text fingerprint |
| `fetcher.py` | Downloads each new article's page politely and marks it `ready` |
| `run.py` | Runs the poller every 5 minutes and the fetcher every 2 minutes, side by side |
| `stats.py` | Prints a health report |

## Run on your PC

```
docker compose up -d db
python scraper/load_sources.py
python scraper/run.py
```

## Run everything in Docker

```
docker compose -f docker-compose.yml -f docker-compose.scraper.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.scraper.yml run --rm scraper python load_sources.py
```

## For the LLM step

Only take articles with `status = 'ready'`. Mark them `llm_processing` while working, then
`llm_done` or `llm_failed`. The `body` column is for internal processing only; the map shows only
the title, a short snippet and a link to the original site.
