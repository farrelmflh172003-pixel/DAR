export type RealtimeProvider = 'gemini_live' | 'openai_realtime';

export type RealtimeMode = 'live_conversation' | 'dual_intelligence' | 'provider_handoff';

export type SessionConnectionStatus = 
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'interrupted'
  | 'error';

export type ProviderExecutionStatus = 
  | 'disconnected'
  | 'connecting'
  | 'native_connected'
  | 'bridge_active'
  | 'mock_active'
  | 'error';

export interface RealtimeTelemetry {
  lastTurnLatencyMs: number;
  medianLatencyMs?: number;
  p95LatencyMs?: number;
  turnCount?: number;
  bargeInCount: number;
  lastBargeInMs: number;
  connectionTime: string;
  providerStatus?: ProviderExecutionStatus;
  providerStatusDetail?: string;
}

export interface RealtimeTranscriptItem {
  id: string;
  role: 'user' | 'assistant';
  provider: RealtimeProvider;
  text: string;
  timestamp: string;
}

export interface RealtimeSessionEvent {
  type: string;
  session_id?: string;
  provider?: RealtimeProvider;
  mode?: RealtimeMode;
  role?: string;
  delta?: string;
  text?: string;
  telemetry?: {
    last_turn_latency_ms: number;
    median_latency_ms?: number;
    p95_latency_ms?: number;
    turn_count?: number;
    barge_in_count: number;
    last_barge_in_ms: number;
  };
  barge_in_latency_ms?: number;
  provider_status?: string;
  provider_status_detail?: string;
  status?: string;
  detail?: string;
  details?: Record<string, any>;
  data?: Record<string, any>;
  message?: string;
}
