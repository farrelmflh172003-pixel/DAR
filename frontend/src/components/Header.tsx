import React from 'react';
import type { User } from '../types/auth';

export type ViewMode = 'split' | 'assistant' | 'prompter';

interface HeaderProps {
  viewMode?: ViewMode;
  onViewModeChange?: (mode: ViewMode) => void;
  currentUser?: User | null;
  onOpenLogin?: () => void;
  onLogout?: () => void;
  savedFilesCount?: number;
  onOpenSavedFiles?: () => void;
  onNewFile?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  viewMode = 'split',
  onViewModeChange,
  currentUser,
  onOpenLogin,
  onLogout,
  savedFilesCount = 0,
  onOpenSavedFiles,
  onNewFile: _onNewFile
}) => {
  return (
    <header className="official-header">
      <div className="official-header-brand">
        <img
          src="/Kemenkopolkam.webp"
          alt="Kemenko Polkam Logo"
          className="official-logo-img"
        />
        <div className="brand-text-col">
          <h1 className="official-title">MENKOPOLKAM AI HUB</h1>
          <span className="official-subtitle-badge">Kemenko Polkam RI</span>
        </div>
      </div>

      <div className="official-header-center">
        {onViewModeChange && (
          <div className="view-mode-selector">
            <button
              type="button"
              id="view-mode-split"
              className={`view-mode-pill ${viewMode === 'split' ? 'active' : ''}`}
              onClick={() => onViewModeChange('split')}
              title="Tampilkan Split Screen (Asisten AI & Prompter Dokumen)"
            >
              <span>Split</span>
            </button>
            <button
              type="button"
              id="view-mode-assistant"
              className={`view-mode-pill ${viewMode === 'assistant' ? 'active' : ''}`}
              onClick={() => onViewModeChange('assistant')}
              title="Tampilkan Layar Penuh Asisten AI"
            >
              <span>AI & Translator</span>
            </button>
            <button
              type="button"
              id="view-mode-prompter"
              className={`view-mode-pill ${viewMode === 'prompter' ? 'active' : ''}`}
              onClick={() => onViewModeChange('prompter')}
              title="Tampilkan Layar Penuh Prompter Naskah"
            >
              <span>Prompter</span>
            </button>
            {onOpenSavedFiles && (
              <button
                type="button"
                id="view-mode-saved-files"
                className="view-mode-pill"
                onClick={onOpenSavedFiles}
                title="Buka List Pertanyaan (View, Edit, Delete)"
              >
                <span>List Pertanyaan</span>
                {savedFilesCount > 0 && (
                  <span className="header-saved-count">{savedFilesCount}</span>
                )}
              </button>
            )}
          </div>
        )}
      </div>

      <div className="official-header-right">
        {currentUser ? (
          <div className="header-user-profile-group">
            <div className="header-user-badge">
              <span className="user-name-text">{currentUser.name || currentUser.username}</span>
            </div>
            {onLogout && (
              <button
                type="button"
                id="header-logout-btn"
                className="header-logout-btn"
                onClick={onLogout}
                title="Keluar dari sesi dan kembali ke halaman login"
              >
                <span className="logout-label">Keluar</span>
              </button>
            )}
          </div>
        ) : (
          <button
            type="button"
            className="header-login-btn"
            onClick={onOpenLogin}
          >
            Masuk Akun
          </button>
        )}
      </div>
    </header>
  );
};
