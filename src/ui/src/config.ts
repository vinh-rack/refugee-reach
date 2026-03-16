// When served over HTTPS (production Docker), route API calls through the
// nginx reverse proxy at /api to avoid mixed-content blocks.
// In dev (plain HTTP on localhost), talk directly to the API on port 8000.
const isSecure = window.location.protocol === 'https:';
const apiHost = window.location.hostname;
const apiPort = import.meta.env.VITE_API_PORT || '8000';

export const API_BASE = import.meta.env.VITE_API_BASE
  || (isSecure
    ? `${window.location.origin}/api`
    : `http://${apiHost}:${apiPort}`);

const wsProtocol = isSecure ? 'wss' : 'ws';
export const WS_BASE = import.meta.env.VITE_WS_BASE
  || (isSecure
    ? `${wsProtocol}://${window.location.host}/api`
    : `${wsProtocol}://${apiHost}:${apiPort}`);
