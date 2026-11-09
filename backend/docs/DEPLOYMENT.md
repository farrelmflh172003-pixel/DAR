# MENKOPOLKAM AI HUB — OPERATIONAL & DEPLOYMENT GUIDE

## 1. Overview & Architecture

MENKOPOLKAM AI HUB is an analytical diplomacy, geopolitical translation, and real-time bidirectional voice synthesis platform designed for controlled internal government environments.
The system is built on a high-speed decoupled architecture:
- **Frontend**: React 19 / TypeScript / Vite / Web Audio API AudioWorklet for low-latency full-duplex audio capture & playback.
- **Backend**: FastAPI / Python 3.12 / ASGI / WebSockets for duplex session orchestration, stateful Catmull-Rom audio resampling (16kHz $\leftrightarrow$ 24kHz), live web grounding with prompt injection defenses, and honest provider adapters (Gemini Live & OpenAI Realtime).

---

## 2. Configuration & Required Environment Variables

All sensitive values must be provided via protected environment variables or injected from a secure secret store (e.g., Vault, AWS Secrets Manager, Kubernetes Secrets). **Never commit production credentials or API keys to source control.**

### Staging & Production Configuration Template

```bash
# ==========================================
# Application Environment & Network
# ==========================================
ENV=staging                              # "development", "staging", or "production"
HOST=0.0.0.0                             # Bind host for ASGI runner (e.g., Uvicorn)
PORT=8000                                # Internal listening port
CORS_ORIGINS=https://aihub.menkopolkam.go.id,https://staging-aihub.menkopolkam.go.id

# ==========================================
# Authentication & Access Control
# ==========================================
AUTH_ENABLED=true                        # Enforce JWT validation and single-use tickets
ALLOW_ANONYMOUS_DEV=false                # STRICTLY FALSE in staging & production
JWT_SECRET_KEY=REPLACE_WITH_MIN_32_BYTES_CRYPTOGRAPHIC_RANDOM_SECRET
JWT_ALGORITHM=HS256                      # HS256 or RS256
JWT_ISSUER=menkopolkam-ai-hub
JWT_AUDIENCE=menkopolkam-web
TICKET_TTL_SECONDS=60                    # Single-use connection ticket expiration (seconds)

# ==========================================
# Abuse Prevention & Rate Limits
# ==========================================
MAX_CONCURRENT_SESSIONS_PER_USER=2       # Max concurrent voice sessions per user
MAX_FAILED_HANDSHAKES_PER_IP=10          # Failed connection threshold before IP block
SESSION_IDLE_TIMEOUT_SECONDS=120         # Inactivity timeout before graceful disconnection
TRUSTED_PROXIES=127.0.0.1,10.0.0.1        # Reverse proxies permitted for X-Forwarded-For
RATE_LIMIT_SWITCH_PROVIDER=5             # Max provider switches per 30-second window
MAX_AUDIO_CHUNK_BYTES=524288             # 512 KB max binary PCM audio frame

# ==========================================
# External AI Model Integrations
# ==========================================
OPENAI_API_KEY=sk-proj-...               # OpenAI API Key with Realtime API entitlement
OPENAI_REALTIME_MODEL=gpt-realtime-mini  # or gpt-realtime
GEMINI_API_KEY=AQ....                    # Google Cloud / AI Studio API Key
GEMINI_LIVE_MODEL=models/gemini-2.0-flash-exp

# ==========================================
# Mock Fallback Control
# ==========================================
ENABLE_REALTIME_MOCK=false               # Strictly false in staging/prod. Only true for offline dev.
```

---

## 3. Authentication & Access Control Flow

To eliminate credential exposure in URLs, browser history, and reverse proxy access logs:

1. **Ticket Exchange (`POST /api/auth/ticket`)**:
   - The authenticated client issues an HTTP POST request carrying its Identity Provider (IdP) access token in the header:
     ```http
     POST /api/auth/ticket HTTP/1.1
     Host: aihub.menkopolkam.go.id
     Authorization: Bearer <IDP_ACCESS_TOKEN>
     ```
   - The backend validates the signature, `exp`, `iss`, and `aud` against `JWT_SECRET_KEY`.
   - Upon successful verification, the server issues a cryptographically random, single-use ticket valid for 60 seconds:
     ```json
     {
       "ticket": "9V_x...32_bytes_urlsafe...",
       "expires_in": 60,
       "user_id": "analyst-049"
     }
     ```

2. **WebSocket Handshake (`/ws/realtime-session?ticket=<TICKET>`)**:
   - The browser opens the WebSocket passing `?ticket=<TICKET>`.
   - The server verifies and **immediately redeems (invalidates)** the ticket from the ticket store.
   - **Replay Protection**: Any subsequent connection attempt using the same ticket fails with `1008 Policy Violation`.
   - The WebSocket session is strictly bound to the authenticated `user_id`. Any attempt to hijack an existing `session_id` belonging to another user raises `PermissionError` and terminates the connection.

---

## 4. Reverse Proxy & TLS Requirements

The application relies on an enterprise reverse proxy (e.g., Nginx, Envoy, Traefik) to terminate TLS.

### TLS / Reverse Proxy Guidelines
- **TLS Version**: TLS 1.3 (or TLS 1.2 with AEAD ciphers).
- **HTTP/2 & WebSocket Upgrade**: The proxy must support standard `Connection "Upgrade"` and `Upgrade "websocket"` headers.
- **Client IP Preservation**:
  - The proxy must append the client's direct IP to `X-Forwarded-For`.
  - The backend only trusts `X-Forwarded-For` if the immediate upstream connecting IP matches `TRUSTED_PROXIES`.
- **Timeouts**: Configure proxy proxy-read-timeout to at least 300 seconds to prevent premature WebSocket termination during long pauses:
  ```nginx
  proxy_read_timeout 300s;
  proxy_send_timeout 300s;
  ```

### Sample Nginx Configuration Snippet
```nginx
server {
    listen 443 ssl http2;
    server_name aihub.menkopolkam.go.id;

    ssl_certificate /etc/ssl/certs/menkopolkam.crt;
    ssl_certificate_key /etc/ssl/private/menkopolkam.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        root /var/www/menkopolkam-frontend/dist;
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 5. Provider Quotas, Permissions & Failure Modes

| Provider Path | Protocol | Prerequisite | Behavior on Quota / Billing Exhaustion |
| :--- | :--- | :--- | :--- |
| **OpenAI Realtime GA** | WebSocket (`wss://api.openai.com/v1/realtime`) | Active API credit balance ($\ge \$5$) | Immediately reports `error` with actionable notice: `"OpenAI Realtime quota exceeded (credit_balance_exhausted)"`. Never falls back to mock unless `ENABLE_REALTIME_MOCK=true`. |
| **Gemini Live (Native Bidi)** | WebSocket (`wss://generativelanguage.googleapis.com/...BidiGenerateContent`) | Google Cloud Enterprise Project whitelisting | Public keys receive `1008 policy violation`. Adapter automatically engages Flash Streaming Bridge fallback with explicit disclosure. |
| **Gemini Flash Streaming Bridge** | REST (`gemini-flash-lite`) + Neural TTS (`gemini-*-flash-tts`) | Google Cloud Gemini Text & Audio quota | Text generates in $\sim 450\text{ms}$. If TTS quota is exceeded (HTTP 429), reports honest error: `"Streaming bridge audio generation failed: Gemini TTS quota exceeded (HTTP 429)"`. |

---

## 6. Health Checks, Monitoring & Telemetry

### Health Check Endpoint: `GET /api/health`
- Returns operational readiness without disclosing API keys, secrets, or internal paths:
  ```json
  {
    "status": "operational",
    "application": "MENKOPOLKAM AI HUB",
    "integrations": {
      "openai": { "configured": true, "service": "OpenAI GPT-4o" },
      "gemini": { "configured": true, "service": "Gemini 1.5 Pro/Flash" }
    },
    "mode": "live_api"
  }
  ```

### Telemetry & Privacy Safeguards
- **Zero Raw Audio Logging**: Audio byte streams (PCM16) are streamed directly into memory buffers and never written to disk or logged.
- **Zero Secret Exposure**: Tokens, tickets, and keys are masked from all console and application logs.
- **Latency Monitoring**: Each turn reports `last_turn_latency_ms`, `median_latency_ms`, `p95_latency_ms`, and `last_barge_in_ms`.

---

## 7. Startup, Shutdown & Rollback

### Supported Worker Topology & State Management
- **Single-Worker Topology (Validated Staging)**:
  - Command: `python -m uvicorn main:app --host 127.0.0.1 --port 8000` or `uvicorn main:app --workers 1`.
  - In this topology, `ConnectionTicketManager`, `HandshakeAbuseTracker`, and `PerUserConnectionTracker` run thread-safely in-memory with zero network overhead and zero external dependencies.
  - This topology is fully tested, verified, and approved for controlled internal staging.
- **Multi-Worker Clustered Topology (Production Scale)**:
  - When scaling horizontally across multiple Uvicorn/Gunicorn workers or Kubernetes pods, in-memory state cannot be shared between separate OS processes.
  - **Prerequisite**: Deploy a Redis instance (`REDIS_URL=redis://...`) to host distributed single-use ticket sets (`SET ... EX 60 NX`) and sliding-window rate limiters.
  - In the absence of Redis, traffic MUST be pinned to a single worker process or routed with strict sticky sessions.

---

## 8. Fail-Closed Startup Diagnostics

In staging and production (`ENV in ("staging", "production")`):
- The application performs pre-flight invariant validation in `@app.on_event("startup")`:
  1. `AUTH_ENABLED` must be strictly `True`.
  2. `ALLOW_ANONYMOUS_DEV` must be strictly `False`.
  3. `JWT_SECRET_KEY` must be configured and contain at least 32 cryptographically secure characters.
  4. Known default/placeholder keys (e.g., `secret`, `changeme`, `your_secret_key`) are immediately rejected.
  5. `WORKERS` must be strictly `1`. Starting with `WORKERS > 1` raises `RuntimeError` (`CRITICAL TOPOLOGY ERROR`) and halts the process immediately. The guard inspects `WORKERS`, `WEB_CONCURRENCY`, and CLI arguments (`--workers`).
- **Multi-Instance Disclaimer**: A single-worker process configuration (`WORKERS=1`) guarantees safety only within that single process. It does **not** provide safety if an operator deploys multiple container replicas or instances behind a round-robin load balancer without sticky sessions. Multi-instance horizontal scaling strictly requires a Redis shared backend.
- **Fail-Closed Behavior**: If any check fails, startup raises `SecurityError` or `RuntimeError` and immediately halts execution with an explicit error code. The application never boots in an unauthenticated or insecure state. Secrets are never printed in diagnostic error messages.

---

## 9. Secret Rotation & Incident Response

### Secret Rotation Procedure
1. **JWT Secret Key Rotation**:
   - For HMAC keys (`HS256`):
     - Transition to key-rotation dual-verification if supported, or schedule a maintenance window.
     - Generate a new 32+ byte cryptographic random string: `openssl rand -base64 32`.
     - Update `JWT_SECRET_KEY` in environment secret store.
     - Restart backend service. Active WebSocket connections will continue until session completion or 120s idle timeout; new handshakes will require tokens signed with the new secret.
   - For Asymmetric keys (`RS256`):
     - Rotate private key on Identity Provider; distribute updated public JWKS URI to backend.
2. **Provider API Key Rotation**:
   - Generate new API keys in OpenAI Platform and Google Cloud Console.
   - Update `OPENAI_API_KEY` and `GEMINI_API_KEY`.
   - Reload backend workers (`kill -HUP <pid>` or rolling restart). Zero client session interruption if using connection ticket persistence.

### Security Incident Response Plan
- **Compromised JWT Secret**:
  - Immediately rotate `JWT_SECRET_KEY` in production secrets manager.
  - Restart all worker processes to invalidate all pending connection tickets.
  - Flush all active WebSocket connections: `pkill -f "uvicorn main:app"`.
- **IP Flooding / Brute Force Attack**:
  - `HandshakeAbuseTracker` automatically locks out offending client IPs for 300 seconds after 10 failed handshakes.
  - If attack traverses upstream CDN/proxy, inspect sanitized reverse proxy logs for real client IPs and apply firewall drop rules at the edge:
    ```bash
    sudo iptables -A INPUT -s <ATTACKER_IP> -j DROP
    ```
- **Provider Quota Depletion**:
  - If alerts trigger for HTTP 429 (`credit_balance_exhausted`), verify billing status in OpenAI / Google Cloud dashboards.
  - The system will automatically return sanitized error messages to users without crashing or falling back to mocks.

---

## 10. Startup, Shutdown & Rollback

### Production Startup (Uvicorn / Gunicorn)
```bash
# Using Gunicorn with Uvicorn Worker (Single-worker validated baseline)
gunicorn main:app \
  --workers 1 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 127.0.0.1:8000 \
  --access-logfile - \
  --error-logfile -
```

### Graceful Shutdown
Upon receiving `SIGTERM` or `SIGINT`, the ASGI server drains open WebSocket connections, cancels pending tasks, shuts down active provider streaming tasks, and closes clean.

### Rollback Procedure
1. Revert Git tag/commit to the previous validated release tag.
2. Re-run `pip install -r requirements.txt` and `npm run build`.
3. Restart backend service via `systemctl restart menkopolkam-backend`.
4. Verify `/api/health` responds HTTP 200 with `"status": "operational"`.

