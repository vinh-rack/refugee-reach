from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import sys
import uuid

# Allow running this file directly: `python workers/deduplicate/main.py`
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.models.article import Article
from app.models.enums import ArticleStatus, EventStatus, TrustTier
from app.models.event_article import EventArticle
from app.models.event_cluster import EventCluster
from app.queue.constant import ANALYSIS_REQUESTS_QUEUE, NORMALIZED_NEWS_QUEUE
from app.queue.rabbitmq import consumer, publish
from app.repos.article_repo import (
    find_duplicate_by_normalized_hash,
    find_duplicate_by_url,
    list_articles_by_status,
)
from app.services.semantic_similarity import semantic_similarity_scores

try:
    from rapidfuzz import fuzz  # type: ignore
except Exception:  # pragma: no cover - fallback if rapidfuzz missing
    fuzz = None


TITLE_WS_RE = re.compile(r"\s+")
RECENT_WINDOW_HOURS = 48
SEMANTIC_MATCH_THRESHOLD = 0.70
LEXICAL_MATCH_THRESHOLD = 72.0


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    text = TITLE_WS_RE.sub(" ", value).strip().lower()
    return text


def title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if fuzz:
        return float(fuzz.token_set_ratio(a, b))
    # Fallback approximation without external library.
    a_tokens = set(a.split())
    b_tokens = set(b.split())
    if not a_tokens or not b_tokens:
        return 0.0
    overlap = len(a_tokens.intersection(b_tokens))
    union = len(a_tokens.union(b_tokens))
    return round((overlap / union) * 100.0, 2)


def article_anchor_time(article: Article) -> datetime:
    return (
        article.published_at
        or article.fetched_at
        or article.created_at
        or datetime.now(timezone.utc)
    )


def build_article_title(article: Article) -> str:
    return normalize_title(article.title or article.summary_hint or "")


def build_article_semantic_text(article: Article) -> str:
    title = (article.title or article.summary_hint or "").strip()
    body = (article.body or article.summary_hint or "").strip()
    return f"title: {title}\nbody: {body[:2000]}"


def build_event_semantic_text(event: EventCluster) -> str:
    return (
        f"title: {(event.canonical_title or '').strip()}\n"
        f"summary: {(event.latest_summary or '').strip()[:2000]}\n"
        f"topic: {(event.topic or '').strip()}\n"
        f"region: {(event.region or '').strip()}"
    )


def mark_duplicate(article: Article, canonical_article: Article, reason: str):
    metadata = dict(article.extra_metadata or {})
    metadata["dedupe"] = {
        "is_duplicate": True,
        "duplicate_reason": reason,
        "canonical_article_id": str(canonical_article.id),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    article.extra_metadata = metadata
    article.status = ArticleStatus.REJECTED


def mark_unique(article: Article):
    metadata = dict(article.extra_metadata or {})
    metadata["dedupe"] = {
        "is_duplicate": False,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    article.extra_metadata = metadata


def match_existing_event(db, article: Article) -> tuple[EventCluster | None, float, str]:
    title = build_article_title(article)
    if not title:
        return None, 0.0, "none"

    anchor = article_anchor_time(article)
    min_time = anchor - timedelta(hours=RECENT_WINDOW_HOURS)

    candidates = (
        db.query(EventCluster)
        .filter(
            EventCluster.last_seen_at >= min_time,
            EventCluster.status.in_([EventStatus.ACTIVE, EventStatus.MONITORING]),
        )
        .order_by(EventCluster.last_seen_at.desc())
        .limit(200)
        .all()
    )
    if not candidates:
        return None, 0.0, "none"

    article_text = build_article_semantic_text(article)
    candidate_texts = [build_event_semantic_text(event) for event in candidates]
    semantic_scores = semantic_similarity_scores(article_text, candidate_texts)

    best_match: EventCluster | None = None
    best_score = 0.0
    mode = "lexical"
    for idx, event in enumerate(candidates):
        event_title = normalize_title(event.canonical_title)
        if not event_title:
            continue
        lexical_score = title_similarity(title, event_title) / 100.0
        semantic_score = None
        if semantic_scores is not None:
            semantic_score = semantic_scores[idx]

        if semantic_score is None:
            score = lexical_score
        else:
            score = (semantic_score * 0.75) + (lexical_score * 0.25)
            mode = "semantic+lexical"

        # small boost when hints align
        if article.topic_hint and event.topic and article.topic_hint == event.topic:
            score += 0.03
        if article.region_hint and event.region and article.region_hint == event.region:
            score += 0.03

        if score > best_score:
            best_score = score
            best_match = event

    threshold = SEMANTIC_MATCH_THRESHOLD if semantic_scores is not None else (LEXICAL_MATCH_THRESHOLD / 100.0)
    if best_match and best_score >= threshold:
        return best_match, best_score, mode
    return None, best_score, mode


def create_event_from_article(db, article: Article) -> EventCluster:
    anchor = article_anchor_time(article)
    title = (article.title or article.summary_hint or "Untitled event").strip() or "Untitled event"

    event = EventCluster(
        canonical_title=title,
        topic=article.topic_hint,
        region=article.region_hint,
        status=EventStatus.ACTIVE,
        first_seen_at=anchor,
        last_seen_at=anchor,
        source_count=0,
        trusted_source_count=0,
    )
    db.add(event)
    db.flush()
    return event


def upsert_event_article_link(db, event_id: uuid.UUID, article_id: uuid.UUID):
    existing = (
        db.query(EventArticle)
        .filter(
            EventArticle.event_id == event_id,
            EventArticle.article_id == article_id,
        )
        .first()
    )
    if not existing:
        db.add(EventArticle(event_id=event_id, article_id=article_id))


def update_event_rollups(db, event: EventCluster, article: Article):
    anchor = article_anchor_time(article)
    if anchor < event.first_seen_at:
        event.first_seen_at = anchor
    if anchor > event.last_seen_at:
        event.last_seen_at = anchor

    existing_same_source = (
        db.query(Article.id)
        .filter(
            Article.event_id == event.id,
            Article.source_id == article.source_id,
            Article.id != article.id,
            Article.status != ArticleStatus.REJECTED,
        )
        .first()
    )
    if not existing_same_source:
        event.source_count = max(0, event.source_count or 0) + 1
        if article.source and article.source.trust_tier in {TrustTier.HIGH, TrustTier.VERIFIED}:
            event.trusted_source_count = max(0, event.trusted_source_count or 0) + 1


def assign_article_to_event(
    db,
    article: Article,
    event: EventCluster,
    *,
    status_on_assign: ArticleStatus = ArticleStatus.CLUSTERED,
    update_rollups_flag: bool = True,
):
    upsert_event_article_link(db, event.id, article.id)
    article.event_id = event.id
    article.status = status_on_assign
    if update_rollups_flag:
        update_event_rollups(db, event, article)


def deduplicate_and_cluster_article(article_id: str, publish_next: bool = True) -> str:
    try:
        parsed_article_id = uuid.UUID(article_id)
    except ValueError:
        print(f"[dedupe] invalid article_id: {article_id}")
        return "invalid"

    db = SessionLocal()
    try:
        article = (
            db.query(Article)
            .options(joinedload(Article.source))
            .filter(Article.id == parsed_article_id)
            .first()
        )
        if not article:
            print(f"[dedupe] article not found: {article_id}")
            return "missing"

        if article.status != ArticleStatus.NORMALIZED:
            print(f"[dedupe] skipping {article_id}, status={article.status}")
            return "skipped"

        duplicate = find_duplicate_by_normalized_hash(
            db,
            normalized_hash=article.normalized_hash,
            exclude_article_id=article.id,
        )
        duplicate_reason = "normalized_hash" if duplicate else ""

        if not duplicate:
            duplicate = find_duplicate_by_url(
                db,
                url=article.url,
                exclude_article_id=article.id,
            )
            if duplicate:
                duplicate_reason = "canonical_url"

        if duplicate:
            mark_duplicate(article, duplicate, duplicate_reason)
            if duplicate.event_id:
                assign_article_to_event(
                    db,
                    article,
                    duplicate.event,
                    status_on_assign=ArticleStatus.REJECTED,
                    update_rollups_flag=False,
                )
            db.commit()
            print(
                f"[dedupe] rejected duplicate article={article.id} "
                f"canonical={duplicate.id} reason={duplicate_reason}"
            )
            return "duplicate"

        mark_unique(article)
        matched_event, match_score, match_mode = match_existing_event(db, article)
        if matched_event:
            assign_article_to_event(db, article, matched_event)
            event = matched_event
            event_action = f"matched ({match_mode} score={match_score:.3f})"
        else:
            event = create_event_from_article(db, article)
            assign_article_to_event(db, article, event)
            event_action = "created"

        db.commit()

        if publish_next:
            try:
                publish(
                    ANALYSIS_REQUESTS_QUEUE,
                    {"event_id": str(event.id), "article_id": str(article.id)},
                )
            except Exception as exc:
                print(f"[dedupe] warning: publish failed for event={event.id}: {exc}")

        print(
            f"[dedupe] clustered article={article.id} event={event.id} action={event_action}"
        )
        return "clustered"
    except Exception as exc:
        db.rollback()
        print(f"[dedupe] failed for article_id={article_id}: {exc}")
        raise
    finally:
        db.close()


def resolve_canonical_with_event(db, article: Article) -> Article | None:
    current = article
    seen: set[uuid.UUID] = set()

    for _ in range(10):
        metadata = dict(current.extra_metadata or {})
        dedupe = metadata.get("dedupe")
        if not isinstance(dedupe, dict):
            return None
        canonical_id = dedupe.get("canonical_article_id")
        if not canonical_id:
            return None
        try:
            canonical_uuid = uuid.UUID(str(canonical_id))
        except ValueError:
            return None
        if canonical_uuid in seen:
            return None
        seen.add(canonical_uuid)

        canonical = db.get(Article, canonical_uuid)
        if not canonical:
            return None
        if canonical.event_id:
            return canonical
        current = canonical
    return None


def rebuild_rejected_missing_event(article_id: str) -> str:
    try:
        parsed_article_id = uuid.UUID(article_id)
    except ValueError:
        return "invalid"

    db = SessionLocal()
    try:
        article = (
            db.query(Article)
            .options(joinedload(Article.source))
            .filter(Article.id == parsed_article_id)
            .first()
        )
        if not article:
            return "missing"
        if article.event_id:
            return "already_linked"
        if article.status != ArticleStatus.REJECTED:
            return "not_rejected"

        canonical = resolve_canonical_with_event(db, article)
        if canonical and canonical.event:
            assign_article_to_event(
                db,
                article,
                canonical.event,
                status_on_assign=ArticleStatus.REJECTED,
                update_rollups_flag=False,
            )
            db.commit()
            print(
                f"[dedupe] linked rejected article={article.id} to canonical event={canonical.event_id}"
            )
            return "linked_canonical"

        matched_event, match_score, match_mode = match_existing_event(db, article)
        if matched_event:
            assign_article_to_event(
                db,
                article,
                matched_event,
                status_on_assign=ArticleStatus.REJECTED,
                update_rollups_flag=False,
            )
            db.commit()
            print(
                f"[dedupe] linked rejected article={article.id} "
                f"event={matched_event.id} ({match_mode} score={match_score:.3f})"
            )
            return "linked_matched"

        return "unlinked"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def run_rebuild_missing_event_ids(limit: int):
    db = SessionLocal()
    try:
        non_rejected_missing = (
            db.query(Article.id)
            .filter(
                Article.event_id.is_(None),
                Article.status != ArticleStatus.REJECTED,
            )
            .order_by(Article.created_at.asc())
            .limit(limit)
            .all()
        )
        rejected_missing = (
            db.query(Article.id)
            .filter(
                Article.event_id.is_(None),
                Article.status == ArticleStatus.REJECTED,
            )
            .order_by(Article.created_at.asc())
            .limit(limit)
            .all()
        )
    finally:
        db.close()

    non_rejected_ids = [str(row[0]) for row in non_rejected_missing]
    rejected_ids = [str(row[0]) for row in rejected_missing]
    print(
        "[dedupe] rebuild missing event_id candidates: "
        f"non_rejected={len(non_rejected_ids)} rejected={len(rejected_ids)}"
    )

    result_counts = {
        "clustered": 0,
        "duplicate": 0,
        "skipped": 0,
        "invalid": 0,
        "missing": 0,
        "linked_canonical": 0,
        "linked_matched": 0,
        "already_linked": 0,
        "not_rejected": 0,
        "unlinked": 0,
    }

    for article_id in non_rejected_ids:
        result = deduplicate_and_cluster_article(article_id, publish_next=True)
        if result in result_counts:
            result_counts[result] += 1

    for article_id in rejected_ids:
        result = rebuild_rejected_missing_event(article_id)
        if result in result_counts:
            result_counts[result] += 1

    print(f"[dedupe] rebuild missing event_id completed {result_counts}")


def handle_normalized_news_message(payload: dict):
    article_id = payload.get("article_id")
    if not article_id:
        print(f"[dedupe] payload missing article_id: {payload}")
        return
    deduplicate_and_cluster_article(str(article_id), publish_next=True)


def run_consumer():
    print(f"[dedupe] consuming from {NORMALIZED_NEWS_QUEUE}")
    consumer(NORMALIZED_NEWS_QUEUE, handle_normalized_news_message)


def run_backfill(limit: int):
    db = SessionLocal()
    try:
        normalized_articles = list_articles_by_status(db, ArticleStatus.NORMALIZED, limit=limit)
        article_ids = [str(article.id) for article in normalized_articles]
    finally:
        db.close()

    print(f"[dedupe] backfill candidates={len(article_ids)}")
    result_counts = {
        "clustered": 0,
        "duplicate": 0,
        "skipped": 0,
        "invalid": 0,
        "missing": 0,
    }
    for article_id in article_ids:
        result = deduplicate_and_cluster_article(article_id, publish_next=True)
        if result in result_counts:
            result_counts[result] += 1
    print(f"[dedupe] backfill completed {result_counts}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deduplicate normalized articles and cluster into events.")
    parser.add_argument(
        "--rebuild-missing-event-ids",
        action="store_true",
        help="Backfill missing article.event_id links across database.",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Process existing NORMALIZED articles from DB instead of consuming queue.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of NORMALIZED records to process in backfill mode.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.rebuild_missing_event_ids:
        run_rebuild_missing_event_ids(limit=args.limit)
    elif args.backfill:
        run_backfill(limit=args.limit)
    else:
        run_consumer()


if __name__ == "__main__":
    main()
