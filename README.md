# MENKOPOLKAM AI HUB

Sistem bantuan penerjemahan multilingual, analisis analitikal kebijakan, dan platform suara interaktif *real-time duplex* untuk **Menteri Koordinator Bidang Politik dan Keamanan Republik Indonesia**.

Dirancang khusus untuk pertemuan diplomatik real-time, diskusi resmi bilateral/multilateral, wawancara internasional, penegakan hukum kedaulatan, dan keterlibatan kenegaraan tingkat tinggi.

---

## Arsitektur Voice Real-Time (Phase 2)

Sistem mengintegrasikan dua engine suara AI tingkat tinggi dengan pemisahan status eksekusi yang jujur:

1. **Google Gemini Live:**
   - **Native Multimodal Bidi WebSocket:** Menghubungkan secara langsung ke endpoint `BidiGenerateContent` (`v1beta`).
   - **Gemini Flash Streaming Bridge (Explicit Fallback):** Apabila API key belum memiliki izin whitelisting enterprise Bidi (ditolak dengan error kebijakan `1008 policy violation`), sistem secara otomatis beralih ke streaming bridge berkecepatan tinggi: teks inferensi Flash Lite + sintesis audio Neural TTS 24kHz dengan pembersihan header WAV RIFF untuk kualitas audio jernih tanpa artefak/klik.
2. **OpenAI Realtime GA:**
   - Menghubungkan ke endpoint resmi GA `wss://api.openai.com/v1/realtime?model=gpt-realtime-mini` (atau `gpt-realtime`).
   - Validasi format audio 24.000 Hz PCM16 little-endian, resampling otomatis dari input mikrofon 16 kHz menjadi 24 kHz via interpolasi linier.
   - Deteksi suara server (Server VAD), pengenalan barge-in, dan penanganan kuota (`credit_balance_exhausted`) secara transparan dan jujur.
   - Mode mock fallback hanya aktif apabila dikonfigurasi secara eksplisit melalui `ENABLE_REALTIME_MOCK=true`.

---

## Matriks Status Provider

| Status | Deskripsi | Kapan Terjadi |
| :--- | :--- | :--- |
| `native_connected` | Terhubung langsung ke socket native audio-to-audio resmi penyedia | Akun & project memiliki akses native WebSocket yang valid dan aktif |
| `bridge_active` | Menggunakan streaming bridge Flash Lite + 24kHz Neural TTS | Gemini Live WebSocket ditolak karena kebijakan whitelisting project/enterprise |
| `mock_active` | Simulasi respons sintetis offline | `ENABLE_REALTIME_MOCK=true` di `.env` (untuk pengujian offline) |
| `disconnected` | Sesi ditutup atau dibersihkan secara aman | Sesi berakhir atau koneksi diputus oleh pengguna |
| `error` | Gagal terhubung atau kuota habis | API key salah, saldo habis (`credit_balance_exhausted`), atau jaringan terputus |

---

## Tiga Mode Orkestrasi

- **Mode A (Percakapan Live):** Satu provider menangani dialog secara langsung dan interaktif tanpa jeda atau tumpang tindih audio.
- **Mode B (Dual Intelligence):** Provider utama menyajikan respons suara seketika, sementara engine sekunder melakukan analisis strategis/yuridis/operasional mendalam secara asinkron tanpa menahan aliran suara utama.
- **Mode C (Handoff Konteks):** Pengalihan engine secara mulus (misal dari Gemini ke ChatGPT) di mana ringkasan konteks percakapan dialihkan secara eksplisit dan audio provider sebelumnya dihentikan seketika.

---

## Pengukuran Latensi & Interupsi (Barge-In)

- **Barge-In Latency:** Pemotongan playback instan < 30 ms di frontend (Web Audio `instantBargeIn`) dan pembatalan tugas asinkron di backend (`cancel_response`).
- **Telemetry HUD:** Mengukur latensi giliran (*turn latency*) secara nyata dari akhir ucapan pengguna hingga chunk audio pertama terdengar, lengkap dengan metrik **Median** dan **P95**.

---

## Konfigurasi Lingkungan (`backend/.env`)

Salin `backend/.env.example` ke `backend/.env` dan isi kredensial:

```env
# Kredensial API
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AQ...

# Konfigurasi Model Suara Real-Time
OPENAI_REALTIME_MODEL=gpt-realtime-mini
GEMINI_LIVE_MODEL=models/gemini-2.0-flash-exp

# Kontrol Fallback Mock (wajib false untuk koneksi nyata)
ENABLE_REALTIME_MOCK=false

# Konfigurasi Jaringan Server
ENV=development
HOST=127.0.0.1
PORT=8000
```

---

## Menjalankan Aplikasi & Pengujian

### 1. Menjalankan Server Backend
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Menjalankan Frontend
```bash
cd frontend
npm run dev
```
Akses di browser: `http://localhost:5173/`

### 3. Menjalankan Pengujian Otomatis
```bash
# Backend Pytest (Unit, Keamanan, Latensi, & Integrasi API):
cd backend
python -m pytest -v

# Frontend TypeScript Typecheck & Production Build:
cd frontend
npm run build
```
