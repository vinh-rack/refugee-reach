"""
Simple standalone test for OpenRouteService API.
This script tests the API directly without requiring the full project setup.

Usage:
    python test_routing_simple.py

Or with API key as argument:
    python test_routing_simple.py YOUR_API_KEY_HERE
"""

import os
import sys

import requests
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()


def test_openrouteservice_api(api_key=None):
    """Test OpenRouteService API directly."""

    print("=" * 70)
    print("OpenRouteService API Test (Standalone)")
    print("=" * 70)

    # Get API key from argument, environment, or prompt
    if not api_key:
        api_key = os.getenv("OPENROUTESERVICE_API_KEY")

    if not api_key or api_key == "your_openrouteservice_api_key":
        print("\n⚠️  No API key provided!")
        print("\nOptions:")
        print("1. Add OPENROUTESERVICE_API_KEY to .env file")
        print("2. Run: python test_routing_simple.py YOUR_API_KEY")
        print("3. Get free API key: https://openrouteservice.org/dev/#/signup")
        print("\n📝 Testing with OSRM (free, no API key) instead...\n")
        test_osrm()
        return

    print(f"\n✓ Using API Key: {api_key[:10]}...{api_key[-4:]}\n")

    # Test coordinates: Ho Chi Minh City
    start_lon, start_lat = 106.7009, 10.7769  # District 1
    end_lon, end_lat = 106.6631, 10.7559      # Cho Ray Hospital

    print(f"📍 Test Route:")
    print(f"   From: {start_lat}, {start_lon} (District 1, HCMC)")
    print(f"   To:   {end_lat}, {end_lon} (Cho Ray Hospital)")
    print(f"\n⏳ Sending request to OpenRouteService...\n")

    try:
        response = requests.post(
            "https://api.openrouteservice.org/v2/directions/foot-walking",
            json={
                "coordinates": [[start_lon, start_lat], [end_lon, end_lat]],
                "instructions": True,
                "geometry": True,
                "elevation": False
            },
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json"
            },
            timeout=15
        )

        print(f"📡 Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            route = data["routes"][0]
            summary = route["summary"]

            print("\n" + "=" * 70)
            print("✅ SUCCESS! OpenRouteService is working!")
            print("=" * 70)

            print(f"\n📊 Route Details:")
            print(f"   Distance: {summary['distance'] / 1000:.2f} km")
            print(f"   Duration: {summary['duration'] / 60:.1f} minutes")

            # Count segments and steps
            total_steps = sum(len(seg.get("steps", [])) for seg in route.get("segments", []))
            print(f"   Navigation steps: {total_steps}")

            # Count polyline points
            polyline_points = len(route["geometry"]["coordinates"])
            print(f"   Polyline points: {polyline_points}")

            # Show first few steps
            print(f"\n🧭 First 3 Navigation Instructions:")
            step_count = 0
            for segment in route.get("segments", []):
                for step in segment.get("steps", []):
                    if step_count < 3:
                        instruction = step.get("instruction", "Continue")
                        distance = step.get("distance", 0)
                        print(f"   {step_count + 1}. {instruction} ({distance:.0f}m)")
                        step_count += 1

            # Show polyline sample
            print(f"\n📍 Route Polyline (first 3 coordinates):")
            for i, coord in enumerate(route["geometry"]["coordinates"][:3], 1):
                print(f"   {i}. Lon: {coord[0]:.6f}, Lat: {coord[1]:.6f}")

            print("\n" + "=" * 70)
            print("✅ Your OpenRouteService API key is working perfectly!")
            print("=" * 70)

            return True

        elif response.status_code == 401:
            print("\n" + "=" * 70)
            print("❌ AUTHENTICATION FAILED")
            print("=" * 70)
            print("\n🔑 Your API key is invalid or expired.")
            print("\nSteps to fix:")
            print("1. Go to: https://openrouteservice.org/dev/#/signup")
            print("2. Sign up or log in")
            print("3. Copy your API key")
            print("4. Update your .env file or run with the new key")
            return False

        elif response.status_code == 403:
            print("\n" + "=" * 70)
            print("❌ ACCESS FORBIDDEN")
            print("=" * 70)
            print("\n⚠️  Your API key doesn't have permission for this service.")
            print("   This might mean you've exceeded your rate limit.")
            print(f"\n   Free tier: 2000 requests/day")
            return False

        else:
            print("\n" + "=" * 70)
            print(f"❌ ERROR: HTTP {response.status_code}")
            print("=" * 70)
            print(f"\nResponse: {response.text[:500]}")
            return False

    except requests.exceptions.Timeout:
        print("\n❌ Request timed out. Check your internet connection.")
        return False

    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error. Check your internet connection.")
        return False

    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_osrm():
    """Test OSRM as a free alternative."""

    print("=" * 70)
    print("OSRM API Test (Free, No API Key Required)")
    print("=" * 70)

    # Test coordinates
    start_lon, start_lat = 106.7009, 10.7769
    end_lon, end_lat = 106.6631, 10.7559

    print(f"\n📍 Test Route:")
    print(f"   From: {start_lat}, {start_lon}")
    print(f"   To:   {end_lat}, {end_lon}")
    print(f"\n⏳ Sending request to OSRM...\n")

    try:
        response = requests.get(
            f"http://router.project-osrm.org/route/v1/foot/{start_lon},{start_lat};{end_lon},{end_lat}",
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "true"
            },
            timeout=15
        )

        print(f"📡 Response Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]

                print("\n" + "=" * 70)
                print("✅ SUCCESS! OSRM is working!")
                print("=" * 70)

                print(f"\n📊 Route Details:")
                print(f"   Distance: {route['distance'] / 1000:.2f} km")
                print(f"   Duration: {route['duration'] / 60:.1f} minutes")

                # Count steps
                total_steps = sum(len(leg.get("steps", [])) for leg in route.get("legs", []))
                print(f"   Navigation steps: {total_steps}")

                # Count polyline points
                polyline_points = len(route["geometry"]["coordinates"])
                print(f"   Polyline points: {polyline_points}")

                print("\n" + "=" * 70)
                print("✅ OSRM works! You can use routing without an API key.")
                print("=" * 70)

                return True

        print(f"\n❌ OSRM request failed: {data.get('message', 'Unknown error')}")
        return False

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False


def main():
    """Main test function."""

    print("\n🚀 Starting Routing Service Tests\n")

    # Check for API key in command line arguments
    api_key = sys.argv[1] if len(sys.argv) > 1 else None

    # Test OpenRouteService
    ors_success = test_openrouteservice_api(api_key)

    # If OpenRouteService failed and we haven't tested OSRM yet, test it
    if not ors_success and api_key:
        print("\n")
        test_osrm()

    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    if ors_success:
        print("\n✅ OpenRouteService: Working")
        print("   Your API key is valid and routing is functional.")
    else:
        print("\n⚠️  OpenRouteService: Not configured or failed")
        print("   But OSRM (free) can be used as fallback.")

    print("\n💡 Tip: For best results, get a free OpenRouteService API key:")
    print("   https://openrouteservice.org/dev/#/signup")
    print("   Free tier: 2000 requests/day\n")


if __name__ == "__main__":
    main()
