from __future__ import annotations

import argparse
import hashlib
from html import unescape
from pathlib import Path
import re
import sys
import uuid
from urllib.parse import urlparse, urlunparse

# Allow running this file directly: `python workers/normalize/main.py`
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.enums import ArticleStatus
from app.queue.constant import NORMALIZED_NEWS_QUEUE, RAW_NEWS_QUEUE
from app.queue.rabbitmq import consumer, publish
from app.repos.article_repo import get_article_by_id, list_articles_by_status


TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[a-z][a-z0-9'-]{2,}")

STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "from", "into", "have", "has", "had",
    "was", "were", "are", "will", "would", "could", "should", "about", "after", "before",
    "under", "over", "between", "during", "their", "there", "which", "while", "where",
    "when", "what", "who", "your", "ours", "ourselves", "them", "they", "its", "it's",
    "into", "out", "new", "news", "says", "said", "say", "than", "then", "also",
}

REGION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Eastern Europe": ("ukraine", "russia", "crimea", "donbas"),
    "Middle East": ("israel", "gaza", "iran", "syria", "lebanon", "red sea", "yemen"),
    "East Asia": ("taiwan", "china", "south china sea", "korea", "japan"),
    "Global": ("nato", "un", "united nations", "sanctions", "diplomacy"),
}

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Conflict": ("war", "airstrike", "missile", "military", "ceasefire", "troop"),
    "Diplomacy": ("talks", "summit", "negotiation", "diplomacy", "agreement"),
    "Sanctions": ("sanction", "embargo", "restriction"),
    "Security": ("defense", "security", "border", "naval"),
}


def normalize_text(value: str | None) -> str | None:
    if not value:
        return None
    text = unescape(value)
    text = TAG_RE.sub(" ", text)
    text = WS_RE.sub(" ", text).strip()
    return text or None


def normalize_author(value: str | None) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    text = re.sub(r"^(by|from)\s+", "", text, flags=re.IGNORECASE)
    parts = [p.strip() for p in re.split(r"[|;/]+", text) if p.strip()]
    if not parts:
        return None
    # Preserve first-seen order and remove duplicates.
    deduped = list(dict.fromkeys(parts))
    return ", ".join(deduped)[:255]


def canonicalize_url(url: str | None) -> str:
    if not url:
        return ""
    raw = url.strip()
    parsed = urlparse(raw)
    if not parsed.scheme:
        return raw
    normalized = parsed._replace(query="", fragment="")
    return urlunparse(normalized).rstrip("/")


def extract_domain(url: str) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def extract_keywords(text: str, top_n: int = 12) -> list[str]:
    counts: dict[str, int] = {}
    for token in TOKEN_RE.findall(text.lower()):
        if token in STOPWORDS:
            continue
        counts[token] = counts.get(token, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:top_n]]


def infer_label(text: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
    lowered = text.lower()
    for label, keywords in mapping.items():
        if any(keyword in lowered for keyword in keywords):
            return label
    return None


def compute_normalized_hash(title: str | None, body: str | None, url: str | None) -> str | None:
    pieces = [normalize_text(title), normalize_text(body), canonicalize_url(url)]
    normalized = "|".join((part or "").lower() for part in pieces).strip("|")
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_quality_score(
    title: str | None,
    body: str | None,
    author: str | None,
    published_at_present: bool,
) -> float:
    score = 0.0
    if title:
        score += 0.35
    if body and len(body) >= 120:
        score += 0.45
    if author:
        score += 0.10
    if published_at_present:
        score += 0.10
    return round(score, 3)


def normalize_article(article_id: str, publish_next: bool = True) -> bool:
    try:
        parsed_article_id = uuid.UUID(article_id)
    except ValueError:
        print(f"[normalize] invalid article_id: {article_id}")
        return False

    db = SessionLocal()
    try:
        article = get_article_by_id(db, parsed_article_id)
        if not article:
            print(f"[normalize] article not found: {article_id}")
            return False

        if article.status != ArticleStatus.INGESTED:
            print(f"[normalize] skipping {article_id}, status={article.status}")
            return False

        canonical_url = canonicalize_url(article.url)
        article.title = normalize_text(article.title)
        article.body = normalize_text(article.body) or normalize_text(article.summary_hint)
        article.summary_hint = normalize_text(article.summary_hint)
        article.author = normalize_author(article.author)
        article.language = (article.language or "en").lower()
        article.url = canonical_url or article.url

        merged_text = " ".join(
            value for value in [article.title, article.body, article.summary_hint] if value
        )
        keywords = extract_keywords(merged_text) if merged_text else []
        article.keywords = keywords or None

        if not article.region_hint and merged_text:
            article.region_hint = infer_label(merged_text, REGION_KEYWORDS)
        if not article.topic_hint and merged_text:
            article.topic_hint = infer_label(merged_text, TOPIC_KEYWORDS)

        article.normalized_hash = compute_normalized_hash(article.title, article.body, article.url)
        article.quality_score = compute_quality_score(
            article.title,
            article.body,
            article.author,
            article.published_at is not None,
        )
        metadata = dict(article.extra_metadata or {})
        metadata["canonical_url"] = article.url
        metadata["source_domain"] = extract_domain(article.url)
        metadata["normalized_by"] = "workers.normalize"
        article.extra_metadata = metadata
        article.status = ArticleStatus.NORMALIZED

        db.commit()

        if publish_next:
            try:
                publish(NORMALIZED_NEWS_QUEUE, {"article_id": str(article.id)})
            except Exception as exc:
                print(f"[normalize] warning: normalized publish failed for {article.id}: {exc}")
        print(f"[normalize] normalized article={article.id}")
        return True
    except Exception as exc:
        db.rollback()
        print(f"[normalize] failed for article_id={article_id}: {exc}")
        raise
    finally:
        db.close()


def handle_raw_news_message(payload: dict):
    article_id = payload.get("article_id")
    if not article_id:
        print(f"[normalize] payload missing article_id: {payload}")
        return
    normalize_article(str(article_id), publish_next=True)


def run_consumer():
    print(f"[normalize] consuming from {RAW_NEWS_QUEUE}")
    consumer(RAW_NEWS_QUEUE, handle_raw_news_message)


def run_backfill(limit: int):
    db = SessionLocal()
    try:
        ingested = list_articles_by_status(db, ArticleStatus.INGESTED, limit=limit)
        article_ids = [str(article.id) for article in ingested]
    finally:
        db.close()

    print(f"[normalize] backfill candidates={len(article_ids)}")
    normalized_count = 0
    for article_id in article_ids:
        if normalize_article(article_id, publish_next=True):
            normalized_count += 1
    print(f"[normalize] backfill completed normalized={normalized_count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize article payloads into a unified format.")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Normalize existing INGESTED articles from the database instead of consuming queue.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of INGESTED records to process in backfill mode.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.backfill:
        run_backfill(limit=args.limit)
    else:
        run_consumer()


if __name__ == "__main__":
    main()
