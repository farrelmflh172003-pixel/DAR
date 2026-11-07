# PANDUAN DEPLOYMENT PRODUKSI & OPERASIONAL SISTEM
## MENKOPOLKAM AI HUB
Panduan resmi instalasi, konfigurasi, dan pemeliharaan sistem untuk Administrator Server & Tim DevSecOps.

---

## 1. Persyaratan Sistem Minimum (Prerequisites)

### A. Spesifikasi Server / VPS
* **Sistem Operasi**: Ubuntu 22.04 / 24.04 LTS, Debian 12, atau Windows Server 2019/2022.
* **Processor**: Minimal 2 vCPU (Disarankan 4 vCPU).
* **RAM**: Minimal 4 GB (Disarankan 8 GB).
* **Penyimpanan**: Minimal 20 GB SSD.
* **Port Terbuka**: Port `8000` (atau port `80`/`443` jika menggunakan reverse proxy).

### B. Dependensi Software
* **Opsi Docker**: Docker Engine versi 24+ & Docker Compose v2+.
* **Opsi Standalone**: Python 3.11/3.12 & Node.js 20 LTS (termasuk `npm`).

---

## 2. Langkah Deployment 1: Konfigurasi Environment (`.env`)

Sebelum menjalankan aplikasi, siapkan berkas environment pada direktori utama:
```bash
cp .env.example .env
```

Buka dan sesuaikan parameter wajib di dalam file `.env`:
```ini
# Status Lingkungan (development | staging | production)
ENV=production

# Host & Port Server
HOST=0.0.0.0
PORT=8000

# API Keys AI Providers (Wajib)
GEMINI_API_KEY=AIzaSy...IsiKeyGeminiAnda
OPENAI_API_KEY=sk-proj-...IsiKeyOpenAIAnda

# Keamanan Token JWT (Wajib minimal 32 karakter unik di mode produksi)
# Buat string acak di Linux/Mac: openssl rand -hex 32
JWT_SECRET_KEY=9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b
AUTH_ENABLED=true
ALLOW_ANONYMOUS_DEV=false

# CORS & WebSocket Allowed Origins (Ganti dengan Domain atau IP Publik Server Anda)
CORS_ORIGINS=http://localhost:8000,http://103.20.10.5:8000,https://ai-hub.menkopolkam.go.id

# Konfigurasi Database MariaDB (Opsional - Sistem otomatis beralih ke JSON jika DB tidak ada)
MARIADB_HOST=db
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=menkopolkam_db_secret_2026!
MARIADB_DATABASE=menkopolkam_ai_hub
```

---

## 3. Langkah Deployment 2: Menjalankan Sistem

### Opsi A: Deployment dengan Docker & Docker Compose (Rekomendasi Utama)

1. Jalankan skrip otomatisasi:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```
2. Atau jalankan langsung perintah Compose:
   ```bash
   docker compose up -d --build
   ```
3. Periksa status kontainer:
   ```bash
   docker compose ps
   ```
4. Buka browser pada alamat:
   `http://<IP-SERVER>:8000`

---

### Opsi B: Deployment Standalone di Linux VPS (Tanpa Docker)

1. Pasang dependensi Python:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r backend/requirements.txt
   ```
2. Kompilasi aset Frontend:
   ```bash
   cd frontend
   npm ci
   npm run build
   cd ..
   ```
3. Jalankan server Uvicorn (Single Unified Port 8000):
   ```bash
   python3 -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000
   ```
4. Untuk menjalankan di latar belakang secara permanen, gunakan Systemd:
   Buat file `/etc/systemd/system/menkopolkam.service`:
   ```ini
   [Unit]
   Description=Menkopolkam AI Hub Service
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/var/www/menkopolkam-ai-hub
   ExecStart=/var/www/menkopolkam-ai-hub/venv/bin/python -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```
   Aktifkan service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable menkopolkam
   sudo systemctl start menkopolkam
   ```

---

### Opsi C: Deployment di Komputer / Windows Server

1. Pastikan file `.env` sudah dikonfigurasi.
2. Klik ganda file:
   [**`deploy.bat`**](file:///d:/Menkopolkam%20AI%20HUB/deploy.bat)
   *Skrip otomatis melakukan validasi Docker atau kompilasi frontend dan menjalankan server produksi di Port 8000.*
3. Akses sistem di browser: `http://localhost:8000`

---

## 4. Konfigurasi Domain Resmi & SSL HTTPS (Nginx Reverse Proxy)

Untuk menggunakan nama domain resmi instansi (misal: `https://ai-hub.menkopolkam.go.id`) dan protokol HTTPS:

1. Salin berkas konfigurasi templat:
   ```bash
   sudo cp nginx.conf.example /etc/nginx/sites-available/menkopolkam.conf
   ```
2. Buka dan sesuaikan `server_name` serta path SSL di `/etc/nginx/sites-available/menkopolkam.conf`.
3. Aktifkan konfigurasi:
   ```bash
   sudo ln -s /etc/nginx/sites-available/menkopolkam.conf /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```
4. Jika menggunakan Certbot Let's Encrypt untuk sertifikat gratis:
   ```bash
   sudo certbot --nginx -d ai-hub.menkopolkam.go.id
   ```

---

## 5. Pemeliharaan & Monitoring Operasional

### A. Memeriksa Log Aplikasi
* **Docker**:
  ```bash
  docker compose logs -f menkopolkam-app
  ```
* **Systemd Linux**:
  ```bash
  journalctl -u menkopolkam -f
  ```

### B. Healthcheck Endpoint
Periksa kesehatan sistem secara periodik via HTTP monitoring / uptime robot:
* **URL**: `GET http://<SERVER-IP>:8000/api/health`
* **Response Normal**:
  ```json
  {
    "status": "operational",
    "application": "MENKOPOLKAM AI HUB",
    "mode": "live_api",
    "integrations": {
      "gemini": { "configured": true, "service": "Gemini 1.5 Pro/Flash" },
      "openai": { "configured": true, "service": "OpenAI GPT-4o" }
    }
  }
  ```

### C. Backup Data Persisten
Penyimpanan riwayat pertanyaan dan analisis berada di folder `backend/data/saved_files.json`.
Buat salinan backup berkala menggunakan cron:
```bash
0 2 * * * cp /path/to/backend/data/saved_files.json /backup/saved_files_$(date +\%F).json
```
Jika menggunakan Docker, backup volume `menkopolkam_data`:
```bash
docker run --rm -v menkopolkam_data:/data -v /backup:/backup alpine tar czf /backup/menkopolkam_backup_$(date +\%F).tar.gz /data
```

---

## 6. Penanganan Masalah Cepat (Troubleshooting)

| Gejala Masalah | Penyebab Umum | Langkah Penyelesaian |
| :--- | :--- | :--- |
| **Browser menampilkan `ERR_CONNECTION_REFUSED`** | Server belum aktif atau port 8000 diblokir firewall. | Pastikan container/service aktif (`docker compose ps`). Buka port di firewall: `sudo ufw allow 8000/tcp` atau `80,443/tcp`. |
| **Startup error: `Weak, insecure, or missing JWT_SECRET_KEY`** | Mode produksi aktif namun `JWT_SECRET_KEY` masih memakai nilai default insecure. | Isi `JWT_SECRET_KEY` pada file `.env` dengan string acak minimal 32 karakter tanpa kata "insecure". |
| **Audio TTS tidak bersuara** | Kuota API key Gemini habis atau browser memblokir autoplay. | Periksa kuota API di Google AI Studio. Pastikan izin audio/mikrofon diizinkan di browser pengguna. |
| **WebSocket gagal terhubung (Code 1008)** | Domain/IP server belum terdaftar di `CORS_ORIGINS`. | Tambahkan IP publik atau domain server ke parameter `CORS_ORIGINS` di file `.env`, lalu restart server. |
| **Tampilan Card 11 kosong** | Data belum termuat sempurna. | Sistem kini memiliki auto-fallback ke Kartu 3 Jawaban Utama; cukup klik salah satu kartu respon untuk memicu pemutakhiran otomatis. |
