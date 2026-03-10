from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "agents_configured" in data


@patch('src.api.main.get_device_location')
def test_get_location_success(mock_location):
    mock_location.return_value = (40.7128, -74.0060)

    response = client.get("/location")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["latitude"] == 40.7128
    assert data["longitude"] == -74.0060


@patch('src.api.main.get_device_location')
def test_get_location_failure(mock_location):
    mock_location.return_value = None

    response = client.get("/location")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False


@patch('src.api.main.process_user_input_strands')
def test_chat_basic(mock_process):
    mock_process.return_value = {
        "success": True,
        "response": "Hello! How can I help you?",
        "agent_used": "general",
        "location": None
    }

    response = client.post("/chat", json={
        "message": "Hello"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["response"] == "Hello! How can I help you?"
    assert data["agent_used"] == "general"


@patch('src.api.main.process_user_input_strands')
def test_chat_with_location(mock_process):
    mock_process.return_value = {
        "success": True,
        "response": "Found nearby hospitals",
        "agent_used": "aid_locator",
        "location": (33.8938, 35.5018)
    }

    response = client.post("/chat", json={
        "message": "Find hospitals",
        "location": [33.8938, 35.5018]
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["location"] == [33.8938, 35.5018]


@patch('src.api.main.get_device_location')
@patch('src.api.main.process_user_input_strands')
def test_chat_auto_detect_location(mock_process, mock_location):
    mock_location.return_value = (40.7128, -74.0060)
    mock_process.return_value = {
        "success": True,
        "response": "Response",
        "agent_used": "orchestrator"
    }

    response = client.post("/chat", json={
        "message": "Help me",
        "auto_detect_location": True
    })

    assert response.status_code == 200
    mock_location.assert_called_once()


@patch('src.api.main.process_user_input_strands')
def test_chat_error_handling(mock_process):
    mock_process.side_effect = Exception("Test error")

    response = client.post("/chat", json={
        "message": "Test"
    })

    assert response.status_code == 500
