from __future__ import annotations

import json
from typing import Any

from app.core.config import settings


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = (
    "You are a geopolitical risk analyst. "
    "Return only valid JSON with keys: "
    "topic, region, severity_score, confidence_score, summary, reasoning_brief, "
    "key_entities, risk_labels, evidence. "
    "severity_score and confidence_score must be floats in range 0.0 to 1.0 "
    "(where 1.0 means maximum severity/confidence)."
)

HIGH_RISK_TERMS = {
    "airstrike", "missile", "invasion", "attack", "military strike", "troop",
    "escalation", "blockade", "bombing", "assassination",
}
MEDIUM_RISK_TERMS = {
    "sanction", "ceasefire", "diplomacy", "summit", "border", "warship", "military",
    "conflict", "security", "hostage",
}


def _clamp_score(value: Any, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    # Compatibility: if model returns 1..10 scale, convert to 0..1.
    if numeric > 1.0 and numeric <= 10.0:
        numeric = numeric / 10.0
    # Compatibility: if model returns percentage scale (0..100), convert to 0..1.
    elif numeric > 10.0 and numeric <= 100.0:
        numeric = numeric / 100.0
    return max(0.0, min(1.0, round(numeric, 4)))


def _extract_json_block(text: str) -> dict:
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    block = text[start : end + 1]
    try:
        parsed = json.loads(block)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _heuristic_analysis(event, articles: list, reason: str) -> dict:
    title = event.canonical_title or "Event analysis"
    snippets = []
    combined = []
    for article in articles[:8]:
        t = (article.title or "").strip()
        b = (article.body or article.summary_hint or "").strip()
        if t:
            snippets.append(t)
        if b:
            combined.append(b.lower())
    text = " ".join(combined)

    high_hits = sum(1 for term in HIGH_RISK_TERMS if term in text)
    medium_hits = sum(1 for term in MEDIUM_RISK_TERMS if term in text)
    severity = 0.2 + (high_hits * 0.15) + (medium_hits * 0.06)
    confidence = min(0.9, 0.35 + (len(articles) * 0.04))

    if severity >= 0.75:
        risk_labels = ["high-risk-escalation"]
    elif severity >= 0.5:
        risk_labels = ["moderate-risk"]
    else:
        risk_labels = ["low-to-moderate-risk"]

    summary_seed = "; ".join(snippets[:3]).strip()
    summary = f"{title}. Key coverage: {summary_seed}" if summary_seed else title

    return {
        "topic": event.topic,
        "region": event.region,
        "severity_score": _clamp_score(severity, 0.4),
        "confidence_score": _clamp_score(confidence, 0.5),
        "summary": summary[:3000],
        "reasoning_brief": f"Heuristic fallback used ({reason}).",
        "key_entities": [],
        "risk_labels": risk_labels,
        "evidence": {
            "article_count": len(articles),
            "sample_titles": snippets[:5],
            "mode": "heuristic",
            "reason": reason,
        },
        "raw_response": {"provider": "heuristic", "reason": reason},
        "model_name": "heuristic-fallback",
        "model_version": None,
    }


def _build_event_payload(event, articles: list) -> dict:
    article_payload = []
    for article in articles[:15]:
        article_payload.append(
            {
                "article_id": str(article.id),
                "title": article.title,
                "summary_hint": article.summary_hint,
                "body_excerpt": (article.body or "")[:1200],
                "topic_hint": article.topic_hint,
                "region_hint": article.region_hint,
                "source_id": str(article.source_id),
                "url": article.url,
                "published_at": article.published_at.isoformat() if article.published_at else None,
            }
        )

    return {
        "event_id": str(event.id),
        "canonical_title": event.canonical_title,
        "topic": event.topic,
        "region": event.region,
        "article_count": len(articles),
        "articles": article_payload,
    }


def _normalize_model_output(parsed: dict, event, articles: list, model_name: str, raw_response: dict) -> dict:
    summary = (parsed.get("summary") or "").strip()
    if not summary:
        summary = _heuristic_analysis(event, articles, "missing_summary")["summary"]

    key_entities = parsed.get("key_entities")
    if not isinstance(key_entities, list):
        key_entities = []
    risk_labels = parsed.get("risk_labels")
    if not isinstance(risk_labels, list):
        risk_labels = []
    evidence = parsed.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {"notes": "No structured evidence returned"}

    return {
        "topic": parsed.get("topic") or event.topic,
        "region": parsed.get("region") or event.region,
        "severity_score": _clamp_score(parsed.get("severity_score"), 0.4),
        "confidence_score": _clamp_score(parsed.get("confidence_score"), 0.5),
        "summary": summary[:3000],
        "reasoning_brief": (parsed.get("reasoning_brief") or "")[:3000] or None,
        "key_entities": key_entities[:50],
        "risk_labels": risk_labels[:50],
        "evidence": evidence,
        "raw_response": raw_response,
        "model_name": model_name,
        "model_version": None,
    }


def analyze_event_with_openai(event, articles: list) -> dict:
    api_key = (settings.openai_api_key or "").strip()
    if not api_key or api_key.startswith("your_"):
        return _heuristic_analysis(event, articles, "openai_api_key_not_configured")

    payload = _build_event_payload(event, articles)
    payload_text = json.dumps(payload, ensure_ascii=False)

    try:
        from openai import OpenAI
    except Exception:
        return _heuristic_analysis(event, articles, "openai_sdk_not_available")

    client = OpenAI(api_key=api_key)
    model_name = DEFAULT_OPENAI_MODEL
    raw_response: dict = {}
    parsed: dict = {}

    try:
        response = client.responses.create(
            model=DEFAULT_OPENAI_MODEL,
            temperature=0.2,
            input=[
                {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": [{"type": "text", "text": payload_text}]},
            ],
        )
        model_name = getattr(response, "model", DEFAULT_OPENAI_MODEL)
        raw_response = response.model_dump() if hasattr(response, "model_dump") else {}
        parsed = _extract_json_block(getattr(response, "output_text", "") or "")
    except Exception:
        try:
            completion = client.chat.completions.create(
                model=DEFAULT_OPENAI_MODEL,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": payload_text},
                ],
            )
            model_name = getattr(completion, "model", DEFAULT_OPENAI_MODEL)
            raw_response = completion.model_dump() if hasattr(completion, "model_dump") else {}
            content = ""
            if completion.choices and completion.choices[0].message:
                content = completion.choices[0].message.content or ""
            parsed = _extract_json_block(content)
        except Exception as exc:
            return _heuristic_analysis(event, articles, f"openai_call_failed: {exc}")

    if not parsed:
        return _heuristic_analysis(event, articles, "openai_response_not_json")

    return _normalize_model_output(parsed, event, articles, model_name, raw_response)
