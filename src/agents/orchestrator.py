import os
from typing import Dict, Optional, Tuple

from strands import Agent, tool

from src.agents.aid_agent import (clear_captured_resources,
                                  create_aid_locator_agent,
                                  get_captured_resources)
from src.agents.general_agent import create_general_chat_agent
from src.agents.news_agent import (clear_captured_news, create_news_agent,
                                   get_captured_news)
from src.agents.nova_client import (get_general_model, get_orchestrator_model,
                                    get_sos_model)
from src.agents.sos_agent import (clear_captured_sos_alert, create_sos_agent,
                                  get_captured_sos_alert)

_sos_agent = None
_aid_agent = None
_general_agent = None
_news_agent = None
_orchestrator = None


def _extract_message_text(message) -> str:
    """
    Extract plain text from a Strands/Bedrock message object.
    Handles str, list of content blocks, or dict.
    """
    # Already a string — return directly
    if isinstance(message, str):
        return message

    # Dict with 'role' and 'content' keys (Bedrock format)
    if isinstance(message, dict) and "content" in message:
        content = message["content"]
        # Content is a list of blocks
        if isinstance(content, list):
            return " ".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("text")
            ).strip()
        # Content is a string
        elif isinstance(content, str):
            return content
        return str(content)

    # Strands returns message as a list of content blocks: [{"type": "text", "text": "..."}]
    if isinstance(message, list):
        return " ".join(
            block.get("text", "")
            for block in message
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()

    # Dict with a direct "text" key
    if isinstance(message, dict):
        return message.get("text", str(message))

    # Fallback
    return str(message)


def get_sos_agent():
    """Get or create SOS agent (lazy initialization)."""
    global _sos_agent
    if _sos_agent is None:
        _sos_agent = create_sos_agent(model=get_sos_model())
    return _sos_agent


def get_aid_agent():
    """Get or create Aid Locator agent (lazy initialization)."""
    global _aid_agent
    if _aid_agent is None:
        _aid_agent = create_aid_locator_agent(model=get_sos_model())
    return _aid_agent


def get_general_agent():
    """Get or create General Chat agent (lazy initialization)."""
    global _general_agent
    if _general_agent is None:
        _general_agent = create_general_chat_agent(model=get_general_model())
    return _general_agent


def get_news_agent():
    """Get or create News agent (lazy initialization)."""
    global _news_agent
    if _news_agent is None:
        _news_agent = create_news_agent(model=get_general_model())
    return _news_agent


@tool
def route_to_sos_agent(user_message: str, location: Optional[Tuple[float, float]] = None) -> str:
    """
    Route emergency situations to the SOS agent for crisis analysis and alert triggering.
    Use this for: injuries, bleeding, danger, violence, life-threatening situations.

    Args:
        user_message: The user's emergency message
        location: Optional GPS coordinates (latitude, longitude)

    Returns:
        Response from SOS agent with crisis analysis and alert status
    """
    context = f"User message: {user_message}"
    if location:
        context += f"\nUser location: {location[0]}, {location[1]}"

    response = get_sos_agent()(context)
    return _extract_message_text(response.message)


@tool
def route_to_aid_locator_agent(user_message: str, location: Tuple[float, float]) -> str:
    """
    Route resource finding requests to the Aid Locator agent.
    Use this for: finding hospitals, shelters, food, water, refugee camps.

    Args:
        user_message: The user's request for resources
        location: GPS coordinates (latitude, longitude) - REQUIRED

    Returns:
        Response from Aid Locator agent with nearby resources
    """
    context = f"User message: {user_message}\nUser location: {location[0]}, {location[1]}"

    response = get_aid_agent()(context)
    return _extract_message_text(response.message)


@tool
def route_to_general_chat_agent(user_message: str) -> str:
    """
    Route general questions and greetings to the General Chat agent.
    Use this for: greetings, general questions, information requests, unclear intent.

    Args:
        user_message: The user's message

    Returns:
        Response from General Chat agent
    """
    response = get_general_agent()(user_message)
    return _extract_message_text(response.message)


@tool
def route_to_news_agent(user_message: str) -> str:
    """
    Route news-related requests to the News agent.
    Use this for: latest news, current events, geopolitical updates, crisis news,
    conflict updates, what's happening in a region, news about a topic.

    Args:
        user_message: The user's message asking about news

    Returns:
        Response from News agent with latest event summaries
    """
    response = get_news_agent()(user_message)
    return _extract_message_text(response.message)


def create_orchestrator_agent(model=None) -> Agent:
    """Create and configure the Orchestrator agent."""

    if model is None:
        model = get_orchestrator_model()

    agent = Agent(
        tools=[route_to_sos_agent, route_to_aid_locator_agent, route_to_news_agent, route_to_general_chat_agent],
        model=model
    )

    return agent


def get_orchestrator():
    """Get or create orchestrator agent (lazy initialization)."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = create_orchestrator_agent(model=get_orchestrator_model())
    return _orchestrator


def process_user_input_strands(
    user_input: str,
    location: Optional[Tuple[float, float]] = None
) -> Dict:
    """
    Process user input through the Strands orchestrator agent.

    Args:
        user_input: User's message
        location: Optional GPS coordinates

    Returns:
        Dictionary with orchestrator response and metadata
    """
    context = f"User message: {user_input}"
    if location:
        context += f"\nUser location: {location[0]}, {location[1]}"

    try:
        # Clear accumulators before running
        clear_captured_resources()
        clear_captured_sos_alert()
        clear_captured_news()

        orchestrator = get_orchestrator()
        response = orchestrator(context)

        # Collect captured data from sub-agent tool calls
        resources = get_captured_resources()
        sos_alert = get_captured_sos_alert()
        news_events = get_captured_news()

        result = {
            "success": True,
            "response": _extract_message_text(response.message or []),
            "agent_used": "orchestrator",
            "user_input": user_input,
            "location": location
        }

        if resources:
            result["resources"] = resources
        if sos_alert:
            result["sos_alert"] = sos_alert
        if news_events:
            result["news_events"] = news_events

        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": "I'm having trouble processing your request. Please try again.",
            "user_input": user_input
        }
