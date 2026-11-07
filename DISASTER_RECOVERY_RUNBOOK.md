# DISASTER RECOVERY RUNBOOK — MENKOPOLKAM AI HUB
**Sistem Operasional Pemulihan Bencana & Kesiapsiagaan Darurat**
**Klasifikasi Keamanan: Internal DevSecOps & SRE Kemenko Polkam RI**

---

## 1. TUJUAN & METRIK KESIAPSIAGAAN (SLA / RTO & RPO)
Dokumen ini menetapkan prosedur operasional standar (SOP) untuk memulihkan layanan **MENKOPOLKAM AI HUB** dalam situasi gangguan kritis, kehilangan daya, kerusakan basis data, serangan siber, atau kegagalan infrastruktur server.

| Parameter | Target SLA | Keterangan |
|---|---|---|
| **RTO (Recovery Time Objective)** | **< 15 Menit** | Waktu maksimum layanan harus pulih beroperasi penuh setelah insiden terjadi. |
| **RPO (Recovery Point Objective)** | **< 0 Menit (Realtime)** | Data aktif disimpan secara ganda ke MariaDB dan snapshot atomik `saved_files.json`. |
| **Ketersediaan Layanan (Uptime)** | **99.9%** | Menjamin keandalan operasional diplomasi dan monitoring strategis nasional. |

---

## 2. KLASIFIKASI INSIDEN (SEVERITY MATRIX)
- **SEV-1 (Bencana Kritis / Outage Total)**: Seluruh layanan tidak dapat diakses, web server mati, atau container database crash fatal.
- **SEV-2 (Degradasi Mayor)**: Database MariaDB terputus (aplikasi dialihkan ke mode fallback JSON), atau API AI provider mengalami throttling/timeout.
- **SEV-3 (Isu Fungsional Parsial)**: Fitur TTS audio terhambat atau proses ekspor PDF lambat, layanan web utama tetap melayani delegasi.
- **SEV-4 (Isu Minor / Tampilan)**: Kesalahan penulisan teks UI atau anomali log non-fatal.

---

## 3. SKENARIO 1: KEGAGALAN KONEKSI BASIS DATA MARIADB (AUTO-FAILOVER & RECOVERY)
### A. Gejala
Log backend menampilkan: `MariaDB connection failed. Operating in JSON fallback mode.`

### B. Prosedur Auto-Failover (Arsitektur Resilient)
Aplikasi MENKOPOLKAM AI HUB dilengkapi modul `Dual-Engine Storage`. Ketika MariaDB tidak dapat diakses:
1. Layanan backend secara otomatis beralih ke penyimpanan failover terenkripsi lokal: `backend/data/saved_files.json`.
2. Seluruh aktivitas pembuatan dokumen, pembaruan Card 11 (Jawaban Terpilih), dan riwayat tetap berjalan normal tanpa interupsi bagi pengguna.
3. Thread-safe lock (`threading.Lock()`) melindungi integritas file agar tidak terjadi *race condition* atau korupsi berkas.

### C. Prosedur Pemulihan MariaDB
1. Periksa container basis data:
   ```bash
   docker compose ps db
   docker compose logs db --tail=50
   ```
2. Restart service MariaDB:
   ```bash
   docker compose restart db
   ```
3. Sinkronisasikan kembali data snapshot lokal ke MariaDB setelah pulih:
   ```bash
   python -c "from backend.services.saved_file_service import saved_file_service; saved_file_service.sync_fallback_to_mariadb()"
   ```

---

## 4. SKENARIO 2: CRASH CONTAINER APLIKASI (APPLICATION RESTART RUNBOOK)
### A. Gejala
HTTP 502 Bad Gateway pada Nginx atau container `menkopolkam-app` berstatus `Exited` / `Unhealthy`.

### B. Prosedur Pemulihan Cepat (< 2 Menit)
1. Periksa kode kesalahan dan log terakhir:
   ```bash
   docker compose logs app --tail=100
   ```
2. Jalankan restart container:
   ```bash
   docker compose restart app
   ```
3. Jika container tetap gagal boot (misal berkas korup):
   ```bash
   docker compose down
   docker compose build --no-cache app
   docker compose up -d
   ```
4. Verifikasi endpoint healthcheck:
   ```bash
   curl -s http://127.0.0.1:8000/api/health | jq
   ```

---

## 5. SKENARIO 3: KERUSAKAN DATA & PROSEDUR RESTORE BACKUP
### A. Backup Otomatis
Sistem melakukan backup berkala ke: `backend/data/backups/saved_files_<timestamp>.json` dan snapshot volume Docker MariaDB.

### B. Prosedur Restore Snapshot
1. Hentikan sementara backend:
   ```bash
   docker compose stop app
   ```
2. Identifikasi file backup valid terbaru:
   ```bash
   ls -lat backend/data/backups/
   ```
3. Salin backup ke berkas operasional:
   ```bash
   cp backend/data/backups/saved_files_YYYYMMDD_HHMMSS.json backend/data/saved_files.json
   ```
4. Jalankan kembali aplikasi:
   ```bash
   docker compose start app
   ```

---

## 6. SKENARIO 4: GANGGUAN SERTIFIKAT SSL/TLS ATAU NGINX REVERSE PROXY
### A. Gejala
Browser menampilkan peringatan `NET::ERR_CERT_DATE_INVALID` atau koneksi WSS ditolak.

### B. Prosedur Pemulihan
1. Uji keabsahan konfigurasi Nginx:
   ```bash
   sudo nginx -t
   ```
2. Perbarui sertifikat Let's Encrypt secara manual jika kedaluwarsa:
   ```bash
   sudo certbot renew --force-renewal
   sudo systemctl reload nginx
   ```
3. Verifikasi cipher TLS 1.2 dan 1.3:
   ```bash
   curl -Iv https://aihub.polkam.go.id 2>&1 | grep -i ssl
   ```

---

## 7. MATRIKS KOMUNIKASI & ESKALASI DARURAT
| Tingkat Eskalasi | Petugas / Tim | Waktu Respon Maksimal |
|---|---|---|
| **Level 1** | On-Call SRE / DevOps Engineer | 5 Menit |
| **Level 2** | Application Security Specialist & Database Admin | 10 Menit |
| **Level 3** | Principal Software Architect & Head of IT Polkam | 15 Menit |

*Dokumen ini divalidasi dan dinyatakan aktif untuk pedoman operasional Staging & Production MENKOPOLKAM AI HUB.*

