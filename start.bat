@echo off
title MENKOPOLKAM AI HUB Launcher
echo ========================================================
echo       MENKOPOLKAM AI HUB - Coordinating Minister AI
echo ========================================================
echo Memeriksa dan membersihkan port 8000 dan 5173...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

echo Starting FastAPI Backend (Port 8000)...
start "Menkopolkam Backend (Port 8000)" cmd /k "cd /d "%~dp0" && python -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload"

echo Starting Vite React Frontend (Port 5173)...
start "Menkopolkam Frontend (Port 5173)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo Menunggu inisialisasi server...
powershell -nop -c "Start-Sleep -Seconds 3" >nul 2>&1
start http://localhost:5173/

echo ========================================================
echo Layanan Menkopolkam AI Hub berhasil dijalankan!
echo - Frontend: http://localhost:5173/
echo - Backend:  http://127.0.0.1:8000/
echo ========================================================
