import os

from dotenv import load_dotenv

from src.features.location_service import (get_device_location,
                                           get_location_from_env,
                                           get_location_from_ip)

load_dotenv()


def main():
    print("RefugeeReach - Location Service Demo")
    print("=" * 80)

    print("\n1. Checking environment variables...")
    env_location = get_location_from_env()
    if env_location:
        print(f"   Location from env: {env_location[0]:.4f}, {env_location[1]:.4f}")
    else:
        print("   No location set in environment variables")
        print("   Set USER_LATITUDE and USER_LONGITUDE in .env to use this method")

    print("\n2. Checking IP-based geolocation (using geocoder library)...")
    ip_location = get_location_from_ip()
    if ip_location:
        print(f"   Location from IP: {ip_location[0]:.4f}, {ip_location[1]:.4f}")
    else:
        print("   Failed to get location from IP")

    print("\n3. Getting device location (with fallback)...")
    device_location = get_device_location()
    if device_location:
        print(f"Device location: {device_location[0]:.4f}, {device_location[1]:.4f}")
    else:
        print("Failed to get device location")

    print("\n4. Getting device location (without IP fallback)...")
    device_location_no_fallback = get_device_location(fallback_to_ip=False)
    if device_location_no_fallback:
        print(f"Device location: {device_location_no_fallback[0]:.4f}, {device_location_no_fallback[1]:.4f}")
    else:
        print("No location available (env variables not set)")

    print("\n" + "=" * 80)
    print("Location Priority:")
    print("1. Environment variables (USER_LATITUDE, USER_LONGITUDE)")
    print("2. IP-based geolocation (approximate)")
    print("\nTo set your location, add to .env file:")
    print("USER_LATITUDE=40.7128")
    print("USER_LONGITUDE=-74.0060")


if __name__ == "__main__":
    main()
