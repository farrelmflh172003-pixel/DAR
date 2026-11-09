/**
 * Dynamic configuration for API and WebSocket endpoints.
 * Automatically adapts between local development, custom host, and production deployment.
 */

export const getApiBaseUrl = (): string => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '');
  }
  
  if (typeof window !== 'undefined') {
    // If running on Capacitor native Android app
    if (window.location.protocol === 'capacitor:' || (window.location.protocol === 'http:' && window.location.hostname === 'localhost' && !window.location.port)) {
      const customUrl = localStorage.getItem('dialogue_ai_server_url');
      if (customUrl) return customUrl.replace(/\/$/, '');
      return 'http://192.168.20.22:8000';
    }

    // If running on Vite dev server (port 5173 / 3000), backend is on port 8000 of the same host
    if (window.location.port === '5173' || window.location.port === '3000') {
      return `${window.location.protocol}//${window.location.hostname}:8000`;
    }
    // If running production build served by FastAPI or reverse proxy, use current origin
    return window.location.origin;
  }
  return 'http://127.0.0.1:8000';
};

export const getWsBaseUrl = (): string => {
  if (import.meta.env.VITE_WS_BASE_URL) {
    return import.meta.env.VITE_WS_BASE_URL.replace(/\/$/, '');
  }

  if (typeof window !== 'undefined') {
    // If running on Capacitor native Android app
    if (window.location.protocol === 'capacitor:' || (window.location.protocol === 'http:' && window.location.hostname === 'localhost' && !window.location.port)) {
      const customUrl = localStorage.getItem('dialogue_ai_server_url');
      if (customUrl) {
        return customUrl.replace(/^http/i, 'ws').replace(/\/$/, '');
      }
      return 'ws://192.168.20.22:8000';
    }

    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (window.location.port === '5173' || window.location.port === '3000') {
      return `${wsProto}//${window.location.hostname}:8000`;
    }
    return `${wsProto}//${window.location.host}`;
  }
  return 'ws://127.0.0.1:8000';
};

export const API_BASE_URL = getApiBaseUrl();
export const WS_BASE_URL = getWsBaseUrl();

