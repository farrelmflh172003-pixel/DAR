#!/usr/bin/env bash
# ==============================================================================
# MENKOPOLKAM AI HUB - 1-Click Production Deployment Script (Linux VPS / Server)
# ==============================================================================

set -e

echo "=========================================================="
echo "  🚀 MENKOPOLKAM AI HUB - PROD DEPLOYMENT SETUP"
echo "=========================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker belum terpasang. Silakan pasang Docker terlebih dahulu:"
    echo "   curl -fsSL https://get.docker.com | sh"
    echo "   sudo usermod -aG docker \$USER"
    exit 1
fi

# Determine docker compose command (v2 'docker compose' or v1 'docker-compose')
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "❌ Docker Compose plugin belum terpasang."
    exit 1
fi

# Ensure .env exists
if [ ! -f .env ]; then
    echo "⚠️ File .env tidak ditemukan. Menyalin dari .env.example..."
    cp .env.example .env
    echo "✅ File .env berhasil dibuat."
    echo "👉 PENTING: Edit file .env untuk mengisi GEMINI_API_KEY sebelum digunakan:"
    echo "   nano .env"
fi

# Build and Start Containers
echo ""
echo "📦 Membangun image Docker dan memulai container..."
$COMPOSE_CMD down || true
$COMPOSE_CMD up -d --build

# Healthcheck loop
echo "⏳ Menunggu verifikasi kesiapan layanan (Healthcheck)..."
MAX_ATTEMPTS=20
COUNT=0
READY=false

while [ $COUNT -lt $MAX_ATTEMPTS ]; do
    if curl -s http://localhost:8000/api/health | grep -q "status"; then
        READY=true
        break
    fi
    COUNT=$((COUNT+1))
    sleep 2
done

if [ "$READY" = true ]; then
    SERVER_IP=$(curl -s https://api.ipify.org || hostname -I | awk '{print $1}')
    echo ""
    echo "=========================================================="
    echo "  ✅ DEPLOYMENT BERHASIL & SISTEM AKTIF!"
    echo "=========================================================="
    echo "  🌐 URL Akses Web & API: http://$SERVER_IP:8000"
    echo "  📊 Health Check       : http://$SERVER_IP:8000/api/health"
    echo "  📚 API Docs (Swagger) : http://$SERVER_IP:8000/docs"
    echo "=========================================================="
    echo "Perintah Pengelolaan Berguna:"
    echo "  - Cek Log Realtime : $COMPOSE_CMD logs -f menkopolkam-app"
    echo "  - Restart Layanan  : $COMPOSE_CMD restart"
    echo "  - Hentikan Layanan : $COMPOSE_CMD down"
    echo "=========================================================="
else
    echo "⚠️ Layanan membutuhkan waktu lebih lama untuk inisialisasi."
    echo "Silakan pantau log dengan perintah:"
    echo "   $COMPOSE_CMD logs -f menkopolkam-app"
fi

