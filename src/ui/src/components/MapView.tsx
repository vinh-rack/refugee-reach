import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect, useRef, useState } from 'react';
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';
import { API_BASE } from '../config';

interface Location {
  latitude: number;
  longitude: number;
}

interface AidResource {
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  address?: string;
  contact?: string;
  hours?: string;
  source: string;
}

interface Route {
  total_distance_km: number;
  total_duration_min: number;
  polyline: [number, number][];
}

interface MapViewProps {
  userLocation: Location | null;
  resources: AidResource[];
  selectedResource: AidResource | null;
  onResourceSelect: (resource: AidResource | null) => void;
  onRefresh?: () => void;
  refreshing?: boolean;
}

const userIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const resourceIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const selectedResourceIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

function MapUpdater({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, 13);
  }, [center, map]);
  return null;
}

// Route cache: key = "lat1,lon1->lat2,lon2", value = Route
const routeCache = new Map<string, Route>();

function MapView({ userLocation, resources, selectedResource, onResourceSelect, onRefresh, refreshing }: MapViewProps) {
  const [route, setRoute] = useState<Route | null>(null);
  const [isLoadingRoute, setIsLoadingRoute] = useState(false);
  const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Clear any pending fetch
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
    }

    if (selectedResource && userLocation) {
      // Check cache first
      const cacheKey = `${userLocation.latitude.toFixed(4)},${userLocation.longitude.toFixed(4)}->${selectedResource.latitude.toFixed(4)},${selectedResource.longitude.toFixed(4)}`;
      const cachedRoute = routeCache.get(cacheKey);

      if (cachedRoute) {
        setRoute(cachedRoute);
        setIsLoadingRoute(false);
      } else {
        // Debounce route fetching (300ms delay)
        setIsLoadingRoute(true);
        fetchTimeoutRef.current = setTimeout(() => {
          fetchRoute(userLocation, selectedResource, cacheKey);
        }, 300);
      }
    } else {
      setRoute(null);
      setIsLoadingRoute(false);
    }

    return () => {
      if (fetchTimeoutRef.current) {
        clearTimeout(fetchTimeoutRef.current);
      }
    };
  }, [selectedResource, userLocation]);

  const fetchRoute = async (from: Location, to: AidResource, cacheKey: string) => {
    try {
      const response = await fetch(`${API_BASE}/route/to-resource`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_latitude: from.latitude,
          user_longitude: from.longitude,
          resource_latitude: to.latitude,
          resource_longitude: to.longitude
        })
      });

      const data = await response.json();
      if (data.success && data.route) {
        // Cache the route
        routeCache.set(cacheKey, data.route);
        setRoute(data.route);
      }
    } catch (error) {
      console.error('Failed to fetch route:', error);
    } finally {
      setIsLoadingRoute(false);
    }
  };

  if (!userLocation) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#888' }}>
        Loading location...
      </div>
    );
  }

  const center: [number, number] = [userLocation.latitude, userLocation.longitude];

  return (
    <>
      {onRefresh && (
        <button className="map-refresh-btn" onClick={onRefresh} title="Refresh Resources" disabled={refreshing}>
          <span className={refreshing ? 'spinning' : ''}>↻</span>
        </button>
      )}

      <MapContainer
        center={center}
        zoom={13}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
      >
        <MapUpdater center={center} />

        {/* Use CartoDB Positron for a clean, modern look similar to Google Maps */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          maxZoom={20}
        />

        <Marker position={center} icon={userIcon}>
          <Popup>Your Location</Popup>
        </Marker>

        {resources.map((resource, idx) => (
          <Marker
            key={idx}
            position={[resource.latitude, resource.longitude]}
            icon={selectedResource === resource ? selectedResourceIcon : resourceIcon}
            eventHandlers={{
              click: () => onResourceSelect(resource)
            }}
          >
            <Popup>
              <strong>{resource.name}</strong><br />
              Type: {resource.type}<br />
              Distance: {resource.distance_km.toFixed(2)} km
              {resource.address && <><br />Address: {resource.address}</>}
              {resource.contact && <><br />Contact: {resource.contact}</>}
            </Popup>
          </Marker>
        ))}

        {route && route.polyline && route.polyline.length > 0 && (
          <>
            <Polyline
              positions={route.polyline}
              color="#3b82f6"
              weight={5}
              opacity={0.8}
              smoothFactor={1}
              lineCap="round"
              lineJoin="round"
            />
            {/* Add a subtle shadow/outline for better visibility */}
            <Polyline
              positions={route.polyline}
              color="#1e3a8a"
              weight={7}
              opacity={0.3}
              smoothFactor={1}
              lineCap="round"
              lineJoin="round"
            />
          </>
        )}
      </MapContainer>

        <div className="resource-list">
          {selectedResource && (
            <div className="route-info">
              <div className="route-info-title">Route to {selectedResource.name}</div>
              {isLoadingRoute ? (
                <div className="route-info-details">
                  <span>Calculating route...</span>
                </div>
              ) : route ? (
                <div className="route-info-details">
                  <span>📍 {route.total_distance_km.toFixed(2)} km</span>
                  <span>⏱️ {Math.round(route.total_duration_min)} min</span>
                </div>
              ) : null}
            </div>
          )}
          {resources.slice(0, 5).map((resource, idx) => (
            <div
              key={idx}
              className={`resource-item ${selectedResource === resource ? 'selected' : ''}`}
              onClick={() => onResourceSelect(resource === selectedResource ? null : resource)}
            >
              <div>
                <div className="resource-name">{resource.name}</div>
                <div className="resource-type">{resource.type}</div>
              </div>
              <div className="resource-distance">{resource.distance_km.toFixed(2)} km</div>
            </div>
          ))}
        </div>
    </>
  );
}

export default MapView;
