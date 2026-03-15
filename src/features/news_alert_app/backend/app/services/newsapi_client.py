import httpx
from datetime import datetime, timezone
from app.core.config import settings

NEWSAPI_EVERYTHING_URL = "https://newsapi.org/v2/everything"

def fetch_newsapi_everything(
    query: str, 
    from_dt: datetime | None=None, 
    language='en', 
    search_in: str | None = None,
    sort_by: str = 'publishedAt',
    page_size: int = 100,
    page: int = 1
    ) -> dict:
    params = {
        "q": query,
        "language": language,
        "sortBy": sort_by,
        "pageSize": page_size,
        "page": page,
    }
    if search_in:
        params["searchIn"] = search_in
    if from_dt:
        params["from"] = from_dt.astimezone(timezone.utc).isoformat()
        
    headers = {
        "X-Api-Key": settings.newsapi_key,
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.get(NEWSAPI_EVERYTHING_URL, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "error":
            code = data.get("code", "unknown")
            message = data.get("message", "unknown")
            raise RuntimeError(f"NewsAPI error ({code}): {message}")
        return data
