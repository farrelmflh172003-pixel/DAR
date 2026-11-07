# MENKOPOLKAM AI HUB — DEPLOYMENT READINESS CHECKLIST

**Document Version**: 1.0.0-rc1  
**Target Release**: Menkopolkam AI Hub `v2.0.0`  
**Date**: 2026-10-26  
**Auditor**: Antigravity Senior Application Security & Release Engineering Team  

---

## 1. Staging Release Checklist (Single-Worker Host)

This checklist covers all criteria required to deploy Menkopolkam AI Hub to a controlled internal staging environment.

| Status | Verification Item | Subsystem / Component | Evidence / Test Reference | Owner / Required Action |
| :---: | :--- | :--- | :--- | :--- |
| **VERIFIED** | **Backend Unit & Integration Suite** | Backend (`pytest`) | 47 passed, 0 failed, 0 skipped (`python -m pytest -v`) in 40.57s. | QA Team / Keep green on CI. |
| **VERIFIED** | **Frontend Production Build** | Frontend (`tsc` + `vite build`) | Built in 270ms; 0 type errors; bundle size 288.38 kB. | Frontend Lead / Verify assets on deploy. |
| **VERIFIED** | **JWT Algorithm Allowlisting** | `backend/utils/security.py` | `PERMITTED_JWT_ALGORITHMS = {"HS256", "RS256"}` enforced; `alg: "none"` rejected. | Security Engineer / Automated. |
| **VERIFIED** | **Single-Use Ticket Atomic Redemption** | `backend/utils/security.py` | `ConnectionTicketManager` uses `threading.Lock`; 20-worker concurrent race test passes. | Security Engineer / Automated. |
| **VERIFIED** | **Session Isolation & IDOR Defense** | `backend/orchestration/session_orchestrator.py` | Cross-user session access raises `PermissionError`; tested in `test_adversarial_cross_user_session_operations`. | Backend Lead / Automated. |
| **VERIFIED** | **Fail-Closed Startup Diagnostics** | `backend/main.py` | Startup aborts if `JWT_SECRET_KEY` $<32$ chars or default placeholder string in staging/prod. | Devops / Inject $\ge 32$-byte secret. |
| **VERIFIED** | **Multi-Worker Fail-Fast Guard** | `backend/main.py` | Startup aborts if `WORKERS > 1` without Redis shared state (`test_adversarial_multi_worker_fail_fast_guard`). | Devops / Enforce `WORKERS=1` in staging. |
| **VERIFIED** | **Audio Queue Dual Bounds & Eviction** | `backend/main.py` | Enforced at 120 items and 512 KB budget with drop-oldest eviction; memory strictly bounded. | Backend Lead / Automated. |
| **VERIFIED** | **Queue Byte Accounting & Barge-In Reset** | `backend/main.py` | Queue byte counter strictly reset to 0 on interrupt and disconnect (`test_adversarial_audio_queue_accounting_and_interrupt_purge`). | Backend Lead / Automated. |
| **VERIFIED** | **Idle Watchdog Activity Refresh** | `backend/main.py` | `last_active_time` updated on incoming audio, text, and provider streaming deltas; 120s timeout does not kill monologues. | Backend Lead / Automated. |
| **VERIFIED** | **Origin Header Security** | `backend/main.py` | Valid frontend origins accepted; unauthorized origins (`evil-attacker.com`) rejected with HTTP 403. | Devops / Configure `CORS_ORIGINS`. |
| **VERIFIED** | **Honest Provider Error Handling** | `backend/providers/` | Quota (429) and auth (401/403) errors returned honestly to UI; mock fallback strictly disabled when `ENABLE_REALTIME_MOCK=false`. | Fullstack Lead / Automated. |

---

## 2. Production Release Gate Checklist (Enterprise Clustered Deployment)

This checklist identifies the prerequisites necessary to elevate the release decision from **CONDITIONAL PASS (Staging)** to **PASS (Production Ready)**.

| Status | Production Prerequisite Item | Target Subsystem | Current State in Repository | Required Action & Evidence to Close | Action Owner |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **BLOCKED** | **OpenAI Realtime GA Paid Quota** | `backend/providers/openai_realtime_provider.py` | Fails at session creation with `credit_balance_exhausted`. | Add paid billing credits ($\ge \$5$) to OpenAI account. Close when `test_live_openai_realtime_ga_status` connects natively. | Finance / Account Admin |
| **BLOCKED** | **Google Cloud Gemini Live Bidi Whitelisting** | `backend/providers/gemini_live_provider.py` | Public AI Studio keys receive WebSocket 1008 policy violation. | Complete Google Cloud Enterprise project approval for `models/gemini-2.0-flash-exp` bi-di WebSocket endpoint. Close when native Bidi connects. | Cloud Architect / GCP Admin |
| **BLOCKED** | **Gemini Neural TTS Quota Replenishment** | `backend/providers/gemini_live_provider.py` | Experimental TTS models return HTTP 429 quota exhaustion. | Request enterprise quota tier or migrate to Google Cloud Text-to-Speech API. Close when `test_live_gemini_flash_bridge_turn_execution` delivers audio frames. | Cloud Architect / GCP Admin |
| **BLOCKED** | **Distributed Shared State Backend (Redis)** | `backend/utils/security.py` | Currently process-local in memory. Clustered multi-worker topology blocked by fail-fast startup guard. | Deploy Redis cluster; implement Redis-backed ticket storage (`SET ... EX 60 NX`) and sliding-window rate limiters. Close with multi-instance integration test. | Senior Backend Engineer |
| **UNVERIFIED** | **Enterprise Identity Provider Integration** | `backend/main.py` (`/api/auth/ticket`) | Staging validates local HMAC signatures against `JWT_SECRET_KEY`. Real IdP not connected. | Integrate with Menkopolkam enterprise SSO / IdP (Keycloak, Azure AD) via `RS256` and JWKS public key rotation. Close with live IdP login test. | IAM / Security Team |
| **UNVERIFIED** | **Enterprise Reverse Proxy & TLS 1.3 Termination** | Infrastructure Edge (Nginx / Cloudflare) | Staging tested on local loopback HTTP/WS. | Configure enterprise reverse proxy with TLS 1.3, WebSocket upgrade proxying (`proxy_read_timeout 300s`), and client-IP forwarding (`X-Forwarded-For`). | Devops / Network Team |
| **UNVERIFIED** | **Live End-to-End Voice Turn with Real Cloud Audio** | Realtime Voice Pipeline | Text inference verified; real audio generation blocked by provider quotas. | Execute full conversational voice turn (speech in $\to$ neural audio out $\to$ barge-in) using funded cloud accounts. Close with browser audio recording. | QA Lead / Audio Engineer |

---

## 3. Operational Deployment Runbook (Staging)

### Step 1: Host Preparation
```bash
# 1. Verify runtime versions
python --version   # Must be >= 3.12.0
node --version     # Must be >= v20.0.0

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Build frontend production assets
cd ../frontend
npm install
npm run build
```

### Step 2: Environment Configuration
Create `/etc/menkopolkam/aihub.env` (or `backend/.env`):
```ini
ENV=staging
HOST=127.0.0.1
PORT=8000
WORKERS=1
CORS_ORIGINS=https://aihub.staging.menkopolkam.go.id,http://localhost:5173

# Security & Authentication
AUTH_ENABLED=true
ALLOW_ANONYMOUS_DEV=false
JWT_SECRET_KEY=<GENERATE_MIN_32_BYTES_CRYPTOGRAPHIC_RANDOM_SECRET>
JWT_ALGORITHM=HS256
JWT_ISSUER=menkopolkam-ai-hub
JWT_AUDIENCE=menkopolkam-web
TICKET_TTL_SECONDS=60
MAX_CONCURRENT_SESSIONS_PER_USER=2
MAX_FAILED_HANDSHAKES_PER_IP=10
SESSION_IDLE_TIMEOUT_SECONDS=120
TRUSTED_PROXIES=127.0.0.1,10.0.0.1

# Provider Keys
OPENAI_API_KEY=<REDACTED_OPENAI_KEY>
GEMINI_API_KEY=<REDACTED_GEMINI_KEY>
ENABLE_REALTIME_MOCK=false
```

### Step 3: Service Startup (Single-Worker Mode)
```bash
# Start backend service using Uvicorn (Strictly 1 worker)
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1
```

### Step 4: Health Verification
```bash
# Verify health check returns operational
curl -s http://127.0.0.1:8000/api/health
# Expected output: {"status":"operational","application":"MENKOPOLKAM AI HUB",...}
```
