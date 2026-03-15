from __future__ import annotations

from datetime import datetime
from html import escape
import uuid

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import joinedload

from app.db.session import SessionLocal
from app.models.article import Article
from app.models.event_article import EventArticle
from app.models.event_cluster import EventCluster


app = FastAPI(title="Geopolitical News Alert App", version="1.0")


def _article_sort_key(article: Article) -> datetime:
    return article.published_at or article.fetched_at or article.created_at or datetime.min


def _collect_unique_articles(event: EventCluster) -> list[Article]:
    merged: dict[uuid.UUID, Article] = {}

    for article in event.articles:
        merged[article.id] = article

    for link in event.event_articles:
        if link.article:
            merged[link.article.id] = link.article

    return sorted(merged.values(), key=_article_sort_key, reverse=True)


def _serialize_article(article: Article) -> dict:
    return {
        "id": str(article.id),
        "title": article.title,
        "url": article.url,
        "source_name": article.source.name if article.source else None,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "fetched_at": article.fetched_at.isoformat() if article.fetched_at else None,
    }


def _serialize_event(event: EventCluster, include_articles: bool = False) -> dict:
    articles = _collect_unique_articles(event)
    payload = {
        "id": str(event.id),
        "canonical_title": event.canonical_title,
        "topic": event.topic,
        "region": event.region,
        "status": event.status.value if event.status else None,
        "source_count": event.source_count,
        "trusted_source_count": event.trusted_source_count,
        "latest_severity_score": event.latest_severity_score,
        "latest_confidence_score": event.latest_confidence_score,
        "latest_summary": event.latest_summary,
        "first_seen_at": event.first_seen_at.isoformat() if event.first_seen_at else None,
        "last_seen_at": event.last_seen_at.isoformat() if event.last_seen_at else None,
        "article_count": len(articles),
    }
    if include_articles:
        payload["articles"] = [_serialize_article(article) for article in articles]
    else:
        payload["article_preview"] = [_serialize_article(article) for article in articles[:3]]
    return payload


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/events")
def list_events(limit: int = Query(default=50, ge=1, le=500)):
    db = SessionLocal()
    try:
        events = (
            db.query(EventCluster)
            .options(
                joinedload(EventCluster.articles).joinedload(Article.source),
                joinedload(EventCluster.event_articles)
                .joinedload(EventArticle.article)
                .joinedload(Article.source),
            )
            .order_by(EventCluster.last_seen_at.desc())
            .limit(limit)
            .all()
        )
        return {"events": [_serialize_event(event, include_articles=False) for event in events]}
    finally:
        db.close()


@app.get("/api/events/{event_id}")
def get_event(event_id: uuid.UUID):
    db = SessionLocal()
    try:
        event = (
            db.query(EventCluster)
            .options(
                joinedload(EventCluster.articles).joinedload(Article.source),
                joinedload(EventCluster.event_articles)
                .joinedload(EventArticle.article)
                .joinedload(Article.source),
            )
            .filter(EventCluster.id == event_id)
            .first()
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return _serialize_event(event, include_articles=True)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
@app.get("/events", response_class=HTMLResponse)
def events_page():
    return HTMLResponse(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>RefugeeReach Event Clusters</title>
  <style>
    :root {
      --bg-1: #f5f7f2;
      --bg-2: #dcece8;
      --ink: #0f2d2b;
      --muted: #426b66;
      --accent: #0f766e;
      --card: #ffffff;
      --border: #b9d6d1;
      --danger: #9f1239;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1200px 420px at 15% -10%, #cde8df 0%, transparent 70%),
        radial-gradient(1000px 400px at 100% 0%, #d5e4f8 0%, transparent 65%),
        linear-gradient(180deg, var(--bg-2), var(--bg-1));
      min-height: 100vh;
    }
    .wrap {
      max-width: 1100px;
      margin: 0 auto;
      padding: 28px 16px 40px;
    }
    h1 {
      margin: 0;
      font-size: clamp(1.6rem, 1.4rem + 1vw, 2.6rem);
      letter-spacing: 0.02em;
    }
    .subtitle {
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.95rem;
    }
    .toolbar {
      margin-top: 18px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    input[type="search"] {
      flex: 1;
      min-width: 240px;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.9);
      border-radius: 10px;
      padding: 11px 12px;
      color: var(--ink);
      font-size: 0.95rem;
    }
    button {
      border: none;
      border-radius: 10px;
      padding: 11px 16px;
      font-weight: 600;
      cursor: pointer;
      background: var(--accent);
      color: white;
    }
    #grid {
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 12px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 6px 20px rgba(17, 24, 39, 0.06);
      opacity: 0;
      transform: translateY(8px);
      animation: rise .35s ease forwards;
    }
    @keyframes rise { to { opacity: 1; transform: translateY(0);} }
    .meta {
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.86rem;
    }
    .summary {
      margin-top: 10px;
      font-size: 0.92rem;
      line-height: 1.35rem;
    }
    .chip {
      display: inline-block;
      font-size: 0.76rem;
      margin-right: 8px;
      margin-top: 8px;
      border-radius: 999px;
      padding: 4px 8px;
      border: 1px solid var(--border);
      color: var(--muted);
      background: #f2faf8;
    }
    .sev-high { color: var(--danger); border-color: #f7c5d6; background: #fff1f6; }
    .view {
      display: inline-block;
      margin-top: 10px;
      color: var(--accent);
      text-decoration: none;
      font-weight: 700;
    }
    .empty { color: var(--muted); margin-top: 20px; }
    @media (max-width: 640px) {
      .wrap { padding-top: 18px; }
      .card { padding: 12px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Clustered News Events</h1>
    <div class="subtitle">All news grouped by event; open one cluster to view source articles.</div>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Filter by title, topic, or region..." />
      <button id="refreshBtn" type="button">Refresh</button>
    </div>
    <div id="grid"></div>
    <div id="empty" class="empty" style="display:none;">No clustered events found.</div>
  </div>
<script>
  const grid = document.getElementById("grid");
  const empty = document.getElementById("empty");
  const search = document.getElementById("search");
  const refreshBtn = document.getElementById("refreshBtn");
  let eventsCache = [];

  function sevClass(v) {
    if (typeof v !== "number") return "";
    return v >= 0.8 ? "sev-high" : "";
  }

  function fmt(v) {
    return typeof v === "number" ? v.toFixed(2) : "n/a";
  }

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function render(list) {
    grid.innerHTML = "";
    if (!list.length) {
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
    list.forEach((event, idx) => {
      const card = document.createElement("article");
      card.className = "card";
      card.style.animationDelay = `${Math.min(idx * 0.03, 0.2)}s`;
      const severity = fmt(event.latest_severity_score);
      card.innerHTML = `
        <h3>${esc(event.canonical_title || "Untitled event")}</h3>
        <div class="meta">${esc(event.article_count)} articles | Last seen: ${esc(event.last_seen_at || "n/a")}</div>
        <div>
          <span class="chip ${sevClass(event.latest_severity_score)}">Severity ${severity}</span>
          <span class="chip">Confidence ${fmt(event.latest_confidence_score)}</span>
          <span class="chip">${esc(event.topic || "unknown topic")} / ${esc(event.region || "unknown region")}</span>
        </div>
        <div class="summary">${esc(event.latest_summary || "No summary available.")}</div>
        <a class="view" href="/events/${esc(event.id)}">View clustered articles -></a>
      `;
      grid.appendChild(card);
    });
  }

  async function load() {
    const res = await fetch("/api/events?limit=200");
    const data = await res.json();
    eventsCache = data.events || [];
    applyFilter();
  }

  function applyFilter() {
    const q = search.value.trim().toLowerCase();
    if (!q) {
      render(eventsCache);
      return;
    }
    render(eventsCache.filter((e) => {
      const haystack = `${e.canonical_title || ""} ${e.topic || ""} ${e.region || ""}`.toLowerCase();
      return haystack.includes(q);
    }));
  }

  search.addEventListener("input", applyFilter);
  refreshBtn.addEventListener("click", load);
  load();
</script>
</body>
</html>
        """
    )


@app.get("/events/{event_id}", response_class=HTMLResponse)
def event_detail_page(event_id: uuid.UUID):
    db = SessionLocal()
    try:
        event = (
            db.query(EventCluster)
            .options(
                joinedload(EventCluster.articles).joinedload(Article.source),
                joinedload(EventCluster.event_articles)
                .joinedload(EventArticle.article)
                .joinedload(Article.source),
            )
            .filter(EventCluster.id == event_id)
            .first()
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        articles = _collect_unique_articles(event)
        article_html = ""
        for article in articles:
            title = escape(article.title or "Untitled article")
            source_name = escape(article.source.name) if article.source and article.source.name else "Unknown"
            published = escape(article.published_at.isoformat() if article.published_at else "n/a")
            url = escape(article.url)
            article_html += (
                f'<li><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'
                f'<div class="meta">{source_name} | {published}</div></li>'
            )

        summary = escape(event.latest_summary or "No summary available.")
        title = escape(event.canonical_title or "Untitled event")
        topic = escape(event.topic or "unknown")
        region = escape(event.region or "unknown")
        severity = (
            f"{event.latest_severity_score:.2f}" if event.latest_severity_score is not None else "n/a"
        )
        confidence = (
            f"{event.latest_confidence_score:.2f}" if event.latest_confidence_score is not None else "n/a"
        )

        return HTMLResponse(
            f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
      background: linear-gradient(180deg, #edf6f3, #f9fcfb);
      color: #102926;
    }}
    .wrap {{ max-width: 920px; margin: 0 auto; padding: 22px 16px 40px; }}
    a.back {{ color: #0f766e; text-decoration: none; font-weight: 700; }}
    h1 {{ margin: 12px 0; }}
    .meta {{ color: #476863; font-size: 0.9rem; }}
    .summary {{ background: #fff; border: 1px solid #c8dfd9; border-radius: 12px; padding: 12px; margin-top: 12px; }}
    ul {{ list-style: none; padding: 0; margin: 14px 0 0; }}
    li {{ background: #fff; border: 1px solid #c8dfd9; border-radius: 12px; padding: 10px 12px; margin-bottom: 10px; }}
    li a {{ color: #114f49; text-decoration: none; font-weight: 700; }}
  </style>
</head>
<body>
  <div class="wrap">
    <a class="back" href="/events">&larr; Back to clusters</a>
    <h1>{title}</h1>
    <div class="meta">Topic: {topic} | Region: {region} | Severity: {severity} | Confidence: {confidence}</div>
    <div class="summary">{summary}</div>
    <h3>Clustered Articles ({len(articles)})</h3>
    <ul>{article_html}</ul>
  </div>
</body>
</html>
            """
        )
    finally:
        db.close()
