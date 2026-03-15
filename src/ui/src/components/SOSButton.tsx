import { useEffect, useState } from 'react';

interface SOSButtonProps {
  location: { latitude: number; longitude: number } | null;
  active?: boolean;
  onSOSTriggered?: (alert: { summary: string; urgency_level: string }) => void;
}

type SOSStatus = 'idle' | 'sending' | 'sent' | 'error';

function SOSButton({ location, active, onSOSTriggered }: SOSButtonProps) {
  const [status, setStatus] = useState<SOSStatus>('idle');
  const [message, setMessage] = useState('');

  // React to external SOS trigger (from agent)
  useEffect(() => {
    if (active && status === 'idle') {
      setStatus('sent');
      setMessage('SOS triggered by agent!');
      setTimeout(() => {
        setStatus('idle');
        setMessage('');
      }, 3000);
    }
  }, [active, status]);

  const sendSOS = async () => {
    console.log('[SOS] Button clicked. Current location:', location);

    if (!location) {
      console.warn('[SOS] Aborted — location not available');
      setMessage('Location not available');
      return;
    }

    setStatus('sending');
    setMessage('Sending SOS signal...');
    console.log('[SOS] Sending request to /sos with:', { latitude: location.latitude, longitude: location.longitude });

    try {
      const response = await fetch('http://localhost:8000/sos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: location.latitude,
          longitude: location.longitude
        })
      });

      console.log('[SOS] Response status:', response.status, response.statusText);
      const data = await response.json();
      console.log('[SOS] Response body:', data);

      if (data.success) {
        console.log('[SOS] Success — SOS sent');
        setStatus('sent');
        setMessage('SOS sent successfully!');
        onSOSTriggered?.({ summary: 'Emergency SOS signal sent', urgency_level: 'critical' });
        setTimeout(() => {
          setStatus('idle');
          setMessage('');
        }, 3000);
      } else {
        console.error('[SOS] Server returned failure:', data);
        setStatus('error');
        setMessage('Failed to send SOS');
      }
    } catch (error) {
      console.error('[SOS] Network/fetch error:', error);
      setStatus('error');
      setMessage('Network error');
      onSOSTriggered?.({ summary: 'Failed to send SOS — network error', urgency_level: 'error' });
    }
  };

  return (
    <div className="panel-section">
      <h2>Emergency</h2>
      <button
        className={`sos-button ${status}`}
        onClick={sendSOS}
        disabled={status === 'sending'}
      >
        {status === 'sending' ? 'SENDING...' : status === 'sent' ? 'SOS SENT ✓' : 'SOS'}
      </button>
      {message && <div className="sos-status">{message}</div>}
    </div>
  );
}

export default SOSButton;
