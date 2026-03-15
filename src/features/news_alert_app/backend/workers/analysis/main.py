from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid

# Allow running this file directly: `python workers/analysis/main.py`
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.analysis import Analysis
from app.models.article import Article
from app.models.enums import ArticleStatus, TrustTier
from app.models.event_article import EventArticle
from app.models.event_cluster import EventCluster
from app.queue.constant import ANALYSIS_REQUESTS_QUEUE, ANALYSIS_RESULT_QUEUE
from app.queue.rabbitmq import consumer, publish
from app.services.event_analysis_llm import analyze_event_with_openai


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _resolve_event_id(db, payload: dict) -> uuid.UUID | None:
    event_id = _parse_uuid(payload.get("event_id"))
    if event_id:
        return event_id

    article_id = _parse_uuid(payload.get("article_id"))
    if not article_id:
        return None

    article = db.get(Article, article_id)
    if article and article.event_id:
        return article.event_id
    event_article_link = (
        db.query(EventArticle)
        .filter(EventArticle.article_id == article_id)
        .order_by(EventArticle.created_at.desc())
        .first()
    )
    if event_article_link:
        return event_article_link.event_id
    if article:
        return _bootstrap_event_for_article(db, article)
    return None


def _bootstrap_event_for_article(db, article: Article) -> uuid.UUID:
    anchor_ts = (
        article.published_at
        or article.fetched_at
        or article.created_at
        or datetime.now(timezone.utc)
    )
    title = (article.title or article.summary_hint or "Untitled event").strip()
    if not title:
        title = "Untitled event"

    trusted_source_count = 0
    if article.source and article.source.trust_tier in {TrustTier.HIGH, TrustTier.VERIFIED}:
        trusted_source_count = 1

    event = EventCluster(
        canonical_title=title,
        topic=article.topic_hint,
        region=article.region_hint,
        first_seen_at=anchor_ts,
        last_seen_at=anchor_ts,
        source_count=1,
        trusted_source_count=trusted_source_count,
    )
    db.add(event)
    db.flush()

    article.event_id = event.id
    db.add(
        EventArticle(
            event_id=event.id,
            article_id=article.id,
        )
    )
    db.commit()
    print(f"[analysis] bootstrapped event={event.id} from article={article.id}")
    return event.id


def _collect_event_articles(event: EventCluster) -> list[Article]:
    merged: dict[uuid.UUID, Article] = {}

    for article in event.articles:
        merged[article.id] = article

    for event_link in event.event_articles:
        if event_link.article:
            merged[event_link.article.id] = event_link.article

    def _sort_key(article: Article):
        return article.published_at or article.fetched_at or article.created_at or datetime.min

    return sorted(merged.values(), key=_sort_key, reverse=True)


def _create_analysis(db, event: EventCluster, payload: dict) -> Analysis:
    analysis = Analysis(
        event_id=event.id,
        model_name=payload.get("model_name") or "unknown",
        model_version=payload.get("model_version"),
        topic=payload.get("topic"),
        region=payload.get("region"),
        severity_score=float(payload.get("severity_score") or 0.4),
        confidence_score=float(payload.get("confidence_score") or 0.5),
        summary=(payload.get("summary") or "No summary produced.")[:3000],
        reasoning_brief=payload.get("reasoning_brief"),
        key_entities=payload.get("key_entities"),
        risk_labels=payload.get("risk_labels"),
        evidence=payload.get("evidence"),
        raw_response=payload.get("raw_response"),
    )
    db.add(analysis)
    db.flush()
    return analysis


def _update_event_from_analysis(event: EventCluster, analysis: Analysis):
    event.latest_summary = analysis.summary
    event.latest_severity_score = analysis.severity_score
    event.latest_confidence_score = analysis.confidence_score
    if analysis.topic:
        event.topic = analysis.topic
    if analysis.region:
        event.region = analysis.region


def _mark_articles_analyzed(articles: list[Article]):
    for article in articles:
        if article.status != ArticleStatus.REJECTED:
            article.status = ArticleStatus.ANALYZED


def _normalize_legacy_score(value) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric > 1.0 and numeric <= 10.0:
        numeric = numeric / 10.0
    elif numeric > 10.0 and numeric <= 100.0:
        numeric = numeric / 100.0
    return max(0.0, min(1.0, round(numeric, 4)))


def _extract_raw_scales(raw_response: dict | None) -> tuple[float | None, float | None]:
    if not isinstance(raw_response, dict):
        return None, None

    choices = raw_response.get("choices")
    if not isinstance(choices, list) or not choices:
        return None, None
    first = choices[0]
    if not isinstance(first, dict):
        return None, None
    message = first.get("message")
    if not isinstance(message, dict):
        return None, None
    content = message.get("content")
    if not isinstance(content, str):
        return None, None

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None, None

    try:
        parsed = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return None, None
    if not isinstance(parsed, dict):
        return None, None

    return (
        _normalize_legacy_score(parsed.get("severity_score")),
        _normalize_legacy_score(parsed.get("confidence_score")),
    )


def repair_legacy_analysis_scores(limit: int):
    db = SessionLocal()
    try:
        query = db.query(Analysis).order_by(Analysis.created_at.asc())
        if limit > 0:
            query = query.limit(limit)
        analyses = query.all()

        updated_rows = 0
        touched_event_ids: set[uuid.UUID] = set()

        for analysis in analyses:
            raw_severity, raw_confidence = _extract_raw_scales(analysis.raw_response)
            changed = False

            if raw_severity is not None and abs((analysis.severity_score or 0.0) - raw_severity) > 1e-6:
                analysis.severity_score = raw_severity
                changed = True
            if raw_confidence is not None and abs((analysis.confidence_score or 0.0) - raw_confidence) > 1e-6:
                analysis.confidence_score = raw_confidence
                changed = True

            if changed:
                updated_rows += 1
                touched_event_ids.add(analysis.event_id)

        for event_id in touched_event_ids:
            event = db.get(EventCluster, event_id)
            if not event:
                continue
            latest = (
                db.query(Analysis)
                .filter(Analysis.event_id == event_id)
                .order_by(Analysis.created_at.desc())
                .first()
            )
            if not latest:
                continue
            event.latest_severity_score = latest.severity_score
            event.latest_confidence_score = latest.confidence_score
            event.latest_summary = latest.summary

        db.commit()
        print(
            f"[analysis] repaired legacy score scale in analyses={updated_rows}, "
            f"events_refreshed={len(touched_event_ids)}"
        )
    except Exception as exc:
        db.rollback()
        print(f"[analysis] repair failed: {exc}")
        raise
    finally:
        db.close()


def analyze_event(event_id: uuid.UUID, publish_next: bool = True) -> str:
    db = SessionLocal()
    try:
        event = db.get(EventCluster, event_id)
        if not event:
            print(f"[analysis] event not found: {event_id}")
            return "missing"

        articles = _collect_event_articles(event)
        if not articles:
            print(f"[analysis] no articles linked to event: {event_id}")
            return "no_articles"

        payload = analyze_event_with_openai(event, articles)
        analysis = _create_analysis(db, event, payload)
        _update_event_from_analysis(event, analysis)
        _mark_articles_analyzed(articles)
        db.commit()

        if publish_next:
            try:
                publish(
                    ANALYSIS_RESULT_QUEUE,
                    {"analysis_id": str(analysis.id), "event_id": str(event.id)},
                )
            except Exception as exc:
                print(f"[analysis] warning: publish failed for analysis={analysis.id}: {exc}")

        print(
            f"[analysis] created analysis={analysis.id} event={event.id} "
            f"severity={analysis.severity_score} confidence={analysis.confidence_score}"
        )
        return "ok"
    except Exception as exc:
        db.rollback()
        print(f"[analysis] failed for event={event_id}: {exc}")
        raise
    finally:
        db.close()


def handle_analysis_request(payload: dict):
    db = SessionLocal()
    try:
        event_id = _resolve_event_id(db, payload)
    finally:
        db.close()

    if not event_id:
        print(f"[analysis] payload missing resolvable event_id: {payload}")
        return

    analyze_event(event_id, publish_next=True)


def run_consumer():
    print(f"[analysis] consuming from {ANALYSIS_REQUESTS_QUEUE}")
    consumer(ANALYSIS_REQUESTS_QUEUE, handle_analysis_request)


def run_drain(limit: int | None = None):
    print(f"[analysis] draining {ANALYSIS_REQUESTS_QUEUE} until idle")
    consumer(
        ANALYSIS_REQUESTS_QUEUE,
        handle_analysis_request,
        stop_when_idle=True,
        inactivity_timeout=3.0,
        max_messages=limit,
    )


def run_backfill(limit: int):
    db = SessionLocal()
    try:
        events = (
            db.query(EventCluster)
            .order_by(EventCluster.last_seen_at.desc())
            .limit(limit)
            .all()
        )
        event_ids = [event.id for event in events]
    finally:
        db.close()

    print(f"[analysis] backfill candidates={len(event_ids)}")
    results = {"ok": 0, "missing": 0, "no_articles": 0}
    for event_id in event_ids:
        status = analyze_event(event_id, publish_next=True)
        if status in results:
            results[status] += 1
    print(f"[analysis] backfill completed {results}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze events and produce Analysis rows.")
    parser.add_argument(
        "--repair-legacy-scores",
        action="store_true",
        help="Fix previously stored analysis scores that used 1..10 or 1..100 scales.",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Analyze recent events from DB instead of consuming queue.",
    )
    parser.add_argument(
        "--drain",
        action="store_true",
        help="Consume current queue items and exit when queue is idle.",
    )
    parser.add_argument(
        "--drain-limit",
        type=int,
        default=0,
        help="Optional max messages in drain mode (0 = no limit).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of events in backfill mode.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.repair_legacy_scores:
        repair_legacy_analysis_scores(limit=args.limit)
    elif args.backfill:
        run_backfill(limit=args.limit)
    elif args.drain:
        run_drain(limit=(args.drain_limit if args.drain_limit > 0 else None))
    else:
        run_consumer()


if __name__ == "__main__":
    main()
