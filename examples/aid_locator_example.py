import os

from dotenv import load_dotenv

from src.features.aid_locator import find_aid_resources
from src.features.location_service import get_device_location

load_dotenv()


def main():
    user_location = get_device_location()

    if user_location:
        latitude, longitude = user_location
        print(f"Device Location Detected: {latitude:.4f}, {longitude:.4f}")
    else:
        latitude, longitude = 33.8938, 35.5018
        print(f"Using default location: Beirut, Lebanon ({latitude}, {longitude})")
    print("=" * 80)

    resources = find_aid_resources(
        latitude=latitude,
        longitude=longitude,
        radius_km=15,
        max_results=10
    )

    if not resources:
        print("No aid resources found in the area.")
        return

    print(f"\nFound {len(resources)} aid resources:\n")

    for i, resource in enumerate(resources, 1):
        print(f"{i}. {resource.name}")
        print(f"Type: {resource.type}")
        print(f"Distance: {resource.distance_km:.2f} km")
        print(f"Location: {resource.latitude:.6f}, {resource.longitude:.6f}")

        if resource.address:
            print(f"Address: {resource.address}")
        if resource.contact:
            print(f"Contact: {resource.contact}")
        if resource.hours:
            print(f"Hours: {resource.hours}")

        print(f"Source: {resource.source}")
        print()


if __name__ == "__main__":
    main()
