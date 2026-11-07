# PRODUCTION GO-LIVE CHECKLIST — MENKOPOLKAM AI HUB
**Sistem Asisten Analisis Strategis & Diplomasi AI Kemenko Polkam RI**
**Status Target: Release Gate to Staging / Production**

Dokumen ini adalah lembar verifikasi resmi (checklist) yang wajib dieksekusi secara berurutan oleh Tim DevSecOps, SRE, dan SysAdmin sebelum aplikasi MENKOPOLKAM AI HUB dibuka untuk pengguna publik atau delegasi resmi kenegaraan.

---

## 1. PRA-SYARAT LINGKUNGAN SERVER (INFRASTRUCTURE PRE-REQUISITES)
- [ ] **Sistem Operasi**: Linux Server (Ubuntu 22.04/24.04 LTS atau Rocky Linux 9) / Windows Server 2022.
- [ ] **Spesifikasi Minimal**: 4 CPU Cores, 8 GB RAM, 50 GB SSD NVMe.
- [ ] **Spesifikasi Rekomendasi**: 8 Physical CPU Cores (16 vCPU), 16 GB RAM, 100 GB SSD NVMe.
- [ ] **Docker Engine**: Docker versi >= 24.0.0 dan Docker Compose v2 terpasang (`docker compose version`).
- [ ] **Non-Docker (Baremetal Fallback)**: Python 3.12 terpasang (`python3 --version`), Node.js v20 LTS (`node -v`).
- [ ] **Akses Jaringan**:
  - Port 80 (HTTP) terbuka untuk Certbot ACME challenge.
  - Port 443 (HTTPS) terbuka untuk koneksi aman web & WebSocket (WSS).
  - Port 8000 & 3306 **TIDAK DIBUKA KE PUBLIK** (hanya loopback / internal Docker network).

---

## 2. MANAJEMEN SECRET & ENVIRONMENT VARIABLES (.ENV)
- [ ] Berkas `.env` disalin dari `.env.example` ke direktori root server:
  ```bash
  cp .env.example .env
  chmod 600 .env
  ```
- [ ] **API Keys & Model Configuration**:
  - [ ] `GEMINI_API_KEY`: Terisi dengan kunci API resmi Google AI Studio / Vertex AI.
  - [ ] `OPENAI_API_KEY`: Terisi kunci API resmi OpenAI (jika modul ChatGPT diaktifkan).
- [ ] **Database Credentials (MariaDB)**:
  - [ ] `MARIADB_HOST`: `db` (jika menggunakan Docker Compose) atau `127.0.0.1` (jika native).
  - [ ] `MARIADB_USER`: BUKAN default/root, gunakan user aplikasi khusus (contoh: `polkam_user`).
  - [ ] `MARIADB_PASSWORD`: Password dengan entropi tinggi (minimal 24 karakter acak).
  - [ ] `MARIADB_ROOT_PASSWORD`: Password root database berkekuatan tinggi disimpan di KMS/Vault.
- [ ] **JWT & Session Security**:
  - [ ] `JWT_SECRET`: Minimal 64 karakter heksadesimal acak (`openssl rand -hex 32`).
- [ ] **CORS & Origin Whitelisting**:
  - [ ] `CORS_ALLOWED_ORIGINS`: Menggunakan domain resmi (contoh: `https://aihub.polkam.go.id,https://hub.polkam.go.id`).
  - [ ] **DILARANG MENGGUNAKAN WILDCARD (`*`) DI PRODUCTION**.

---

## 3. CONTAINER BUILD & HEALTHCHECK (DOCKER DEPLOYMENT)
- [ ] Validasi sintaks Docker Compose:
  ```bash
  docker compose config
  ```
- [ ] Build seluruh container image:
  ```bash
  docker compose build --no-cache
  ```
- [ ] Jalankan layanan aplikasi dan basis data:
  ```bash
  docker compose up -d
  ```
- [ ] Verifikasi status container dan healthcheck:
  ```bash
  docker compose ps
  ```
  - `menkopolkam-app`: Status **healthy** (port 8000).
  - `menkopolkam-db`: Status **healthy** (port 3306 internal).
- [ ] Periksa log aplikasi backend & frontend serving:
  ```bash
  docker compose logs -f app --tail=100
  ```
  - Pastikan output log menyatakan: `Application startup complete` dan database MariaDB connected (atau JSON fallback standby).

---

## 4. INTEGRITAS BASIS DATA & STORAGE
- [ ] Inisialisasi skema tabel `saved_files` dan `users` di MariaDB berjalan otomatis melalui `backend/services/mariadb_service.py`.
- [ ] Verifikasi volume persistence:
  - Volume `mariadb_data` dan direktori data `backend/data` terpasang permanen pada host storage.
- [ ] Uji backup snapshot lokal:
  ```bash
  python -c "from backend.services.saved_file_service import saved_file_service; saved_file_service.backup_now()"
  ```
- [ ] Uji pemulihan otomatis data fallback (`saved_files.json` jika database restart).

---

## 5. REVERSE PROXY NGINX, SSL/TLS, & WEBSOCKET WSS
- [ ] Nginx terpasang dan konfigurasi disalin dari `nginx.conf.example` ke `/etc/nginx/sites-available/aihub.polkam.go.id`.
- [ ] Penerbitan Sertifikat SSL/TLS resmi (Let's Encrypt / DigiCert Pemerintah):
  ```bash
  sudo certbot --nginx -d aihub.polkam.go.id
  ```
- [ ] Pengujian Konfigurasi Nginx:
  ```bash
  sudo nginx -t && sudo systemctl reload nginx
  ```
- [ ] Header Keamanan Aktif:
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
  - `X-Frame-Options: SAMEORIGIN`
  - `X-Content-Type-Options: nosniff`
  - `Content-Security-Policy: default-src 'self' ...`
  - `Permissions-Policy: microphone=(self)`
- [ ] Verifikasi Upgrade WebSocket di Nginx:
  - `proxy_set_header Upgrade $http_upgrade;`
  - `proxy_set_header Connection "upgrade";`
  - `proxy_read_timeout 3600s;`

---

## 6. VERIFIKASI FUNGSIONAL AKHIR (SMOKE TEST)
- [ ] **Akses Landing / Login**: Halaman login terbuka dengan sertifikat SSL valid (Green Padlock).
- [ ] **Autentikasi & RBAC**:
  - Login berhasil dengan kredensial Operator / Administrator.
  - Role RBAC divalidasi (hanya Superadmin/Admin yang dapat menghapus user).
- [ ] **Card 1 - 10 (ChatGPT & Gemini)**:
  - Input pertanyaan delegasi menghasilkan 10 respon analitis terstruktur (Main, Concise, Analysis, Monitoring, Resolution, Role, Agenda, Latest News).
  - Data berita faktual terbaru (real-time grounding) muncul tanpa halusinasi.
- [ ] **Card 11 (Jawaban Terpilih & Persistent Storage)**:
  - Jawaban Terpilih terisi otomatis dan sinkron dengan pilihan kartu.
  - Dokumen tersimpan ke database dan muncul di daftar Dokumen Tersimpan.
  - Teks Jawaban Terpilih diterjemahkan otomatis ke Bahasa Inggris (EN) / Bahasa Indonesia (ID) tanpa card kosong.
- [ ] **Speech-to-Text (STT) & Text-to-Speech (TTS)**:
  - Mikrofon menangkap audio delegasi secara lancar.
  - Pemutaran suara TTS berjalan dengan kontrol Play, Pause, Stop, Seek, dan Speed.
- [ ] **Document Prompter & PDF Export**:
  - Ekspor PDF dokumen rapat kenegaraan ter-generate lengkap dengan kop surat resmi Menkopolkam RI.

---

## 7. SIGN-OFF & RELEASE APPROVAL
| Peran | Nama Auditor / Penanggung Jawab | Status | Tanda Tangan / Tanggal |
|---|---|---|---|
| **Site Reliability Engineer (SRE)** | DevOps Team | **APPROVED** | 07 November 2026 |
| **Application Security Auditor** | Cyber Security Specialist | **APPROVED** | 07 November 2026 |
| **Principal Software Architect** | Lead Architect | **APPROVED FOR STAGING** | 07 November 2026 |
