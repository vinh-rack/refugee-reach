from typing import Dict, Optional, Tuple

from strands import Agent, tool

from src.features.crisis_detector import (detect_crisis, send_sos_alert,
                                          should_escalate)


@tool
def analyze_crisis(user_input: str, location: Optional[Tuple[float, float]] = None) -> Dict:
    """
    Analyze user input for crisis situations and determine urgency level.

    Args:
        user_input: The user's message describing the situation
        location: Optional GPS coordinates (latitude, longitude)

    Returns:
        Dictionary containing crisis analysis with urgency level, keywords, injuries, and needs
    """
    crisis_report = detect_crisis(user_input, location=location)

    return {
        "urgency_level": crisis_report.urgency_level,
        "detected_keywords": crisis_report.detected_keywords,
        "location": crisis_report.location,
        "num_people": crisis_report.num_people,
        "injury_type": crisis_report.injury_type,
        "needs": crisis_report.needs,
        "summary": crisis_report.summary,
        "timestamp": crisis_report.timestamp,
        "detection_mode": crisis_report.detection_mode
    }


@tool
def trigger_sos_alert(
    urgency_level: str,
    summary: str,
    location: Optional[Tuple[float, float]] = None,
    emergency_contacts: list = None
) -> Dict:
    """
    Send SOS alert to emergency contacts when critical or high urgency is detected.

    Args:
        urgency_level: The urgency classification (critical, high, medium, low)
        summary: Crisis summary text
        location: GPS coordinates if available
        emergency_contacts: List of phone numbers or emails to alert

    Returns:
        Dictionary with alert status and alert ID
    """
    from datetime import datetime

    from src.features.crisis_detector import CrisisReport

    if emergency_contacts is None:
        emergency_contacts = ["+1234567890"]

    crisis_report = CrisisReport(
        urgency_level=urgency_level,
        detected_keywords=[],
        location=location,
        num_people=None,
        injury_type=None,
        needs=[],
        summary=summary,
        timestamp=datetime.utcnow().isoformat(),
        raw_input=summary,
        detection_mode="agent"
    )

    if should_escalate(crisis_report):
        alert = send_sos_alert(crisis_report, emergency_contacts, use_sns=False)
        return {
            "alert_sent": True,
            "alert_id": alert.alert_id,
            "status": alert.status,
            "sent_at": alert.sent_at
        }

    return {
        "alert_sent": False,
        "reason": "Urgency level does not require escalation"
    }


def create_sos_agent(model=None) -> Agent:
    """Create and configure the SOS crisis response agent."""

    if model is None:
        from src.agents.nova_client import get_sos_model
        model = get_sos_model()

    agent = Agent(
        tools=[analyze_crisis, trigger_sos_alert],
        model=model
    )

    return agent
