from dataclasses import dataclass
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
                    resources.append({
                        "name": tags.get("name", f"{tags.get('amenity', 'facility').title()}"),
                        "type": tags.get("amenity", "facility"),
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
