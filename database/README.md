# MENKOPOLKAM AI HUB — DATABASE REPOSITORY

Repositori database ini mengelola penyimpanan data arsip kenegaraan, akun pengguna (RBAC), serta log audit sesi.

## Struktur Database:
1. **`saved_files.json`**:
   - Penyimpanan data berkas, naskah resmi, transkripsi suara, analisis intelijen diplomatik (ChatGPT & Gemini), serta Jawaban Terpilih (Card 11).
   - Berfungsi sebagai database utama mandiri (*self-contained resilient storage*) dengan *thread-safe atomic write* & *auto-snapshot*.
2. **`schema.sql` / `init.sql`**:
   - Skrip DDL untuk MariaDB / MySQL Enterprise 11.4+.
   - Menyediakan tabel `users`, `saved_files`, dan `session_history`.
   - Otomatis diinisialisasi oleh Docker Compose saat deployment ke server produksi.

