import React from 'react';

interface LiveVoiceButtonProps {
  title: string;
  service?: 'chatgpt' | 'gemini';
  isActive: boolean;
  onToggle: () => void;
  statusLabel?: string;
}

export const LiveVoiceButton: React.FC<LiveVoiceButtonProps> = ({
  title,
  isActive,
  onToggle,
  statusLabel
}) => {
  return (
    <div className={`live-voice-bar ${isActive ? 'active' : ''}`}>
      <div className="live-voice-info">
        <span className="live-voice-name">{title}</span>
        <span className="live-voice-status">
          <span className={`live-dot ${isActive ? 'pulse' : ''}`} />
          {statusLabel || (isActive ? 'Mendengarkan...' : 'Standby')}
        </span>
      </div>

      <button
        type="button"
        className={`live-waveform-btn ${isActive ? 'listening' : ''}`}
        onClick={onToggle}
        title={`${title}: ${isActive ? 'Hentikan Input Suara' : 'Aktifkan Live Suara'}`}
        aria-label={`${title} Voice Interaction`}
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
  );
};
