from unittest.mock import Mock, patch

import pytest

from src.features.location_service import (get_device_location,
                                           get_location_from_env,
                                           get_location_from_ip)


@patch('src.features.location_service.geocoder.ip')
def test_get_location_from_ip_success(mock_geocoder_ip):
    mock_result = Mock()
    mock_result.latlng = [40.7128, -74.0060]
    mock_geocoder_ip.return_value = mock_result

    location = get_location_from_ip()

    assert location == (40.7128, -74.0060)
    mock_geocoder_ip.assert_called_once_with('me')


@patch('src.features.location_service.geocoder.ip')
def test_get_location_from_ip_failure(mock_geocoder_ip):
    mock_geocoder_ip.side_effect = Exception("Network error")

    location = get_location_from_ip()

    assert location is None


@patch('src.features.location_service.geocoder.ip')
def test_get_location_from_ip_no_coordinates(mock_geocoder_ip):
    mock_result = Mock()
    mock_result.latlng = None
    mock_geocoder_ip.return_value = mock_result

    location = get_location_from_ip()

    assert location is None


def test_get_location_from_env_success():
    with patch.dict('os.environ', {'USER_LATITUDE': '40.7128', 'USER_LONGITUDE': '-74.0060'}):
        location = get_location_from_env()
        assert location == (40.7128, -74.0060)


def test_get_location_from_env_not_set():
    with patch.dict('os.environ', {}, clear=True):
        location = get_location_from_env()
        assert location is None


def test_get_location_from_env_invalid_values():
    with patch.dict('os.environ', {'USER_LATITUDE': 'invalid', 'USER_LONGITUDE': 'invalid'}):
        location = get_location_from_env()
        assert location is None


@patch('src.features.location_service.get_location_from_ip')
@patch('src.features.location_service.get_location_from_env')
def test_get_device_location_from_env(mock_env, mock_ip):
    mock_env.return_value = (40.7128, -74.0060)
    mock_ip.return_value = (51.5074, -0.1278)

    location = get_device_location()

    assert location == (40.7128, -74.0060)
    mock_ip.assert_not_called()


@patch('src.features.location_service.get_location_from_ip')
@patch('src.features.location_service.get_location_from_env')
def test_get_device_location_fallback_to_ip(mock_env, mock_ip):
    mock_env.return_value = None
    mock_ip.return_value = (51.5074, -0.1278)

    location = get_device_location()

    assert location == (51.5074, -0.1278)
    mock_ip.assert_called_once()


@patch('src.features.location_service.get_location_from_ip')
@patch('src.features.location_service.get_location_from_env')
def test_get_device_location_no_fallback(mock_env, mock_ip):
    mock_env.return_value = None
    mock_ip.return_value = (51.5074, -0.1278)

    location = get_device_location(fallback_to_ip=False)

    assert location is None
    mock_ip.assert_not_called()


@patch('src.features.location_service.get_location_from_ip')
@patch('src.features.location_service.get_location_from_env')
def test_get_device_location_all_fail(mock_env, mock_ip):
    mock_env.return_value = None
    mock_ip.return_value = None

    location = get_device_location()

    assert location is None
