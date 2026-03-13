from dataclasses import dataclass
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from typing import Dict, List, Optional, Tuple

import requests


@dataclass
class AidResource:
    name: str
    type: str
    latitude: float
    longitude: float
    distance_km: float
    address: Optional[str] = None
    contact: Optional[str] = None
    hours: Optional[str] = None
    source: str = "unknown"


@dataclass
class RouteStep:
    instruction: str
    distance_m: float
    duration_s: float
    latitude: float
    longitude: float


@dataclass
class Route:
    total_distance_km: float
    total_duration_min: float
    steps: List[RouteStep]
    polyline: List[Tuple[float, float]]

    @dataclass
    class RouteStep:
        instruction: str
        distance_m: float
        duration_s: float
        latitude: float
        longitude: float


    @dataclass
    class Route:
        total_distance_km: float
        total_duration_min: float
        steps: List[RouteStep]
        polyline: List[Tuple[float, float]]


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return c * r


def query_unhcr_camps(latitude: float, longitude: float, radius_km: float = 50) -> List[Dict]:
    camps = []

    try:
        # query from UNHCR's open source API
        response = requests.get(
            "https://data.unhcr.org/api/population/regional.json",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            for camp in data.get("data", []):
                if "latitude" in camp and "longitude" in camp:
                    distance = calculate_distance(
                        latitude, longitude,
                        float(camp["latitude"]), float(camp["longitude"])
                    )
                    if distance <= radius_km:
                        camps.append({
                            "name": camp.get("name", "UNHCR Camp"),
                            "type": "refugee_camp",
                            "latitude": float(camp["latitude"]),
                            "longitude": float(camp["longitude"]),
                            "distance_km": distance,
                            "source": "UNHCR"
                        })
    except Exception:
        pass

    return camps


def query_openstreetmap(latitude: float, longitude: float, radius_km: float = 10) -> List[Dict]:
    resources = []
    amenities = ["hospital", "clinic", "doctors", "pharmacy", "drinking_water", "shelter"]

    radius_m = radius_km * 1000

    # Overpass API to query OpenStreetMap data
    overpass_url = "https://overpass-api.de/api/interpreter"

    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"{'|'.join(amenities)}"](around:{radius_m},{latitude},{longitude});
      way["amenity"~"{'|'.join(amenities)}"](around:{radius_m},{latitude},{longitude});
    );
    out center;
    """

    try:
        response = requests.post(overpass_url, data={"data": query}, timeout=30)

        if response.status_code == 200:
            data = response.json()

            for element in data.get("elements", []):
                tags = element.get("tags", {})
                elem_id = element.get("id", "")
                if element.get("type") == "node":
                    elem_lat = element.get("lat")
                    elem_lon = element.get("lon")
                elif element.get("center"):
                    elem_lat = element["center"].get("lat")
                    elem_lon = element["center"].get("lon")
                else:
                    continue

                if elem_lat and elem_lon:
                    distance = calculate_distance(latitude, longitude, elem_lat, elem_lon)

                    # Generate a better name if no name tag exists
                    amenity_type = tags.get("amenity", "facility")
                    if "name" in tags and tags["name"]:
                        resource_name = tags["name"]
                    else:
                        # Create a more descriptive name using available tags
                        type_label = amenity_type.replace("_", " ").title()

                        # Try to add location context
                        street = tags.get("addr:street") or tags.get("addr:full")
                        if street:
                            resource_name = f"{type_label} on {street}"
                        else:
                            # Use operator or brand if available
                            operator = tags.get("operator") or tags.get("brand")
                            if operator:
                                resource_name = f"{operator} ({type_label})"
                            else:
                                # Last resort: add unique identifier using OSM ID
                                resource_name = f"{type_label} #{elem_id}"

                    resources.append({
                        "name": resource_name,
                        "type": amenity_type,
                        "latitude": elem_lat,
                        "longitude": elem_lon,
                        "distance_km": distance,
                        "address": tags.get("addr:full") or tags.get("addr:street"),
                        "contact": tags.get("phone") or tags.get("contact:phone"),
                        "hours": tags.get("opening_hours"),
                        "source": "OpenStreetMap"
                    })
    except Exception:
        pass

    return resources


def find_aid_resources(
    latitude: float,
    longitude: float,
    radius_km: float = 10,
    max_results: int = 20
) -> List[AidResource]:
    all_resources = []

    osm_resources = query_openstreetmap(latitude, longitude, radius_km)
    all_resources.extend(osm_resources)

    unhcr_camps = query_unhcr_camps(latitude, longitude, radius_km * 5)
    all_resources.extend(unhcr_camps)

    sorted_resources = sorted(all_resources, key=lambda x: x["distance_km"])

    aid_resources = []
    for resource in sorted_resources[:max_results]:
        aid_resources.append(AidResource(
            name=resource["name"],
            type=resource["type"],
            latitude=resource["latitude"],
            longitude=resource["longitude"],
            distance_km=resource["distance_km"],
            address=resource.get("address"),
            contact=resource.get("contact"),
            hours=resource.get("hours"),
            source=resource["source"]
        ))

    return aid_resources


@lru_cache(maxsize=128)
def _get_route_cached(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    api_key: Optional[str] = None
) -> Optional[Route]:
    """
    Cached route calculation. Rounds coordinates to 4 decimal places (~11m precision).
    """
    return _calculate_route(start_lat, start_lon, end_lat, end_lon, api_key)


def _calculate_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    api_key: Optional[str] = None
) -> Optional[Route]:
    """
    Get detailed walking route from start to end location.
    Tries OpenRouteService first, then OSRM (free, no API key), falls back to straight line.
    """
    straight_line_distance = calculate_distance(start_lat, start_lon, end_lat, end_lon)

    # Try OpenRouteService if API key is provided
    if api_key:
        try:
            response = requests.post(
                "https://api.openrouteservice.org/v2/directions/foot-walking/geojson",
                json={
                    "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
                    "instructions": True,
                    "elevation": False
                },
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json"
                },
                timeout=10
            )

            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception as json_error:
                    print(f"OpenRouteService JSON parse error: {json_error}")
                    print(f"Response text: {response.text[:500]}")
                    raise

                # GeoJSON format returns features array
                if isinstance(data, dict) and "features" in data and data["features"]:
                    feature = data["features"][0]
                    route_props = feature.get("properties", {})
                    geometry = feature.get("geometry", {})

                    # Extract summary
                    summary = route_props.get("summary", {})
                    total_distance = summary.get("distance", 0)
                    total_duration = summary.get("duration", 0)

                    # Extract steps
                    steps = []
                    segments = route_props.get("segments", [])
                    for segment in segments:
                        for step in segment.get("steps", []):
                            steps.append(RouteStep(
                                instruction=step.get("instruction", "Continue"),
                                distance_m=step.get("distance", 0),
                                duration_s=step.get("duration", 0),
                                latitude=0,  # Will be filled from geometry if needed
                                longitude=0
                            ))

                    # Extract polyline from geometry
                    polyline = []
                    if geometry.get("type") == "LineString" and geometry.get("coordinates"):
                        polyline = [
                            (coord[1], coord[0])  # Convert from [lon, lat] to (lat, lon)
                            for coord in geometry["coordinates"]
                        ]

                    return Route(
                        total_distance_km=total_distance / 1000,
                        total_duration_min=total_duration / 60,
                        steps=steps,
                        polyline=polyline
                    )
                else:
                    print(f"OpenRouteService invalid GeoJSON structure")
                    print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                    raise ValueError("Invalid GeoJSON structure")
            else:
                print(f"OpenRouteService error: {response.status_code}")
                if response.text:
                    print(f"Response: {response.text[:200]}")
        except ValueError as ve:
            print(f"OpenRouteService validation error: {ve}")
        except Exception as e:
            print(f"OpenRouteService request failed: {e}")

    # Skip OSRM if we have an API key (it's timing out and we prefer OpenRouteService)
    # Only try OSRM if no API key is provided
    if not api_key:
        # Try OSRM (free, no API key required) - reduced timeout
        try:
            response = requests.get(
                f"http://router.project-osrm.org/route/v1/foot/{start_lon},{start_lat};{end_lon},{end_lat}",
                params={
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "true"
                },
                timeout=5  # Reduced from 15 to 5 seconds
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    route_data = data["routes"][0]

                    # Extract steps
                    steps = []
                    for leg in route_data.get("legs", []):
                        for step in leg.get("steps", []):
                            location = step.get("maneuver", {}).get("location", [])
                            if location:
                                steps.append(RouteStep(
                                    instruction=step.get("maneuver", {}).get("instruction", "Continue"),
                                    distance_m=step.get("distance", 0),
                                    duration_s=step.get("duration", 0),
                                    latitude=location[1],
                                    longitude=location[0]
                                ))

                    # Convert geometry to polyline
                    geometry = route_data.get("geometry", {})
                    if geometry and geometry.get("coordinates"):
                        polyline = [
                            (coord[1], coord[0])  # Convert from [lon, lat] to (lat, lon)
                            for coord in geometry["coordinates"]
                        ]
                    else:
                        polyline = [(start_lat, start_lon), (end_lat, end_lon)]

                    return Route(
                        total_distance_km=route_data.get("distance", 0) / 1000,
                        total_duration_min=route_data.get("duration", 0) / 60,
                        steps=steps,
                        polyline=polyline
                    )
        except Exception as e:
            print(f"OSRM request failed: {e}")

    # Fallback: Return straight line route
    print("Using straight-line fallback route")
    return Route(
        total_distance_km=straight_line_distance,
        total_duration_min=straight_line_distance / 5 * 60,  # Assume 5 km/h walking speed
        steps=[
            RouteStep(
                instruction=f"Walk approximately {straight_line_distance:.2f} km to destination",
                distance_m=straight_line_distance * 1000,
                duration_s=straight_line_distance / 5 * 3600,
                latitude=end_lat,
                longitude=end_lon
            )
        ],
        polyline=[(start_lat, start_lon), (end_lat, end_lon)]
    )


def get_route_to_resource(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    api_key: Optional[str] = None
) -> Optional[Route]:
    """
    Get route with caching. Rounds coordinates to 4 decimal places for cache efficiency.
    """
    # Round to 4 decimal places (~11m precision) for better cache hits
    start_lat_rounded = round(start_lat, 4)
    start_lon_rounded = round(start_lon, 4)
    end_lat_rounded = round(end_lat, 4)
    end_lon_rounded = round(end_lon, 4)

    return _get_route_cached(
        start_lat_rounded,
        start_lon_rounded,
        end_lat_rounded,
        end_lon_rounded,
        api_key
    )


def map_route_to_aid_resource(
    user_lat: float,
    user_lon: float,
    resource: AidResource,
    api_key: Optional[str] = None
) -> Optional[Route]:
    return get_route_to_resource(
        user_lat,
        user_lon,
        resource.latitude,
        resource.longitude,
        api_key
    )
