import { useEffect, useState } from 'react';
import './App.css';
import ChatFrame from './components/ChatFrame';
import MapView from './components/MapView';
import SOSButton from './components/SOSButton';
import VoiceButton from './components/VoiceButton';

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

interface Notification {
  id: number;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

function App() {
  const [location, setLocation] = useState<Location | null>(null);
  const [resources, setResources] = useState<AidResource[]>([]);
  const [selectedResource, setSelectedResource] = useState<AidResource | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [sosActive, setSOSActive] = useState(false);
  const [mapVisible, setMapVisible] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchLocation();
  }, []);

  const addNotification = (type: Notification['type'], message: string) => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, type, message }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  const fetchLocation = async () => {
    // Try browser geolocation first — no timeout so the user can respond to the prompt
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          maximumAge: 60000
        });
      });
      setLocation({ latitude: pos.coords.latitude, longitude: pos.coords.longitude });
      console.log('Using device location');
      return;
    } catch (err: any) {
      // PERMISSION_DENIED = 1, POSITION_UNAVAILABLE = 2
      console.warn('Device geolocation unavailable, falling back to IP:', err?.message);
    }

    // Fallback to IP-based location only after user denied or device can't provide it
    try {
      const response = await fetch('http://localhost:8000/location');
      const data = await response.json();
      if (data.success) {
        setLocation({ latitude: data.latitude, longitude: data.longitude });
        console.log('Using IP-based location');
      }
    } catch (error) {
      console.error('Failed to fetch location:', error);
    }
  };

  const fetchNearbyResources = async (lat: number, lon: number) => {
    setRefreshing(true);
    try {
      const response = await fetch(
        `http://localhost:8000/aid/nearby?latitude=${lat}&longitude=${lon}&radius_km=10&max_results=10`
      );
      const data = await response.json();
      if (data.success) {
        setResources(data.resources);
        setMapVisible(true);
        console.log('Resources updated:', data.resources.length);
      }
    } catch (error) {
      console.error('Failed to fetch resources:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const refreshResources = () => {
    if (location) {
      fetchNearbyResources(location.latitude, location.longitude);
    }
  };

  const handleResourcesReceived = (agentResources: AidResource[]) => {
    console.log('Updating map with agent resources:', agentResources);
    setResources(agentResources);
    setMapVisible(true);
    addNotification('success', `Found ${agentResources.length} nearby resources`);
  };

  const handleSOSTriggered = (alert: any) => {
    console.log('SOS Alert triggered by agent:', alert);
    setSOSActive(true);
    const summary = alert.summary || 'Emergency detected';
    const urgency = alert.urgency_level || 'unknown';
    addNotification('error', `🚨 SOS Alert (${urgency}): ${summary}`);
    setTimeout(() => setSOSActive(false), 5000);
  };

  const handleToolCall = (toolCalls: any[]) => {
    console.log('Tool calls from agent:', toolCalls);
    toolCalls.forEach(call => {
      if (call.tool_name.includes('sos')) {
        addNotification('warning', 'Agent is analyzing emergency situation...');
      } else if (call.tool_name.includes('aid_locator')) {
        addNotification('info', 'Agent is searching for nearby resources...');
      }
    });
  };

  return (
    <div className="app">
      {/* Notification System */}
      <div className="notifications">
        {notifications.map(notif => (
          <div key={notif.id} className={`notification notification-${notif.type}`}>
            {notif.message}
          </div>
        ))}
      </div>

      <header className="app-header">
        <h1>RefugeeReach</h1>
        <p>Crisis Response & Aid Location</p>
      </header>

      <div className="main-content">
        <div className={`control-panel ${mapVisible ? 'map-open' : ''}`}>
          <SOSButton location={location} active={sosActive} />
          <VoiceButton
            location={location}
            onResourcesReceived={handleResourcesReceived}
            onSOSTriggered={handleSOSTriggered}
          />
          <ChatFrame
            location={location}
            onResourceRequest={refreshResources}
            onResourcesReceived={handleResourcesReceived}
            onSOSTriggered={handleSOSTriggered}
            onToolCall={handleToolCall}
            onToggleMap={() => setMapVisible(!mapVisible)}
            mapVisible={mapVisible}
          />
        </div>

        <div className={`map-sidebar ${mapVisible ? 'visible' : ''}`}>
          <button className="map-close-btn" onClick={() => setMapVisible(false)}>✕</button>
          <MapView
            userLocation={location}
            resources={resources}
            selectedResource={selectedResource}
            onResourceSelect={setSelectedResource}
            onRefresh={refreshResources}
            refreshing={refreshing}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
