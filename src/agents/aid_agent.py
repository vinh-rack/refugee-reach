from typing import Dict, List, Optional, Tuple

from strands import Agent, tool

from src.agents.nova_client import get_sos_model
from src.features.aid_locator import find_aid_resources

# Accumulator for captured resource results from tool calls
_captured_resources: List[Dict] = []


def get_captured_resources() -> List[Dict]:
    """Return and clear captured resources."""
    global _captured_resources
    result = list(_captured_resources)
    _captured_resources = []
    return result


def clear_captured_resources():
    """Clear captured resources."""
    global _captured_resources
    _captured_resources = []


@tool
def search_nearby_resources(
    latitude: float,
    longitude: float,
    radius_km: float = 15,
    max_results: int = 10
) -> Dict:
    """
    Search for nearby aid resources including hospitals, shelters, food, water, and refugee camps.

    Args:
        latitude: User's GPS latitude coordinate
        longitude: User's GPS longitude coordinate
        radius_km: Search radius in kilometers (default: 15)
        max_results: Maximum number of results to return (default: 10)

    Returns:
        Dictionary containing list of resources with details and count
    """
    resources = find_aid_resources(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        max_results=max_results
    )

    resources_list = [
        {
            "name": r.name,
            "type": r.type,
            "distance_km": round(r.distance_km, 2),
            "latitude": r.latitude,
            "longitude": r.longitude,
            "address": r.address,
            "contact": r.contact,
            "hours": r.hours,
            "source": r.source
        }
        for r in resources
    ]

    result = {
        "resources_found": len(resources_list),
        "resources": resources_list,
        "search_location": {"latitude": latitude, "longitude": longitude},
        "search_radius_km": radius_km
    }

    # Capture all resources for the API response
    _captured_resources.extend(resources_list)

    return result


@tool
def filter_resources_by_type(
    resources: List[Dict],
    resource_type: str
) -> List[Dict]:
    """
    Filter resources by specific type (hospital, clinic, shelter, food, water, refugee_camp).

    Args:
        resources: List of resource dictionaries from search_nearby_resources
        resource_type: Type to filter by (hospital, clinic, shelter, etc.)

    Returns:
        Filtered list of resources matching the type
    """
    filtered = [r for r in resources if resource_type.lower() in r.get("type", "").lower()]

    # If the agent filtered, replace captured resources with the filtered set
    if filtered:
        global _captured_resources
        _captured_resources = list(filtered)

    return filtered


def create_aid_locator_agent(model=None) -> Agent:
    """Create and configure the Aid Locator agent."""

    if model is None:
        model = get_sos_model()

    agent = Agent(
        tools=[search_nearby_resources, filter_resources_by_type],
        model=model
    )

    return agent
