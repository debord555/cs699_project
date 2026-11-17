import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from fetcher import fetch_new_articles
from poller import poll_all_feeds


def main():
    logging.getLogger("apscheduler").setLevel(logging.ERROR)
    scheduler = BlockingScheduler()
    scheduler.add_job(poll_all_feeds, "interval", minutes=5, next_run_time=datetime.now())
    scheduler.add_job(fetch_new_articles, "interval", minutes=2, next_run_time=datetime.now())
    print("Scraper started. Press Ctrl+C to stop.")
    scheduler.start()


if __name__ == "__main__":
    main()
