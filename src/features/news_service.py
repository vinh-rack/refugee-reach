"""
News service — queries the news_alert_app database for latest events and articles.

This module connects directly to the same Postgres database used by the
news_alert_app pipeline, providing read-only access to processed news data
for the main RefugeeReach API and agents.
"""

import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


@dataclass
class NewsArticle:
    id: str
    title: Optional[str]
    url: str
    source_name: Optional[str]
    published_at: Optional[str]
    summary_hint: Optional[str]


@dataclass
class NewsEvent:
    id: str
    canonical_title: str
    topic: Optional[str]
    region: Optional[str]
    status: Optional[str]
    severity_score: Optional[float]
    confidence_score: Optional[float]
    summary: Optional[str]
    article_count: int
    first_seen_at: Optional[str]
    last_seen_at: Optional[str]
    articles: List[NewsArticle]


def _get_engine():
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set — cannot connect to news database")
    return create_engine(url, future=True, pool_pre_ping=True)


def _get_session():
    engine = _get_engine()
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    return Session()


def get_latest_events(
    limit: int = 20,
    topic: Optional[str] = None,
    region: Optional[str] = None,
    min_severity: Optional[float] = None,
) -> List[NewsEvent]:
    """
    Fetch the latest news event clusters from the database.

    Args:
        limit: Max number of events to return.
        topic: Filter by topic (e.g. "Conflict", "Diplomacy").
        region: Filter by region (e.g. "Middle East", "Eastern Europe").
        min_severity: Only return events with severity >= this value.

    Returns:
        List of NewsEvent dataclasses with nested articles.
    """
    db = _get_session()
    try:
        params = {"limit": limit}
        where_clauses = []

        if topic:
            where_clauses.append("ec.topic ILIKE :topic")
            params["topic"] = f"%{topic}%"
        if region:
            where_clauses.append("ec.region ILIKE :region")
            params["region"] = f"%{region}%"
        if min_severity is not None:
            where_clauses.append("ec.latest_severity_score >= :min_severity")
            params["min_severity"] = min_severity

        where_sql = (" AND " + " AND ".join(where_clauses)) if where_clauses else ""

        events_query = text(f"""
            SELECT ec.id, ec.canonical_title, ec.topic, ec.region, ec.status,
                   ec.latest_severity_score, ec.latest_confidence_score,
                   ec.latest_summary, ec.source_count,
                   ec.first_seen_at, ec.last_seen_at
            FROM event_clusters ec
            WHERE 1=1 {where_sql}
            ORDER BY ec.last_seen_at DESC
            LIMIT :limit
        """)

        rows = db.execute(events_query, params).fetchall()
        events = []

        for row in rows:
            event_id = str(row[0])
            articles_query = text("""
                SELECT a.id, a.title, a.url, s.name, a.published_at, a.summary_hint
                FROM articles a
                LEFT JOIN sources s ON a.source_id = s.id
                WHERE a.event_id = :event_id
                ORDER BY a.published_at DESC NULLS LAST
                LIMIT 10
            """)
            art_rows = db.execute(articles_query, {"event_id": event_id}).fetchall()

            articles = [
                NewsArticle(
                    id=str(ar[0]),
                    title=ar[1],
                    url=ar[2],
                    source_name=ar[3],
                    published_at=ar[4].isoformat() if ar[4] else None,
                    summary_hint=ar[5],
                )
                for ar in art_rows
            ]

            events.append(NewsEvent(
                id=event_id,
                canonical_title=row[1],
                topic=row[2],
                region=row[3],
                status=row[4],
                severity_score=row[5],
                confidence_score=row[6],
                summary=row[7],
                article_count=row[8] or len(articles),
                first_seen_at=row[9].isoformat() if row[9] else None,
                last_seen_at=row[10].isoformat() if row[10] else None,
                articles=articles,
            ))

        return events
    finally:
        db.close()

def get_filter_options() -> dict:
    """Return distinct topics and regions from event_clusters."""
    db = _get_session()
    try:
        topics = [
            r[0] for r in db.execute(
                text("SELECT DISTINCT topic FROM event_clusters WHERE topic IS NOT NULL ORDER BY topic")
            ).fetchall()
        ]
        regions = [
            r[0] for r in db.execute(
                text("SELECT DISTINCT region FROM event_clusters WHERE region IS NOT NULL ORDER BY region")
            ).fetchall()
        ]
        return {"topics": topics, "regions": regions}
    finally:
        db.close()



def get_event_by_id(event_id: str) -> Optional[NewsEvent]:
    """Fetch a single event by ID with its articles."""
    events = get_latest_events(limit=1)
    db = _get_session()
    try:
        row = db.execute(text("""
            SELECT ec.id, ec.canonical_title, ec.topic, ec.region, ec.status,
                   ec.latest_severity_score, ec.latest_confidence_score,
                   ec.latest_summary, ec.source_count,
                   ec.first_seen_at, ec.last_seen_at
            FROM event_clusters ec
            WHERE ec.id = :event_id
        """), {"event_id": event_id}).fetchone()

        if not row:
            return None

        art_rows = db.execute(text("""
            SELECT a.id, a.title, a.url, s.name, a.published_at, a.summary_hint
            FROM articles a
            LEFT JOIN sources s ON a.source_id = s.id
            WHERE a.event_id = :event_id
            ORDER BY a.published_at DESC NULLS LAST
        """), {"event_id": event_id}).fetchall()

        articles = [
            NewsArticle(
                id=str(ar[0]),
                title=ar[1],
                url=ar[2],
                source_name=ar[3],
                published_at=ar[4].isoformat() if ar[4] else None,
                summary_hint=ar[5],
            )
            for ar in art_rows
        ]

        return NewsEvent(
            id=str(row[0]),
            canonical_title=row[1],
            topic=row[2],
            region=row[3],
            status=row[4],
            severity_score=row[5],
            confidence_score=row[6],
            summary=row[7],
            article_count=row[8] or len(articles),
            first_seen_at=row[9].isoformat() if row[9] else None,
            last_seen_at=row[10].isoformat() if row[10] else None,
            articles=articles,
        )
    finally:
        db.close()


def news_event_to_dict(event: NewsEvent) -> dict:
    """Convert a NewsEvent to a serializable dict."""
    return asdict(event)
