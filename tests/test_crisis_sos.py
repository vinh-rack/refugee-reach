from unittest.mock import Mock, patch

import pytest

from src.features.crisis_detector import (CrisisReport, SOSAlert,
                                          detect_crisis,
                                          detect_crisis_with_llm,
                                          send_sos_alert, should_escalate)


def test_send_sos_alert_mock():
    report = CrisisReport(
        urgency_level="critical",
        detected_keywords=["bleeding", "dying"],
        location=(33.8938, 35.5018),
        num_people=5,
        injury_type="severe_bleeding",
        needs=["medical"],
        summary="Test summary",
        timestamp="2024-01-01T00:00:00",
        raw_input="Test input",
        detection_mode="keyword"
    )

    emergency_contacts = ["+1234567890", "+9876543210"]

    alert = send_sos_alert(report, emergency_contacts, use_sns=False)

    assert isinstance(alert, SOSAlert)
    assert alert.report == report
    assert alert.recipients == emergency_contacts
    assert alert.status == "mock_sent"
    assert alert.alert_id is not None


@patch('src.features.crisis_detector.boto3.client')
def test_send_sos_alert_sns_success(mock_boto_client):
    mock_sns = Mock()
    mock_boto_client.return_value = mock_sns

    report = CrisisReport(
        urgency_level="high",
        detected_keywords=["injured"],
        location=(33.8938, 35.5018),
        num_people=2,
        injury_type="fracture",
        needs=["medical"],
        summary="Test summary",
        timestamp="2024-01-01T00:00:00",
        raw_input="Test input",
        detection_mode="keyword"
    )

    emergency_contacts = ["+1234567890"]

    with patch.dict('os.environ', {'SNS_SOS_TOPIC_ARN': 'arn:aws:sns:us-east-1:123456789012:test'}):
        alert = send_sos_alert(report, emergency_contacts, use_sns=True)

    assert alert.status == "sent_sns"
    mock_sns.publish.assert_called_once()


@patch('src.features.crisis_detector.boto3.client')
def test_send_sos_alert_sns_no_topic(mock_boto_client):
    report = CrisisReport(
        urgency_level="critical",
        detected_keywords=["dying"],
        location=None,
        num_people=None,
        injury_type=None,
        needs=[],
        summary="Test",
        timestamp="2024-01-01T00:00:00",
        raw_input="Test",
        detection_mode="keyword"
    )

    with patch.dict('os.environ', {}, clear=True):
        alert = send_sos_alert(report, ["+1234567890"], use_sns=True)

    assert alert.status == "no_topic_configured"


@patch('src.features.crisis_detector.boto3.client')
def test_send_sos_alert_sns_failure(mock_boto_client):
    mock_sns = Mock()
    mock_sns.publish.side_effect = Exception("SNS Error")
    mock_boto_client.return_value = mock_sns

    report = CrisisReport(
        urgency_level="high",
        detected_keywords=["injured"],
        location=None,
        num_people=None,
        injury_type=None,
        needs=[],
        summary="Test",
        timestamp="2024-01-01T00:00:00",
        raw_input="Test",
        detection_mode="keyword"
    )

    with patch.dict('os.environ', {'SNS_SOS_TOPIC_ARN': 'arn:aws:sns:us-east-1:123456789012:test'}):
        alert = send_sos_alert(report, ["+1234567890"], use_sns=True)

    assert alert.status == "sns_failed"


@patch('src.features.crisis_detector.boto3.client')
def test_detect_crisis_with_llm_success(mock_boto_client):
    mock_bedrock = Mock()
    mock_response = {
        'body': Mock()
    }
    mock_response['body'].read.return_value = '''
    {
        "output": {
            "message": {
                "content": [{
                    "text": "{\\"urgency_level\\": \\"critical\\", \\"detected_keywords\\": [\\"bleeding\\", \\"dying\\"], \\"num_people\\": 5, \\"injury_type\\": \\"severe_bleeding\\", \\"needs\\": [\\"medical\\"]}"
                }]
            }
        }
    }
    '''
    mock_bedrock.invoke_model.return_value = mock_response
    mock_boto_client.return_value = mock_bedrock

    user_input = "5 people are bleeding and dying"

    report = detect_crisis_with_llm(user_input)

    assert report.urgency_level == "critical"
    assert "bleeding" in report.detected_keywords
    assert report.num_people == 5
    assert report.injury_type == "severe_bleeding"
    assert "medical" in report.needs
    assert report.detection_mode == "llm"


@patch('src.features.crisis_detector.boto3.client')
def test_detect_crisis_with_llm_fallback(mock_boto_client):
    mock_boto_client.side_effect = Exception("Bedrock Error")

    user_input = "I am injured and need help"

    report = detect_crisis_with_llm(user_input)

    assert report.detection_mode == "keyword_fallback"
    assert report.urgency_level in ["critical", "high", "medium", "low"]


def test_sos_alert_dataclass():
    report = CrisisReport(
        urgency_level="critical",
        detected_keywords=["test"],
        location=None,
        num_people=None,
        injury_type=None,
        needs=[],
        summary="Test",
        timestamp="2024-01-01T00:00:00",
        raw_input="Test",
        detection_mode="keyword"
    )

    alert = SOSAlert(
        report=report,
        alert_id="test-123",
        recipients=["+1234567890"],
        status="mock_sent",
        sent_at="2024-01-01T00:00:00"
    )

    assert alert.alert_id == "test-123"
    assert alert.status == "mock_sent"
    assert len(alert.recipients) == 1
