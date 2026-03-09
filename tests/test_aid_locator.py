from unittest.mock import Mock, patch

import pytest

from src.agents.aid_locator import (AidResource, calculate_distance,
                                    find_aid_resources, query_openstreetmap,
                                    query_unhcr_camps)


def test_calculate_distance():
    lat1, lon1 = 40.7128, -74.0060
    lat2, lon2 = 34.0522, -118.2437

    distance = calculate_distance(lat1, lon1, lat2, lon2)

    assert 3900 < distance < 4000


def test_calculate_distance_same_location():
    distance = calculate_distance(40.7128, -74.0060, 40.7128, -74.0060)
    assert distance == 0.0


@patch('src.agents.aid_locator.requests.get')
def test_query_unhcr_camps_success(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "name": "Test Camp",
                "latitude": "40.7128",
                "longitude": "-74.0060"
            }
        ]
    }
    mock_get.return_value = mock_response

    camps = query_unhcr_camps(40.7128, -74.0060, radius_km=50)

    assert len(camps) == 1
    assert camps[0]["name"] == "Test Camp"
    assert camps[0]["type"] == "refugee_camp"
    assert camps[0]["source"] == "UNHCR"


@patch('src.agents.aid_locator.requests.get')
def test_query_unhcr_camps_failure(mock_get):
    mock_get.side_effect = Exception("API Error")

    camps = query_unhcr_camps(40.7128, -74.0060)

    assert camps == []


@patch('src.agents.aid_locator.requests.post')
def test_query_openstreetmap_success(mock_post):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "elements": [
            {
                "type": "node",
                "lat": 40.7128,
                "lon": -74.0060,
                "tags": {
                    "name": "Test Hospital",
                    "amenity": "hospital",
                    "phone": "+1234567890"
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    resources = query_openstreetmap(40.7128, -74.0060, radius_km=10)

    assert len(resources) == 1
    assert resources[0]["name"] == "Test Hospital"
    assert resources[0]["type"] == "hospital"
    assert resources[0]["source"] == "OpenStreetMap"


@patch('src.agents.aid_locator.requests.post')
def test_query_openstreetmap_failure(mock_post):
    mock_post.side_effect = Exception("API Error")

    resources = query_openstreetmap(40.7128, -74.0060)

    assert resources == []


@patch('src.agents.aid_locator.query_openstreetmap')
@patch('src.agents.aid_locator.query_unhcr_camps')
def test_find_aid_resources(mock_unhcr, mock_osm):
    mock_osm.return_value = [
        {
            "name": "Hospital A",
            "type": "hospital",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "distance_km": 1.0,
            "source": "OpenStreetMap"
        }
    ]
    mock_unhcr.return_value = [
        {
            "name": "Camp B",
            "type": "refugee_camp",
            "latitude": 40.7200,
            "longitude": -74.0100,
            "distance_km": 2.0,
            "source": "UNHCR"
        }
    ]

    resources = find_aid_resources(40.7128, -74.0060, radius_km=10, max_results=20)

    assert len(resources) == 2
    assert isinstance(resources[0], AidResource)
    assert resources[0].name == "Hospital A"
    assert resources[0].distance_km == 1.0
    assert resources[1].name == "Camp B"


@patch('src.agents.aid_locator.query_openstreetmap')
@patch('src.agents.aid_locator.query_unhcr_camps')
def test_find_aid_resources_max_results(mock_unhcr, mock_osm):
    mock_osm.return_value = [
        {
            "name": f"Resource {i}",
            "type": "hospital",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "distance_km": float(i),
            "source": "OpenStreetMap"
        }
        for i in range(15)
    ]
    mock_unhcr.return_value = []

    resources = find_aid_resources(40.7128, -74.0060, max_results=5)

    assert len(resources) == 5


def test_aid_resource_dataclass():
    resource = AidResource(
        name="Test Hospital",
        type="hospital",
        latitude=40.7128,
        longitude=-74.0060,
        distance_km=1.5,
        address="123 Main St",
        contact="+1234567890",
        hours="24/7",
        source="OpenStreetMap"
    )

    assert resource.name == "Test Hospital"
    assert resource.type == "hospital"
    assert resource.distance_km == 1.5
    assert resource.source == "OpenStreetMap"
