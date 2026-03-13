"""Test route caching functionality"""
import time

from src.features.aid_locator import _get_route_cached, get_route_to_resource


def test_route_caching():
    """Test that route caching improves performance"""
    # Test coordinates (Berlin area)
    start_lat, start_lon = 52.5200, 13.4050
    end_lat, end_lon = 52.5300, 13.4150

    # First call - should take longer (actual API call)
    start_time = time.time()
    route1 = get_route_to_resource(start_lat, start_lon, end_lat, end_lon, api_key=None)
    first_call_time = time.time() - start_time

    # Second call with same coordinates - should be cached
    start_time = time.time()
    route2 = get_route_to_resource(start_lat, start_lon, end_lat, end_lon, api_key=None)
    second_call_time = time.time() - start_time

    # Cached call should be significantly faster
    print(f"First call: {first_call_time:.3f}s")
    print(f"Second call (cached): {second_call_time:.3f}s")
    print(f"Speedup: {first_call_time / second_call_time:.1f}x")

    assert route1 is not None
    assert route2 is not None
    assert second_call_time < first_call_time * 0.1  # Should be at least 10x faster

    # Verify routes are identical
    assert route1.total_distance_km == route2.total_distance_km
    assert route1.total_duration_min == route2.total_duration_min


def test_coordinate_rounding():
    """Test that similar coordinates use the same cache entry"""
    # Coordinates that differ by less than 0.0001 degrees (~11m)
    start_lat1, start_lon1 = 52.52001, 13.40501
    start_lat2, start_lon2 = 52.52009, 13.40509
    end_lat, end_lon = 52.5300, 13.4150

    route1 = get_route_to_resource(start_lat1, start_lon1, end_lat, end_lon, api_key=None)
    route2 = get_route_to_resource(start_lat2, start_lon2, end_lat, end_lon, api_key=None)

    # Should return same cached result due to rounding
    assert route1 is not None
    assert route2 is not None
    assert route1.total_distance_km == route2.total_distance_km


def test_cache_info():
    """Test cache statistics"""
    # Clear cache by accessing cache_info and cache_clear
    _get_route_cached.cache_clear()

    # Make some calls
    get_route_to_resource(52.5200, 13.4050, 52.5300, 13.4150, api_key=None)
    get_route_to_resource(52.5200, 13.4050, 52.5300, 13.4150, api_key=None)  # Cache hit
    get_route_to_resource(52.5200, 13.4050, 52.5400, 13.4250, api_key=None)  # Cache miss

    cache_info = _get_route_cached.cache_info()
    print(f"Cache stats: {cache_info}")

    assert cache_info.hits >= 1
    assert cache_info.misses >= 2


if __name__ == "__main__":
    print("Testing route caching...")
    test_route_caching()
    print("\nTesting coordinate rounding...")
    test_coordinate_rounding()
    print("\nTesting cache info...")
    test_cache_info()
    print("\nAll tests passed!")
