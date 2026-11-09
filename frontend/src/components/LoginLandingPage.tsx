import React, { useState, useEffect } from 'react';
import type { User, CaptchaData } from '../types/auth';
import { API_BASE_URL } from '../config';

interface LoginLandingPageProps {
  onLoginSuccess: (user: User, token: string) => void;
}

export const LoginLandingPage: React.FC<LoginLandingPageProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('superadmin');
  const [password, setPassword] = useState('superadmin');
  const [captchaAnswer, setCaptchaAnswer] = useState('');
  const [captchaData, setCaptchaData] = useState<CaptchaData | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Fetch captcha challenge on mount or refresh
  const refreshCaptcha = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/captcha`);
      if (res.ok) {
        const data = await res.json();
        setCaptchaData(data);
        setCaptchaAnswer('');
      }
    } catch {
      setErrorMessage('Gagal memuat kode keamanan captcha dari server backend.');
    }
  };

  useEffect(() => {
    refreshCaptcha();
  }, []);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');

    if (!username.trim()) {
      setErrorMessage('Username wajib diisi.');
      return;
    }
    if (!password.trim()) {
      setErrorMessage('Kata sandi wajib diisi.');
      return;
    }
    if (!captchaAnswer.trim() || !captchaData) {
      setErrorMessage('Jawaban verifikasi captcha keamanan wajib diisi.');
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
        setErrorMessage(json.detail || 'Otentikasi ditolak. Periksa kembali username dan kata sandi Anda.');
        refreshCaptcha();
      } else {
        onLoginSuccess(json.user, json.token);
      }
    } catch {
      setErrorMessage('Terjadi gangguan jaringan saat menghubungi server backend FastAPI.');
      refreshCaptcha();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-minimal-page">
      <div className="login-minimal-wrapper">
        {/* Logo & Identitas Resmi */}
        <div className="login-minimal-brand">
          <img
            src="/logo.png"
            alt="Dialogue AI Representative"
            className="login-minimal-logo"
          />
          <div className="login-minimal-institution">
            <h1 className="inst-main text-lg font-bold tracking-tight">Dialogue AI Representative</h1>
          </div>
        </div>

        {/* Header Form */}
        <div className="login-minimal-heading">
          <h2 className="login-minimal-title">Masuk</h2>
        </div>

        {/* Error Notice */}
        {errorMessage && (
          <div className="landing-error-banner" role="alert">
            <span className="error-icon">⚠️</span>
            <span className="error-text">{errorMessage}</span>
          </div>
        )}

        {/* Form Credentials */}
        <form onSubmit={handleFormSubmit} className="login-minimal-form">
          <div className="minimal-field">
            <label htmlFor="login-username">Username</label>
            <input
              id="login-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className="minimal-field">
            <label htmlFor="login-password">Kata Sandi</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {/* Captcha Security Challenge */}
          <div className="minimal-captcha-box">
            <div className="captcha-top-bar">
              <label htmlFor="login-captcha" className="captcha-title">
                Verifikasi Keamanan Captcha
              </label>
              <button
                type="button"
                onClick={refreshCaptcha}
                className="captcha-refresh-action"
                title="Klik untuk mengganti kode captcha"
              >
                ↻ Segarkan Kode
              </button>
            </div>

            <div className="captcha-content-row">
              {captchaData ? (
                <div
                  className="landing-captcha-svg"
                  dangerouslySetInnerHTML={{ __html: captchaData.svg }}
                />
              ) : (
                <div className="landing-captcha-loading">Memuat Captcha...</div>
              )}
              <input
                id="login-captcha"
                type="text"
                value={captchaAnswer}
                onChange={(e) => setCaptchaAnswer(e.target.value)}
                placeholder=""
                autoComplete="off"
                required
              />
            </div>
          </div>

          {/* Submit Action */}
          <button
            type="submit"
            id="login-submit-btn"
            className="minimal-login-btn"
            disabled={loading}
          >
            {loading ? (
              <span className="btn-loading-state">
                <span className="login-spinner" /> Memverifikasi...
              </span>
            ) : (
              'Masuk'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
