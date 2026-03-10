from unittest.mock import Mock, patch

import pytest

from src.agents.aid_agent import (create_aid_locator_agent,
                                  search_nearby_resources)
from src.agents.general_agent import create_general_chat_agent
from src.agents.sos_agent import (analyze_crisis, create_sos_agent,
                                  trigger_sos_alert)


@patch('src.agents.nova_client.NovaAPIModel')
def test_create_general_chat_agent(mock_model):
    mock_model.return_value = Mock()

    agent = create_general_chat_agent(model=mock_model.return_value)

    assert agent is not None


@patch('src.agents.sos_agent.detect_crisis')
def test_analyze_crisis_tool(mock_detect):
    from src.features.crisis_detector import CrisisReport

    mock_report = CrisisReport(
        urgency_level="critical",
        detected_keywords=["bleeding"],
        location=(33.8938, 35.5018),
        num_people=3,
        injury_type="severe_bleeding",
        needs=["medical"],
        summary="Test summary",
        timestamp="2024-01-01T00:00:00",
        raw_input="Test",
        detection_mode="keyword"
    )
    mock_detect.return_value = mock_report

    result = analyze_crisis("Help! Bleeding", location=(33.8938, 35.5018))

    assert result["urgency_level"] == "critical"
    assert "bleeding" in result["detected_keywords"]
    assert result["location"] == (33.8938, 35.5018)


@patch('src.agents.sos_agent.send_sos_alert')
@patch('src.agents.sos_agent.should_escalate')
def test_trigger_sos_alert_tool(mock_escalate, mock_send):
    from src.features.crisis_detector import SOSAlert

    mock_escalate.return_value = True

    mock_alert = SOSAlert(
        report=Mock(),
        alert_id="test-123",
        recipients=["+1234567890"],
        status="mock_sent",
        sent_at="2024-01-01T00:00:00"
    )
    mock_send.return_value = mock_alert

    result = trigger_sos_alert(
        urgency_level="critical",
        summary="Emergency",
        location=(33.8938, 35.5018)
    )

    assert result["alert_sent"] is True
    assert result["alert_id"] == "test-123"


def test_trigger_sos_alert_no_escalation():
    result = trigger_sos_alert(
        urgency_level="low",
        summary="General question"
    )

    assert result["alert_sent"] is False
    assert "reason" in result


@patch('src.agents.aid_agent.find_aid_resources')
def test_search_nearby_resources_tool(mock_find):
    from src.features.aid_locator import AidResource

    mock_resources = [
        AidResource(
            name="Test Hospital",
            type="hospital",
            latitude=33.8938,
            longitude=35.5018,
            distance_km=1.5,
            source="OpenStreetMap"
        )
    ]
    mock_find.return_value = mock_resources

    result = search_nearby_resources(33.8938, 35.5018, radius_km=10)

    assert result["resources_found"] == 1
    assert result["resources"][0]["name"] == "Test Hospital"
    assert result["search_radius_km"] == 10


def test_filter_resources_by_type():
    from src.agents.aid_agent import filter_resources_by_type

    resources = [
        {"name": "Hospital A", "type": "hospital"},
        {"name": "Clinic B", "type": "clinic"},
        {"name": "Hospital C", "type": "hospital"}
    ]

    filtered = filter_resources_by_type(resources, "hospital")

    assert len(filtered) == 2
    assert all("hospital" in r["type"] for r in filtered)
