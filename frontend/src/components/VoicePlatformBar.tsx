import React, { useState, useRef, useEffect } from 'react';
import { 
  VolumeX, 
  AlertCircle,
  Settings
} from 'lucide-react';
import type { 
  RealtimeProvider, 
  RealtimeMode, 
  SessionConnectionStatus, 
  RealtimeTelemetry 
} from '../types/realtime';

interface VoicePlatformBarProps {
  status: SessionConnectionStatus;
  provider: RealtimeProvider;
  mode: RealtimeMode;
  isMuted: boolean;
  isRecording: boolean;
  telemetry: RealtimeTelemetry;
  errorMessage?: string | null;
  onToggleRecording: () => void;
  onInterrupt: () => void;
  onToggleMute: () => void;
  onSwitchProvider: (provider: RealtimeProvider) => void;
  onSetMode: (mode: RealtimeMode) => void;
  liveStreamingText?: string;
  liveLanguage?: string;
  onChangeLanguage?: (lang: string) => void;
  children?: React.ReactNode;
}

export const VoicePlatformBar: React.FC<VoicePlatformBarProps> = ({
  status,
  provider,
  mode,
  isMuted: _isMuted,
  isRecording,
  telemetry,
  errorMessage,
  onToggleRecording,
  onInterrupt,
  onToggleMute: _onToggleMute,
  onSwitchProvider,
  onSetMode,
  liveStreamingText: _liveStreamingText,
  liveLanguage = 'auto',
  onChangeLanguage,
  children
}) => {
  const isSpeaking = status === 'speaking';
  const isThinking = status === 'thinking';

  // Setting Popover State
  const [isSettingOpen, setIsSettingOpen] = useState(false);
  const settingRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (settingRef.current && !settingRef.current.contains(e.target as Node)) {
        setIsSettingOpen(false);
      }
    };
    if (isSettingOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isSettingOpen]);

  return (
    <div className="voice-platform-container">
      {/* Top Configuration Ribbon */}
      <div className="voice-platform-ribbon">
        {/* Unified Single Setting Button */}
        <div className="relative inline-block" ref={settingRef}>
          <button
            type="button"
            id="voice-setting-btn"
            className={`voice-setting-btn ${isSettingOpen ? 'active' : ''}`}
            onClick={() => setIsSettingOpen((prev) => !prev)}
            title="Pengaturan Engine & Mode Percakapan"
          >
            <Settings size={13} className="text-zinc-400" />
            <span>Setting</span>
          </button>

          {isSettingOpen && (
            <div className="voice-setting-popover">
              <div className="setting-popover-section">
                <span className="setting-popover-title">Engine Suara Real-Time</span>
                <div className="provider-tabs-group w-full justify-center">
                  <button
                    type="button"
                    className={`provider-tab-btn flex-1 justify-center ${provider === 'gemini_live' ? 'active' : ''}`}
                    onClick={() => {
                      onSwitchProvider('gemini_live');
                    }}
                  >
                    <span>Gemini</span>
                  </button>
                  <button
                    type="button"
                    className={`provider-tab-btn flex-1 justify-center ${provider === 'openai_realtime' ? 'active' : ''}`}
                    onClick={() => {
                      onSwitchProvider('openai_realtime');
                    }}
                  >
                    <span>ChatGPT</span>
                  </button>
                </div>
              </div>

              <div className="setting-popover-section">
                <span className="setting-popover-title">Mode Orkestrasi</span>
                <div className="mode-tabs-group w-full justify-center">
                  <button
                    type="button"
                    className={`mode-tab-btn flex-1 justify-center ${mode === 'live_conversation' ? 'active' : ''}`}
                    onClick={() => {
                      onSetMode('live_conversation');
                    }}
                    title="Mode A: Percakapan Langsung"
                  >
                    <span>Mode A</span>
                  </button>
                  <button
                    type="button"
                    className={`mode-tab-btn flex-1 justify-center ${mode === 'dual_intelligence' ? 'active' : ''}`}
                    onClick={() => {
                      onSetMode('dual_intelligence');
                    }}
                    title="Mode B: Dual Intelligence"
                  >
                    <span>Mode B</span>
                  </button>
                  <button
                    type="button"
                    className={`mode-tab-btn flex-1 justify-center ${mode === 'provider_handoff' ? 'active' : ''}`}
                    onClick={() => {
                      onSetMode('provider_handoff');
                    }}
                    title="Mode C: Provider Handoff"
                  >
                    <span>Mode C</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Telemetry HUD & Status Badge (Latency text removed per user instruction) */}
        <div className="telemetry-hud" title="Status Eksekusi Provider">
          {telemetry.providerStatus && (
            <div className="telemetry-item" title={telemetry.providerStatusDetail || telemetry.providerStatus}>
              {telemetry.providerStatus === 'native_connected' && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                  ● NATIVE LIVE
                </span>
              )}
              {telemetry.providerStatus === 'bridge_active' && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-blue-500/20 text-blue-300 border border-blue-500/40">
                  ⚡ FLASH BRIDGE
                </span>
              )}
              {telemetry.providerStatus === 'mock_active' && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  ⚠ MOCK FALLBACK
                </span>
              )}
              {telemetry.providerStatus === 'error' && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-rose-500/20 text-rose-300 border border-rose-500/40">
                  ✕ ERROR
                </span>
              )}
              {telemetry.providerStatus === 'connecting' && (
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase bg-zinc-700 text-zinc-300 animate-pulse">
                  CONNECTING
                </span>
              )}
            </div>
          )}
        </div>

        {/* Universal Multi-Language Auto-Detect & Selection */}
        {onChangeLanguage && (
          <div className="lang-toggle-group" title="Pilih Mode Bahasa Percakapan">
            <button
              type="button"
              className={`lang-toggle-btn ${liveLanguage === 'auto' ? 'active' : ''}`}
              onClick={() => onChangeLanguage('auto')}
              title="Auto-Detect: Deteksi otomatis semua bahasa dunia (Arab, Mandarin, Rusia, Inggris, Prancis, Jerman, Jepang, dll.)"
            >
              AUTO
            </button>
            <button
              type="button"
              className={`lang-toggle-btn ${liveLanguage === 'id-ID' ? 'active' : ''}`}
              onClick={() => onChangeLanguage('id-ID')}
              title="Bahasa Indonesia"
            >
              ID
            </button>
            <button
              type="button"
              className={`lang-toggle-btn ${liveLanguage === 'en-US' ? 'active' : ''}`}
              onClick={() => onChangeLanguage('en-US')}
              title="English"
            >
              EN
            </button>
            <select
              className="lang-select-dropdown"
              value={['auto', 'id-ID', 'en-US'].includes(liveLanguage) ? '' : liveLanguage}
              onChange={(e) => {
                if (e.target.value) {
                  onChangeLanguage(e.target.value);
                }
              }}
              title="Pilih Bahasa Internasional Khusus"
            >
              <option value="" disabled>
                {['auto', 'id-ID', 'en-US'].includes(liveLanguage) ? 'Lainnya ▾' : liveLanguage.split('-')[0].toUpperCase()}
              </option>
              <option value="zh-CN">🇨🇳 Mandarin (中文)</option>
              <option value="ar-SA">🇸🇦 Arab (العربية)</option>
              <option value="ru-RU">🇷🇺 Rusia (Русский)</option>
              <option value="fr-FR">🇫🇷 Prancis (Français)</option>
              <option value="de-DE">🇩🇪 Jerman (Deutsch)</option>
              <option value="ja-JP">🇯🇵 Jepang (日本語)</option>
              <option value="ko-KR">🇰🇷 Korea (한국어)</option>
              <option value="es-ES">🇪🇸 Spanyol (Español)</option>
              <option value="pt-BR">🇧🇷 Portugis (Português)</option>
              <option value="nl-NL">🇳🇱 Belanda (Nederlands)</option>
              <option value="tr-TR">🇹🇷 Turki (Türkçe)</option>
            </select>
          </div>
        )}
      </div>

      {/* Main Unified Card: Search Input and Voice Controls on the SAME SINGLE ROW */}
      <div className={`unified-live-bar ${isRecording ? 'active' : ''} ${isSpeaking ? 'ai-speaking' : ''}`}>
        {(isSpeaking || isThinking) && (
          <div className="unified-live-status-bar">
            <span className={`live-dot ${isSpeaking ? 'pulse-green' : ''}`} />
            <span>
              {isSpeaking
                ? 'AI Sedang Berbicara (Klik "Sela AI" atau bicara langsung untuk interupsi)'
                : 'Mensintesis Respons Suara Streaming...'}
            </span>
          </div>
        )}

        <div className="unified-live-single-row">
          {children && (
            <div className="unified-live-search-col">
              {children}
            </div>
          )}

          <div className="live-controls-right">
            {/* Instant Barge-In / Interrupt Button */}
            {isSpeaking && (
              <button
                type="button"
                className="bargein-action-btn"
                onClick={onInterrupt}
                title="Sela Pembicaraan AI Seketika (Barge-In)"
              >
                <VolumeX size={14} />
                <span>Sela AI</span>
              </button>
            )}

            {/* Live Waveform / Mic Stream Button */}
            <button
              type="button"
              className={`live-waveform-btn ${isSpeaking ? 'speaking' : (isRecording ? 'listening' : '')}`}
              onClick={onToggleRecording}
              aria-label="Toggle Live Voice"
              title={isRecording ? "Klik untuk Langsung Proses AI & Simpan Dokumen (Save Generate)" : "Mulai Percakapan Suara Real-Time (On Mic)"}
            >
              <div className="waveform-icon">
                <span className="wave-bar bar-1" />
                <span className="wave-bar bar-2" />
                <span className="wave-bar bar-3" />
                <span className="wave-bar bar-4" />
                <span className="wave-bar bar-5" />
              </div>
            </button>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="voice-error-banner">
          <AlertCircle size={13} className="text-amber-400" />
          <span>{errorMessage}</span>
        </div>
      )}
    </div>
  );
};
