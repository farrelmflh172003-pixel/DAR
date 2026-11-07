import React, { useState, useEffect } from 'react';
import type { User, CaptchaData } from '../types/auth';
import { API_BASE_URL } from '../config';

interface LoginModalProps {
  isOpen: boolean;
  onLoginSuccess: (user: User, token: string) => void;
  onClose?: () => void;
  currentUser?: User | null;
}

const PRESET_ACCOUNTS = [
  { username: 'admin', label: 'Admin', role: 'Admin', pass: 'admin' },
  { username: 'superadmin', label: 'Superadmin', role: 'Superadmin', pass: 'superadmin' },
  { username: 'viewer', label: 'Viewer', role: 'Viewer', pass: 'viewer' },
];

export const LoginModal: React.FC<LoginModalProps> = ({
  isOpen,
  onLoginSuccess,
  onClose,
  currentUser
}) => {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [captchaAnswer, setCaptchaAnswer] = useState('');
  const [captchaData, setCaptchaData] = useState<CaptchaData | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Fetch new captcha challenge from backend
  const refreshCaptcha = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/captcha`);
      if (res.ok) {
        const data = await res.json();
        setCaptchaData(data);
        setCaptchaAnswer('');
      }
    } catch {
      setErrorMessage('Gagal memuat kode keamanan captcha dari server.');
    }
  };

  useEffect(() => {
    if (isOpen) {
      refreshCaptcha();
      setErrorMessage('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSelectPreset = (acc: typeof PRESET_ACCOUNTS[0]) => {
    setUsername(acc.username);
    setPassword(acc.pass);
    setErrorMessage('');
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!username.trim()) {
      setErrorMessage('Username harus diisi.');
      return;
    }
    if (!password.trim()) {
      setErrorMessage('Password harus diisi.');
      return;
    }
    if (!captchaAnswer.trim() || !captchaData) {
      setErrorMessage('Jawaban kode keamanan captcha harus diisi.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username.trim(),
          password: password.trim(),
          captcha_id: captchaData.captcha_id,
          captcha_answer: captchaAnswer.trim()
        })
      });

      const json = await res.json();
      if (!res.ok) {
        setErrorMessage(json.detail || 'Otentikasi gagal. Periksa kembali kredensial Anda.');
        refreshCaptcha();
      } else {
        onLoginSuccess(json.user, json.token);
      }
    } catch {
      setErrorMessage('Terjadi gangguan jaringan saat menghubungi server backend.');
      refreshCaptcha();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-modal-overlay">
      <div className="login-modal-box">
        {/* Close button if user already logged in */}
        {currentUser && onClose && (
          <button
            type="button"
            className="login-modal-close-btn"
            onClick={onClose}
            title="Tutup Jendela"
          >
            ✕
          </button>
        )}

        <div className="login-modal-grid">
          {/* Sisi Kiri: Logo Besar Kemenkopolkam & Identitas Resmi */}
          <div className="login-branding-col">
            <div className="login-logo-wrapper">
              <img
                src="/Kemenkopolkam.webp"
                alt="Logo Resmi Kemenko Polkam RI"
                className="login-large-logo"
              />
            </div>
            <div className="login-branding-text">
              <h2>KEMENTERIAN KOORDINATOR</h2>
              <h3>BIDANG POLITIK DAN KEAMANAN</h3>
              <p>REPUBLIK INDONESIA</p>
              <div className="login-seal-badge">AI HUB STRATEGIS</div>
            </div>

            {/* Informasi Hak Akses & Role Matrix */}
            <div className="login-role-matrix-guide">
              <div className="matrix-title">Matriks Otoritas Akun:</div>
              <ul className="matrix-list">
                <li><strong>Admin</strong>: Administrator Operasional Diplomasi &amp; Kebijakan Polkam</li>
                <li><strong>Superadmin</strong>: Akses penuh administrasi &amp; konfigurasi keamanan sistem</li>
                <li><strong>Viewer</strong>: Pengamat &amp; Peninjau Dokumen Resmi (Mode Pantau)</li>
              </ul>
            </div>
          </div>

          {/* Sisi Kanan: Form Login Tanpa Placeholder dan Tanpa Bintang */}
          <div className="login-form-col">
            <div className="login-form-header">
              <h2>Autentikasi Pengguna</h2>
              <p>Masukkan username dan password resmi Anda</p>
            </div>

            {/* Pilihan Cepat Akun Demo / Uji Coba */}
            <div className="preset-account-pills">
              {PRESET_ACCOUNTS.map((acc) => (
                <button
                  key={acc.username}
                  type="button"
                  className={`preset-pill ${username === acc.username ? 'active' : ''}`}
                  onClick={() => handleSelectPreset(acc)}
                >
                  {acc.label}
                </button>
              ))}
            </div>

            {errorMessage && (
              <div className="login-error-alert" role="alert">
                {errorMessage}
              </div>
            )}

            <form onSubmit={handleFormSubmit} className="login-credentials-form">
              {/* Field Username: Tanpa Placeholder, Tanpa Bintang */}
              <div className="login-field-group">
                <label htmlFor="login-input-username">Username</label>
                <input
                  id="login-input-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>

              {/* Field Password: Tanpa Placeholder, Tanpa Bintang */}
              <div className="login-field-group">
                <label htmlFor="login-input-password">Password</label>
                <input
                  id="login-input-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
              </div>

              {/* Field Captcha Keamanan: Tanpa Placeholder, Tanpa Bintang */}
              <div className="login-field-group captcha-group">
                <div className="captcha-label-row">
                  <label htmlFor="login-input-captcha">Kode Keamanan Captcha</label>
                  <button
                    type="button"
                    onClick={refreshCaptcha}
                    className="captcha-refresh-btn"
                    title="Segarkan Kode Captcha"
                  >
                    Segarkan
                  </button>
                </div>

                <div className="captcha-display-row">
                  {captchaData ? (
                    <div
                      className="captcha-svg-container"
                      dangerouslySetInnerHTML={{ __html: captchaData.svg }}
                    />
                  ) : (
                    <div className="captcha-loading">Memuat Captcha...</div>
                  )}

                  <input
                    id="login-input-captcha"
                    type="text"
                    value={captchaAnswer}
                    onChange={(e) => setCaptchaAnswer(e.target.value)}
                    autoComplete="off"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                id="login-submit-button"
                className="login-submit-btn"
                disabled={loading}
              >
                {loading ? 'Memverifikasi...' : 'Masuk ke Sistem'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
