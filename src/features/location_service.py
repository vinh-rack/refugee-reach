import os
from typing import Optional, Tuple

import geocoder


def get_location_from_ip() -> Optional[Tuple[float, float]]:
    """
    Get approximate location from IP address using geocoder library.

    Returns:
        Tuple of (latitude, longitude) or None if failed
    """
    try:
        g = geocoder.ip('me')
        if g.latlng is not None:
            return tuple(g.latlng)
    except Exception as e:
        print(f"Failed to get location from IP: {e}")
    return None


def get_location_from_env() -> Optional[Tuple[float, float]]:
    """
    Get location from environment variables.

    Returns:
        Tuple of (latitude, longitude) or None if not set
    """
    lat = os.getenv('USER_LATITUDE')
    lon = os.getenv('USER_LONGITUDE')

    if lat and lon:
        try:
            return (float(lat), float(lon))
        except ValueError:
            pass
    return None


def get_device_location(fallback_to_ip: bool = True) -> Optional[Tuple[float, float]]:
    """
    Get device location with multiple fallback strategies.

    Priority:
    1. Environment variables (USER_LATITUDE, USER_LONGITUDE)
    2. IP-based geolocation (if fallback_to_ip is True)

    Args:
        fallback_to_ip: Whether to use IP-based location as fallback

    Returns:
        Tuple of (latitude, longitude) or None if all methods fail
    """
    location = get_location_from_env()
    if location:
        return location

    if fallback_to_ip:
        location = get_location_from_ip()
        if location:
            return location

    return None
