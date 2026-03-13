import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.features.aid_locator import get_route_to_resource

# Load environment variables
load_dotenv()


def test_openrouteservice():
    """Test OpenRouteService routing with sample coordinates."""

    print("=" * 60)
    print("OpenRouteService Routing Test")
    print("=" * 60)

    # Get API key
    api_key = os.getenv("OPENROUTESERVICE_API_KEY")

    if not api_key or api_key == "your_openrouteservice_api_key":
        print("\nWARNING: No valid OpenRouteService API key found!")
        print("   The test will use OSRM (free) as fallback.\n")
        print("   To test OpenRouteService:")
        print("   1. Sign up at: https://openrouteservice.org/dev/#/signup")
        print("   2. Add your API key to .env file")
        print("   3. Run this test again\n")
        api_key = None
    else:
        print(f"\n✓ API Key found: {api_key[:10]}...{api_key[-4:]}")

    # Test coordinates (Ho Chi Minh City example)
    # From: District 1 center
    start_lat = 10.7769
    start_lon = 106.7009

    # To: Bệnh viện Chợ Rẫy (Cho Ray Hospital)
    end_lat = 10.7559
    end_lon = 106.6631

    print(f"\n📍 Test Route:")
    print(f"   From: {start_lat}, {start_lon} (District 1)")
    print(f"   To:   {end_lat}, {end_lon} (Cho Ray Hospital)")
    print(f"\n⏳ Calculating route...\n")

    try:
        route = get_route_to_resource(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            api_key=api_key
        )

        if route:
            print("=" * 60)
            print("✅ SUCCESS! Route calculated successfully")
            print("=" * 60)

            print(f"\n📊 Route Summary:")
            print(f"   Distance: {route.total_distance_km:.2f} km")
            print(f"   Duration: {route.total_duration_min:.1f} minutes")
            print(f"   Steps: {len(route.steps)} navigation steps")
            print(f"   Polyline points: {len(route.polyline)} coordinates")

            # Determine which service was used
            if len(route.polyline) > 2:
                if api_key:
                    print(f"\n🌐 Service Used: OpenRouteService (API)")
                else:
                    print(f"\n🌐 Service Used: OSRM (Free)")
                print("   ✓ Detailed road-following route")
            else:
                print(f"\n🌐 Service Used: Fallback (Straight line)")
                print("   ⚠️  Both routing services failed")

            # Show first few navigation steps
            if route.steps and len(route.steps) > 0:
                print(f"\n🧭 First 3 Navigation Steps:")
                for i, step in enumerate(route.steps[:3], 1):
                    print(f"   {i}. {step.instruction}")
                    print(f"      Distance: {step.distance_m:.0f}m, Duration: {step.duration_s:.0f}s")

                if len(route.steps) > 3:
                    print(f"   ... and {len(route.steps) - 3} more steps")

            # Show polyline sample
            print(f"\n📍 Route Polyline (first 3 points):")
            for i, point in enumerate(route.polyline[:3], 1):
                print(f"   {i}. Lat: {point[0]:.6f}, Lon: {point[1]:.6f}")
            if len(route.polyline) > 3:
                print(f"   ... and {len(route.polyline) - 3} more points")

            print("\n" + "=" * 60)
            print("✅ Test completed successfully!")
            print("=" * 60)

            return True
        else:
            print("=" * 60)
            print("❌ FAILED: Route calculation returned None")
            print("=" * 60)
            return False

    except Exception as e:
        print("=" * 60)
        print(f"❌ ERROR: {str(e)}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


def test_multiple_routes():
    """Test multiple routes to verify consistency."""

    print("\n\n" + "=" * 60)
    print("Testing Multiple Routes")
    print("=" * 60)

    api_key = os.getenv("OPENROUTESERVICE_API_KEY")
    if api_key == "your_openrouteservice_api_key":
        api_key = None

    test_cases = [
        {
            "name": "Short distance (1km)",
            "start": (10.7769, 106.7009),
            "end": (10.7800, 106.7050)
        },
        {
            "name": "Medium distance (3km)",
            "start": (10.7769, 106.7009),
            "end": (10.7559, 106.6631)
        },
        {
            "name": "Long distance (10km)",
            "start": (10.7769, 106.7009),
            "end": (10.8231, 106.6297)
        }
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   From: {test['start']}")
        print(f"   To:   {test['end']}")

        try:
            route = get_route_to_resource(
                start_lat=test['start'][0],
                start_lon=test['start'][1],
                end_lat=test['end'][0],
                end_lon=test['end'][1],
                api_key=api_key
            )

            if route:
                print(f"   ✓ Distance: {route.total_distance_km:.2f} km")
                print(f"   ✓ Duration: {route.total_duration_min:.1f} min")
                print(f"   ✓ Polyline points: {len(route.polyline)}")
                results.append(True)
            else:
                print(f"   ✗ Failed to calculate route")
                results.append(False)

        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            results.append(False)

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    return all(results)


if __name__ == "__main__":
    print("\n🚀 Starting OpenRouteService Tests\n")

    # Run basic test
    basic_success = test_openrouteservice()

    # Run multiple routes test
    if basic_success:
        multiple_success = test_multiple_routes()

        if multiple_success:
            print("\n\n🎉 All tests passed! Your routing system is working perfectly.")
        else:
            print("\n\n⚠️  Some tests failed. Check the output above for details.")
    else:
        print("\n\n❌ Basic test failed. Fix the issues above before running more tests.")

    print("\n")
