import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

# Allow running this file directly: `python workers/ingest/main.py`
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.enums import SourceType
from app.queue.constant import RAW_NEWS_QUEUE
from app.queue.rabbitmq import publish
from app.repos.article_repo import (create_article,
                                    get_article_by_source_external_id)
from app.repos.source_repo import list_active_sources
from app.services.newsapi_client import fetch_newsapi_everything

NEWSAPI_QUERY_PRIMARY = (
    "(ukraine OR russia OR israel OR gaza OR Iran OR taiwan OR nato "
    'OR sanctions OR missile OR ceasefire OR "red sea")'
)
NEWSAPI_QUERY_FALLBACK = "(geopolitics OR conflict OR diplomacy OR military OR war)"

def ingest_rss_source(db, source):
    feed = feedparser.parse(source.rss_url)
    entries = getattr(feed, "entries", [])
    if getattr(feed, "bozo", False):
        print(f"[ingest][rss][{source.slug}] parse warning: {getattr(feed, 'bozo_exception', 'unknown')}")
    print(f"[ingest][rss][{source.slug}] fetched {len(entries)} entries")

    inserted = 0
    for entry in entries:
        external_id = getattr(entry, "id", None) or getattr(entry, "link", None)
        if not external_id:
            print(f"Skipping entry without ID or link: {entry}")
            continue

        existing = get_article_by_source_external_id(db, source.id, external_id)
        if existing:
            print(f"Article already exists: {external_id}")
            continue

        article = create_article(
            db=db,
            source_id=source.id,
            external_id=external_id,
            url=getattr(entry, "link", None) or external_id,
            title=getattr(entry, "title", None),
            body=getattr(entry, "summary", None),
            fetched_at=datetime.now(timezone.utc),
        )
        db.commit()
        publish(RAW_NEWS_QUEUE, {"article_id": str(article.id)})
        inserted += 1

    print(f"[ingest][rss][{source.slug}] inserted {inserted} new articles")


def ingest_newsapi_source(db, source):
    from_dt = datetime.now(timezone.utc) - timedelta(hours=24)
    data = fetch_newsapi_everything(
        query=NEWSAPI_QUERY_PRIMARY,
        from_dt=from_dt,
        language="en",
        search_in="title,description",
        sort_by="publishedAt",
        page_size=100,
        page=1,
    )

    if not data.get("articles"):
        fallback_from_dt = datetime.now(timezone.utc) - timedelta(hours=72)
        print("[ingest][api] primary query returned 0 results, trying fallback query")
        data = fetch_newsapi_everything(
            query=NEWSAPI_QUERY_FALLBACK,
            from_dt=fallback_from_dt,
            language="en",
            search_in="title,description",
            sort_by="publishedAt",
            page_size=100,
            page=1,
        )

    items = data.get("articles", [])
    print(
        f"[ingest][api][{source.slug}] fetched {len(items)} articles "
        f"(totalResults={data.get('totalResults')})"
    )

    inserted = 0
    for item in items:
        external_id = item.get("url")
        if not external_id:
            print(f"Skipping article without URL: {item}")
            continue

        existing = get_article_by_source_external_id(db, source.id, external_id)
        if existing:
            print(f"Article already exists: {external_id}")
            continue

        body = item.get("content") or item.get("description")
        article = create_article(
            db=db,
            source_id=source.id,
            external_id=external_id,
            url=item.get("url", ""),
            title=item.get("title"),
            body=body,
            summary_hint=item.get("description"),
            author=item.get("author"),
            fetched_at=datetime.now(timezone.utc),
        )
        db.commit()
        publish(RAW_NEWS_QUEUE, {"article_id": str(article.id)})
        inserted += 1

    print(f"[ingest][api][{source.slug}] inserted {inserted} new articles")


import argparse
import time

INGEST_INTERVAL_SECONDS = 300  # 5 minutes between cycles


def run():
    db = SessionLocal()
    try:
        sources = list_active_sources(db)
        print(f"[ingest] active sources: {len(sources)}")
        for source in sources:
            print(f"[ingest] source={source.slug} type={source.source_type}")
            try:
                if source.source_type == SourceType.RSS and source.rss_url:
                    ingest_rss_source(db, source)
                elif source.source_type == SourceType.API and source.slug == "newsapi-everything":
                    ingest_newsapi_source(db, source)
            except Exception as e:
                print(f"[ingest] error processing source={source.slug}: {e}")
    finally:
        db.close()


def run_loop():
    print(f"[ingest] starting ingest loop (interval={INGEST_INTERVAL_SECONDS}s)")
    while True:
        try:
            run()
        except Exception as e:
            print(f"[ingest] cycle error: {e}")
        print(f"[ingest] sleeping {INGEST_INTERVAL_SECONDS}s until next cycle...")
        time.sleep(INGEST_INTERVAL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    args = parser.parse_args()
    if args.once:
        run()
    else:
        run_loop()
