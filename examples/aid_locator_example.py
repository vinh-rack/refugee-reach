from src.agents.aid_locator import find_aid_resources


def main():
    latitude = 33.8938
    longitude = 35.5018

    print(f"Searching for aid resources near Beirut, Lebanon ({latitude}, {longitude})")
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
        print(f"   Type: {resource.type}")
        print(f"   Distance: {resource.distance_km:.2f} km")
        print(f"   Location: {resource.latitude:.6f}, {resource.longitude:.6f}")

        if resource.address:
            print(f"   Address: {resource.address}")
        if resource.contact:
            print(f"   Contact: {resource.contact}")
        if resource.hours:
            print(f"   Hours: {resource.hours}")

        print(f"   Source: {resource.source}")
        print()


if __name__ == "__main__":
    main()
