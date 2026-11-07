import { useState, useEffect, useRef, useCallback } from 'react';
import type { 
  RealtimeProvider, 
  RealtimeMode, 
  SessionConnectionStatus, 
  RealtimeTelemetry,
  RealtimeSessionEvent
} from '../types/realtime';
import { globalAudioStreamer } from '../services/audioStreamer';
import { API_BASE_URL, WS_BASE_URL } from '../config';

interface UseRealtimeSessionOptions {
  wsUrl?: string;
  defaultProvider?: RealtimeProvider;
  defaultMode?: RealtimeMode;
  onTranscriptDelta?: (role: 'user' | 'assistant', delta: string, provider: RealtimeProvider) => void;
  onTurnComplete?: (text?: string, telemetry?: any) => void;
}

export function useRealtimeSession(options: UseRealtimeSessionOptions = {}) {
  const {
    wsUrl = `${WS_BASE_URL}/ws/realtime-session`,
    defaultProvider = 'gemini_live',
    defaultMode = 'live_conversation',
    onTranscriptDelta,
    onTurnComplete
  } = options;

  const [status, setStatus] = useState<SessionConnectionStatus>('idle');
  const [provider, setProvider] = useState<RealtimeProvider>(defaultProvider);
  const [mode, setMode] = useState<RealtimeMode>(defaultMode);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [telemetry, setTelemetry] = useState<RealtimeTelemetry>({
    lastTurnLatencyMs: 0,
    bargeInCount: 0,
    lastBargeInMs: 0,
    connectionTime: ''
  });
  const [dualAnalysis, setDualAnalysis] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const isMutedRef = useRef<boolean>(false);
  const providerRef = useRef<RealtimeProvider>(defaultProvider);
  const fullAssistantTextRef = useRef<string>('');

  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  useEffect(() => {
    providerRef.current = provider;
  }, [provider]);

  const disconnectSession = useCallback(() => {
    globalAudioStreamer.instantBargeIn();
    globalAudioStreamer.stopCapture();
    setIsRecording(false);

    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {}
      wsRef.current = null;
    }
    setStatus('idle');
  }, []);

  const connectSession = useCallback(async (authToken?: string) => {
    disconnectSession();
    setStatus('connecting');
    setErrorMessage(null);

    try {
      // 1. Fetch short-lived single-use connection ticket to avoid credentials in WebSocket URL
      let ticketParam = '';
      try {
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        const token = authToken || (typeof window !== 'undefined' ? (localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')) : null);
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
        const ticketRes = await fetch(`${API_BASE_URL}/api/auth/ticket`, {
          method: 'POST',
          headers
        });
        if (ticketRes.ok) {
          const ticketData = await ticketRes.json();
          if (ticketData.ticket) {
            ticketParam = `ticket=${encodeURIComponent(ticketData.ticket)}`;
          }
        }
      } catch {
        // Backend development mode may allow fallback if auth ticket service is local
      }

      const separator = wsUrl.includes('?') ? '&' : '?';
      const targetUrl = ticketParam ? `${wsUrl}${separator}${ticketParam}` : wsUrl;

      const ws = new WebSocket(targetUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus('connected');
        setTelemetry(prev => ({ ...prev, connectionTime: new Date().toLocaleTimeString('id-ID') }));
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          // Binary audio PCM frame from provider
          setStatus('speaking');
          globalAudioStreamer.enqueuePcmChunk(event.data, () => {
            if (!globalAudioStreamer.getIsPlaying()) {
              setStatus('connected');
            }
          });
        } else if (typeof event.data === 'string') {
          try {
            const data: RealtimeSessionEvent = JSON.parse(event.data);
            if (data.type === 'session_created') {
              if (data.provider_status) {
                setTelemetry(prev => ({
                  ...prev,
                  providerStatus: data.provider_status as any,
                  providerStatusDetail: data.provider_status_detail
                }));
              }
            } else if (data.type === 'provider_status_changed') {
              setTelemetry(prev => ({
                ...prev,
                providerStatus: (data.status || data.provider_status) as any,
                providerStatusDetail: data.detail || data.provider_status_detail
              }));
            } else if (data.type === 'transcript_delta') {
              const delta = data.delta || '';
              if (data.role === 'assistant') {
                fullAssistantTextRef.current += delta;
              }
              onTranscriptDelta?.(
                (data.role as 'user' | 'assistant') || 'assistant',
                delta,
                data.provider || providerRef.current
              );
            } else if (data.type === 'turn_complete') {
              if (data.telemetry) {
                setTelemetry(prev => ({
                  ...prev,
                  lastTurnLatencyMs: data.telemetry?.last_turn_latency_ms || prev.lastTurnLatencyMs,
                  medianLatencyMs: data.telemetry?.median_latency_ms || prev.medianLatencyMs,
                  p95LatencyMs: data.telemetry?.p95_latency_ms || prev.p95LatencyMs,
                  turnCount: data.telemetry?.turn_count || prev.turnCount,
                  bargeInCount: data.telemetry?.barge_in_count || prev.bargeInCount,
                  lastBargeInMs: data.telemetry?.last_barge_in_ms || prev.lastBargeInMs
                }));
              }
              onTurnComplete?.(fullAssistantTextRef.current, data.telemetry);
              fullAssistantTextRef.current = '';
              if (!globalAudioStreamer.getIsPlaying()) {
                setStatus('connected');
              }
            } else if (data.type === 'interrupted') {
              const actualBargeMs = globalAudioStreamer.instantBargeIn();
              setStatus('interrupted');
              fullAssistantTextRef.current = '';
              setTelemetry(prev => ({
                ...prev,
                bargeInCount: prev.bargeInCount + 1,
                lastBargeInMs: data.barge_in_latency_ms || actualBargeMs || 15.0
              }));
              setTimeout(() => setStatus('connected'), 600);
            } else if (data.type === 'provider_switched') {
              if (data.provider) {
                setProvider(data.provider);
              }
              if (data.provider_status) {
                setTelemetry(prev => ({
                  ...prev,
                  providerStatus: data.provider_status as any,
                  providerStatusDetail: data.provider_status_detail
                }));
              }
            } else if (data.type === 'dual_analysis_result') {
              setDualAnalysis(data.data);
            } else if (data.type === 'session_timeout') {
              setErrorMessage(data.message || 'Sesi ditutup otomatis karena idle timeout.');
              setStatus('idle');
            } else if (data.type === 'error') {
              setErrorMessage(data.message || 'Error received from provider');
              if (data.provider_status) {
                setTelemetry(prev => ({
                  ...prev,
                  providerStatus: data.provider_status as any
                }));
              }
            }
          } catch {}
        }
      };

      ws.onerror = () => {
        setStatus('error');
        setErrorMessage('WebSocket connection to voice backend failed.');
      };

      ws.onclose = (event) => {
        if (event.code === 1008) {
          setStatus('error');
          setErrorMessage(`Akses Ditolak (Policy Violation / 1008): ${event.reason || 'Otorisasi atau tiket gagal.'}`);
        } else {
          setStatus('idle');
        }
      };
    } catch (err: any) {
      setStatus('error');
      setErrorMessage(err.message || 'Failed to initialize WebSocket');
    }
  }, [wsUrl, disconnectSession, onTranscriptDelta, onTurnComplete]);

  // Barge-In: Cut off AI speech immediately and inform server
  const interruptPlayback = useCallback(() => {
    globalAudioStreamer.instantBargeIn();
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'interrupt' }));
    }
    setStatus('interrupted');
    setTimeout(() => setStatus('connected'), 400);
  }, []);

  useEffect(() => {
    return () => {
      disconnectSession();
    };
  }, [disconnectSession]);

  // Toggle Microphone Audio Streaming
  const toggleRecording = useCallback(async (speechText?: string) => {
    if (isRecording) {
      // User ends speech turn
      globalAudioStreamer.stopCapture();
      setIsRecording(false);
      setStatus('thinking');
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ 
          type: 'user_speech_end',
          text: speechText?.trim() || undefined
        }));
      }
      return;
    }

    // Connect session if not yet open
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectSession();
      await new Promise(r => setTimeout(r, 400));
    }

    // Barge-in if AI is currently playing
    if (globalAudioStreamer.getIsPlaying()) {
      interruptPlayback();
    }

    try {
      setIsRecording(true);
      setStatus('listening');
      fullAssistantTextRef.current = '';

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'user_speech_start' }));
      }

      await globalAudioStreamer.startCapture((pcmChunk) => {
        if (!isMutedRef.current && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(pcmChunk.buffer as ArrayBuffer);
        }
      });

    } catch (_err: any) {
      setIsRecording(false);
      setStatus('error');
      setErrorMessage('Microphone access denied or audio device unavailable.');
    }
  }, [isRecording, connectSession, interruptPlayback]);

  // Mode C: Provider Handoff
  const switchProvider = useCallback((newProvider: RealtimeProvider) => {
    interruptPlayback();
    setProvider(newProvider);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'switch_provider',
        provider: newProvider
      }));
    }
  }, [interruptPlayback]);

  // Send Text into Live Turn
  const sendUserText = useCallback((text: string) => {
    if (!text.trim()) return;
    interruptPlayback();
    setStatus('thinking');
    fullAssistantTextRef.current = '';

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectSession();
      setTimeout(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: 'user_speech_end', text: text.trim() }));
        }
      }, 500);
    } else {
      wsRef.current.send(JSON.stringify({ type: 'user_speech_end', text: text.trim() }));
    }
  }, [connectSession, interruptPlayback]);

  // Mode B: Request Dual Analysis
  const requestDualAnalysis = useCallback((query: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'request_dual_analysis',
        query
      }));
    }
  }, []);

  return {
    status,
    provider,
    mode,
    isMuted,
    isRecording,
    telemetry,
    dualAnalysis,
    errorMessage,
    setIsMuted,
    setMode,
    connectSession,
    disconnectSession,
    toggleRecording,
    interruptPlayback,
    switchProvider,
    sendUserText,
    requestDualAnalysis
  };
}
