import { useEffect, useState } from 'react';

interface SOSButtonProps {
  location: { latitude: number; longitude: number } | null;
  active?: boolean;
}

type SOSStatus = 'idle' | 'sending' | 'sent' | 'error';

function SOSButton({ location, active }: SOSButtonProps) {
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
    if (!location) {
      setMessage('Location not available');
      return;
    }

    setStatus('sending');
    setMessage('Sending SOS signal...');

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `EMERGENCY SOS - I need immediate help at coordinates ${location.latitude}, ${location.longitude}`
        })
      });

      const data = await response.json();

      if (data.success) {
        setStatus('sent');
        setMessage('SOS sent successfully!');
        setTimeout(() => {
          setStatus('idle');
          setMessage('');
        }, 3000);
      } else {
        setStatus('error');
        setMessage('Failed to send SOS');
      }
    } catch (error) {
      setStatus('error');
      setMessage('Network error');
      console.error('SOS error:', error);
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
