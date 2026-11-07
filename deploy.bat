@echo off
setlocal enabledelayedexpansion

echo ==========================================================
echo   MENKOPOLKAM AI HUB - 1-CLICK PRODUCTION DEPLOYMENT
echo ==========================================================

:: 1. Check for .env file
if not exist .env (
    echo [INFO] File .env tidak ditemukan. Menyalin dari .env.example...
    copy .env.example .env >nul
    echo [OK] File .env telah dibuat. Silakan sesuaikan API KEY jika diperlukan.
)

:: 2. Check if Docker is available
where docker >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Docker terdeteksi di sistem.
    echo Apakah Anda ingin menjalankan dengan Docker Compose? [Y/N]
    set /p USE_DOCKER="Pilihan (Default Y): "
    if "!USE_DOCKER!"=="" set USE_DOCKER=Y
    if /i "!USE_DOCKER!"=="Y" (
        echo [INFO] Menjalankan via Docker Compose...
        docker compose down 2>nul
        docker compose up -d --build
        echo.
        echo ==========================================================
        echo   DEPLOYMENT DOCKER SELESAI!
        echo   Buka browser pada: http://localhost:8000
        echo ==========================================================
        pause
        exit /b 0
    )
)

:: 3. Native Windows Server Production Deployment
echo [INFO] Memulai Mode Produksi Native Windows...

echo [1/3] Mengompilasi Frontend SPA (Vite + React)...
cd /d "%~dp0frontend"
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Gagal mengompilasi Frontend. Pastikan NodeJS terpasang.
    pause
    exit /b 1
)

echo [2/3] Memeriksa & Menginstal Dependensi Python Backend...
cd /d "%~dp0"
python -m pip install -r backend\requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Terjadi kendala saat instalasi pip. Melanjutkan server...
)

echo [3/3] Menjalankan Server Produksi Tunggal (Port 8000)...
echo ==========================================================
echo   SISTEM AKTIF: Akses http://localhost:8000 di browser
echo   Tekan CTRL+C untuk menghentikan server.
echo ==========================================================
python -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000
pause

