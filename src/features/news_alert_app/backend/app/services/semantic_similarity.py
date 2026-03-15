from __future__ import annotations

import math

from app.core.config import settings


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_similarity_scores(
    query_text: str,
    candidate_texts: list[str],
) -> list[float] | None:
    if not query_text or not candidate_texts:
        return None

    api_key = (settings.openai_api_key or "").strip()
    if not api_key or api_key.startswith("your_"):
        return None

    # Keep inputs bounded for lower latency/cost.
    texts = [query_text[:6000]] + [text[:6000] for text in candidate_texts]

    try:
        from openai import OpenAI
    except Exception:
        return None

    try:
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model=DEFAULT_EMBEDDING_MODEL,
            input=texts,
        )
    except Exception:
        return None

    vectors = [item.embedding for item in response.data]
    if len(vectors) != len(texts):
        return None

    query_vec = vectors[0]
    candidate_vecs = vectors[1:]
    return [_cosine_similarity(query_vec, vec) for vec in candidate_vecs]
