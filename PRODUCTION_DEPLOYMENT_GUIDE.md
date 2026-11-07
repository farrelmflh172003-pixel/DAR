# PANDUAN DEPLOYMENT PRODUKSI & OPERASIONAL SISTEM
## MENKOPOLKAM AI HUB
Panduan resmi instalasi, konfigurasi, dan pemeliharaan sistem untuk Administrator Server & Tim DevSecOps.

---

## 1. Persyaratan Sistem & Instalasi Docker

### A. Instalasi Docker Engine di Linux Server (Ubuntu / Debian)
Jika Docker belum terpasang di server Linux Anda:
```bash
# 1. Update package index
sudo apt update && sudo apt install -y curl apt-transport-https ca-certificates gnupg

# 2. Pasang Docker Engine resmi
curl -fsSL https://get.docker.com | sh

# 3. Masukkan user saat ini ke grup docker
sudo usermod -aG docker $USER
newgrp docker

# 4. Verifikasi instalasi Docker & Compose
docker version
docker compose version
```

### B. Instalasi Docker di Windows Server
Untuk Windows Server 2022:
1. Aktifkan fitur Kontainer via PowerShell (Administrator):
   ```powershell
   Install-Module -Name DockerMsftProvider -Repository PSGallery -Force
   Install-Package -Name docker -ProviderName DockerMsftProvider -Force
   Restart-Computer -Force
   ```
2. Atau pasang Docker Desktop dengan WSL2 backend untuk pengujian Windows.

---

## 2. Penyelesaian 11 Item Pengujian yang BLOCKED di Server Target

11 item pengujian yang berstatus **BLOCKED** pada lingkungan development lokal wajib dieksekusi saat kode dipasang di server target:

### A. Verifikasi Runtime Docker (8 Item):
Jalankan perintah berikut di server target:
```bash
# 1. Validasi sintaks compose
docker compose config

# 2. Build image
docker compose build --no-cache

# 3. Nyalakan seluruh container di background
docker compose up -d

# 4. Cek status container (memastikan status UP dan HEALTHY)
docker compose ps

# 5. Cek log runtime
docker compose logs -f menkopolkam-app

# 6. Verifikasi Healthcheck HTTP
curl -f http://localhost:8000/api/health

# 7. Uji restart container
docker compose restart
docker compose ps
```

### B. Verifikasi Domain, HTTPS & WSS (3 Item):
1. Pastikan record DNS domain (misal: `ai-hub.menkopolkam.go.id`) mengarah ke alamat IP Publik VPS.
2. Salin template Nginx:
   ```bash
   sudo cp nginx.conf.example /etc/nginx/sites-available/menkopolkam.conf
   sudo nano /etc/nginx/sites-available/menkopolkam.conf
   ```
3. Pasang sertifikat SSL TLS gratis dari Let's Encrypt via Certbot:
   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d ai-hub.menkopolkam.go.id
   ```
4. Verifikasi koneksi aman HTTPS dan WebSocket WSS di browser:
   * URL: `https://ai-hub.menkopolkam.go.id`
   * WebSocket: `wss://ai-hub.menkopolkam.go.id/ws/realtime-session`

---

## 3. Konfigurasi Environment Produksi (`.env`)

Salin file `.env.example` ke `.env`:
```bash
cp .env.example .env
```

Isi parameter wajib di `.env`:
```ini
ENV=production
HOST=0.0.0.0
PORT=8000

# API Keys AI Providers (Wajib)
GEMINI_API_KEY=AIzaSy...IsiKeyGeminiAnda
OPENAI_API_KEY=sk-proj-...IsiKeyOpenAIAnda

# Keamanan Token JWT (Wajib minimal 32 karakter unik acak)
JWT_SECRET_KEY=9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b
AUTH_ENABLED=true
ALLOW_ANONYMOUS_DEV=false

# CORS & WebSocket Allowed Origins (Strict Whitelist - Dilarang Wildcard * pada Produksi)
CORS_ORIGINS=http://localhost:8000,http://103.20.10.5:8000,https://ai-hub.menkopolkam.go.id

# Konfigurasi Database MariaDB
MARIADB_HOST=db
MARIADB_PORT=3306
MARIADB_USER=root
MARIADB_PASSWORD=menkopolkam_db_secret_2026!
MARIADB_DATABASE=menkopolkam_ai_hub
```

---

## 4. Opsi Deployment Alternatif (Native Tanpa Docker)

Jika server produksi tidak mengizinkan Docker, gunakan skrip native:

### Linux VPS / Server:
1. Pastikan Node.js 20 & Python 3.12 terpasang.
2. Jalankan perintah instalasi:
   ```bash
   pip install -r backend/requirements.txt
   cd frontend && npm ci && npm run build && cd ..
   python3 -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000
   ```

### Windows Server:
Klik ganda file [**`deploy.bat`**](file:///d:/Menkopolkam%20AI%20HUB/deploy.bat). Skrip akan mengompilasi frontend, memasang dependensi, dan menyalakan server di Port 8000.

---

## 5. Prosedur Backup & Rollback

### A. Backup Data Rutin
Penyimpanan riwayat pertanyaan dan analisis berada di folder `backend/data/saved_files.json`.
```bash
# Backup harian
cp backend/data/saved_files.json /backup/saved_files_$(date +\%F).json
```

### B. Prosedur Rollback Cepat
Jika versi baru mengalami kendala pada server:
```bash
# 1. Rollback image container
docker compose down
docker compose up -d

# 2. Rollback kode Git
git checkout HEAD~1
cd frontend && npm run build && cd ..

# 3. Pulihkan data
cp /backup/saved_files_backup.json backend/data/saved_files.json
```
