from typing import Dict, List, Optional

from strands import Agent, tool

from src.agents.nova_client import get_general_model
from src.features.news_service import (get_event_by_id, get_latest_events,
                                       news_event_to_dict)

# Accumulator for captured news results
_captured_news: List[Dict] = []


def get_captured_news() -> List[Dict]:
    """Return and clear captured news events."""
    global _captured_news
    result = list(_captured_news)
    _captured_news = []
    return result


def clear_captured_news():
    """Clear captured news events."""
    global _captured_news
    _captured_news = []


@tool
def fetch_latest_news(
    topic: Optional[str] = None,
    region: Optional[str] = None,
    min_severity: Optional[float] = None,
    limit: int = 10,
) -> Dict:
    """
    Fetch the latest geopolitical news events from the database.

    Args:
        topic: Filter by topic (e.g. "Conflict", "Diplomacy", "Sanctions")
        region: Filter by region (e.g. "Middle East", "Eastern Europe", "East Asia")
        min_severity: Minimum severity score (0.0 to 1.0) to filter critical events
        limit: Maximum number of events to return (default: 10)

    Returns:
        Dictionary with list of news events including titles, summaries, severity, and source articles
    """
    global _captured_news

    try:
        events = get_latest_events(
            limit=limit,
            topic=topic,
            region=region,
            min_severity=min_severity,
        )
        event_dicts = [news_event_to_dict(e) for e in events]
        _captured_news.extend(event_dicts)

        return {
            "success": True,
            "count": len(event_dicts),
            "events": event_dicts,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "events": [],
        }


@tool
def get_news_event_detail(event_id: str) -> Dict:
    """
    Get detailed information about a specific news event including all source articles.

    Args:
        event_id: The UUID of the event cluster to retrieve

    Returns:
        Dictionary with full event details and all associated articles
    """
    global _captured_news

    try:
        event = get_event_by_id(event_id)
        if not event:
            return {"success": False, "error": f"Event {event_id} not found"}

        event_dict = news_event_to_dict(event)
        _captured_news.append(event_dict)

        return {
            "success": True,
            "event": event_dict,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_news_agent(model=None) -> Agent:
    """Create and configure the News agent."""
    if model is None:
        model = get_general_model()

    agent = Agent(
        tools=[fetch_latest_news, get_news_event_detail],
        model=model,
    )
    return agent
