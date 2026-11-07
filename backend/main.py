import os
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger("menkopolkam.operational")

from config import settings
from utils.security import (
    verify_access_token,
    create_access_token,
    ticket_manager,
    handshake_tracker,
    user_tracker,
    rate_limiter,
    ip_resolver,
    AuthenticationError,
    SecurityError
)
from models import (
    DiplomaticResponseSet,
    ProcessRequest,
    SelectAnswerRequest,
    EnglishResponse,
    CanonicalQuestion,
    AIAnswerBundle
)
from scenarios import DIPLOMATIC_SCENARIOS
from services.ai_orchestrator import (
    process_live_question_fast,
    generate_gemini_tts,
    detect_language_simple,
    detect_language_universal,
    get_language_display_name,
    translate_text_universal
)
from orchestration.session_orchestrator import session_orchestrator
from services.grounding_tool import grounding_tool
from services.document_parser import extract_text_from_file_bytes
from services.captcha_service import captcha_service
from services.user_service import user_service
from services.saved_file_service import saved_file_service


app = FastAPI(
    title="MENKOPOLKAM AI HUB API",
    description="Universal AI Translator and Analytical Engine",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def validate_staging_and_production_security_invariants():
    """Fails closed immediately upon startup if staging or production environment is insecurely configured."""
    if settings.ENV.lower() in ("staging", "production"):
        if not settings.AUTH_ENABLED:
            raise RuntimeError("CRITICAL SECURITY ERROR: AUTH_ENABLED cannot be False in staging or production mode.")
        if settings.ALLOW_ANONYMOUS_DEV:
            raise RuntimeError("CRITICAL SECURITY ERROR: ALLOW_ANONYMOUS_DEV cannot be True in staging or production mode.")
        if not settings.JWT_SECRET_KEY or len(settings.JWT_SECRET_KEY) < 32 or "insecure" in settings.JWT_SECRET_KEY.lower():
            raise RuntimeError("CRITICAL SECURITY ERROR: Weak, insecure, or missing JWT_SECRET_KEY in staging or production mode.")
        if settings.WORKERS > 1:
            raise RuntimeError(
                f"CRITICAL TOPOLOGY ERROR: Multi-worker configuration (WORKERS={settings.WORKERS}) is strictly forbidden. "
                f"In-memory tickets, rate limiters, and connection trackers cannot be shared across multiple processes without a distributed Redis backend. "
                f"Deploy with a single worker (WORKERS=1)."
            )

active_connections: List[WebSocket] = []

class KeyUpdateRequest(BaseModel):
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "Kore"

class DocumentExtractRequest(BaseModel):
    filename: str
    file_base64: str

class TicketRequest(BaseModel):
    token: Optional[str] = None

@app.post("/api/auth/ticket")
async def create_connection_ticket(request: Request, payload: Optional[TicketRequest] = None):
    """
    Exchanges an authenticated JWT Bearer token for a short-lived (60s),
    single-use WebSocket connection ticket.
    Protects long-lived tokens from being logged in URLs or WebSocket query parameters.
    """
    client_host = request.client.host if request.client else "127.0.0.1"
    client_ip = ip_resolver.resolve_client_ip(dict(request.headers), client_host)

    # Rate limit ticket issuance requests per IP (max 30 tickets per minute)
    if not rate_limiter.check_and_record(f"ticket_rate:{client_ip}", max_requests=30, window_seconds=60.0):
        logger.warning("Ticket issuance rate limit exceeded for client_ip=%s", client_ip)
        raise HTTPException(
            status_code=429,
            detail="Too many ticket issuance requests. Rate limit exceeded."
        )

    auth_header = request.headers.get("authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif payload and payload.token:
        token = payload.token.strip()

    if not token:
        if not settings.AUTH_ENABLED or (settings.ALLOW_ANONYMOUS_DEV and settings.ENV == "development"):
            # Local development fallback
            dev_ticket = ticket_manager.create_ticket(user_id="dev-operator", role="operator")
            logger.info("Anonymous dev connection ticket issued for client_ip=%s", client_ip)
            return {
                "ticket": dev_ticket,
                "expires_in": settings.TICKET_TTL_SECONDS,
                "user_id": "dev-operator",
                "mode": "dev_anonymous"
            }
        logger.info("Ticket request rejected: missing bearer token from client_ip=%s", client_ip)
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization: Bearer <token> for connection ticket creation."
        )

    try:
        claims = verify_access_token(token)
        user_id = claims["sub"]
        role = claims.get("role", "operator")
        scopes = claims.get("scopes", [])
        ticket = ticket_manager.create_ticket(user_id=user_id, role=role, scopes=scopes)
        logger.info("Authenticated connection ticket issued for user=%s role=%s client_ip=%s", user_id, role, client_ip)
        return {
            "ticket": ticket,
            "expires_in": settings.TICKET_TTL_SECONDS,
            "user_id": user_id
        }
    except AuthenticationError as ae:
        logger.warning("Ticket issuance failed (invalid token) from client_ip=%s: %s", client_ip, ae)
        raise HTTPException(status_code=401, detail=f"Authentication token invalid: {ae}")

@app.post("/api/auth/dev-token")
async def get_development_token():
    """Generates a valid test JWT for local operator testing. Disabled in staging/production."""
    if settings.ENV != "development":
        raise HTTPException(
            status_code=403,
            detail="Development token generation is strictly disabled in staging and production environments."
        )
    test_token = create_access_token(sub="operator-diplomat", role="diplomat")
    return {
        "token": test_token,
        "expires_in": 3600,
        "env": "development"
    }

@app.get("/api/health")
async def health_check():
    openai_ready = bool(settings.OPENAI_API_KEY)
    gemini_ready = bool(settings.GEMINI_API_KEY)
    return {
        "status": "operational",
        "application": settings.APP_NAME,
        "integrations": {
            "openai": {"configured": openai_ready, "service": "OpenAI GPT-4o" if openai_ready else "Key Not Set"},
            "gemini": {"configured": gemini_ready, "service": "Gemini 1.5 Pro/Flash" if gemini_ready else "Key Not Set"}
        },
        "mode": "live_api" if (openai_ready or gemini_ready) else "ready_for_keys"
    }

@app.post("/api/settings/keys")
async def update_api_keys(payload: KeyUpdateRequest):
    if payload.openai_api_key is not None:
        settings.OPENAI_API_KEY = payload.openai_api_key.strip()
    if payload.gemini_api_key is not None:
        settings.GEMINI_API_KEY = payload.gemini_api_key.strip()

    env_path = Path(__file__).parent / ".env"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"OPENAI_API_KEY={settings.OPENAI_API_KEY}\n")
        f.write(f"GEMINI_API_KEY={settings.GEMINI_API_KEY}\n")
        f.write("ENV=production\n")

    return {
        "status": "success",
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "gemini_configured": bool(settings.GEMINI_API_KEY)
    }

@app.get("/api/scenarios")
async def list_scenarios():
    return {
        "active_id": "natuna_unclos",
        "scenarios": [
            {
                "id": key,
                "title": val.canonical_question.original_text[:65] + "...",
                "speaker": val.canonical_question.speaker,
                "timestamp": val.canonical_question.timestamp
            }
            for key, val in DIPLOMATIC_SCENARIOS.items()
        ]
    }

@app.get("/api/saved-files")
async def list_saved_files(sort_order: str = "oldest_first"):
    """Lists all saved, listed, and documented session files. Defaults to oldest first."""
    return saved_file_service.list_files(sort_order=sort_order)

@app.get("/api/saved-files/{file_id}")
async def get_saved_file(file_id: str):
    """Retrieves a single documented saved file by ID."""
    f = saved_file_service.get_file(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    return f

@app.post("/api/saved-files")
async def save_session_file(payload: Dict[str, Any]):
    """Saves a new session file into the documented archive."""
    return saved_file_service.create_file(payload)

@app.put("/api/saved-files/{file_id}")
async def update_saved_file(file_id: str, payload: Dict[str, Any]):
    """Edits and updates an existing saved file."""
    updated = saved_file_service.update_file(file_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    return updated

@app.delete("/api/saved-files/{file_id}")
async def delete_saved_file(file_id: str):
    """Deletes a saved file from the archive."""
    success = saved_file_service.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")
    return {"status": "success", "message": "Dokumen berhasil dihapus"}

@app.get("/api/session/{scenario_id}", response_model=DiplomaticResponseSet)
async def get_session(scenario_id: str):
    if scenario_id in DIPLOMATIC_SCENARIOS:
        return DIPLOMATIC_SCENARIOS[scenario_id]
    # Check if exists in saved files
    sf = saved_file_service.get_file(scenario_id)
    if sf:
        cq = CanonicalQuestion(
            id=sf.get("id", scenario_id),
            original_text=sf.get("original_audio_text", ""),
            detected_language=sf.get("detected_language", "auto"),
            detected_language_name=sf.get("detected_language_name", "Otomatis"),
            timestamp=sf.get("timestamp", ""),
            speaker=sf.get("speaker", "Delegasi"),
            uncertain_words=[]
        )
        answers = sf.get("ai_answers", {})
        cg_answers = sf.get("chatgpt_answers") or sf.get("ai_answers", {})
        gem_answers = sf.get("gemini_answers") or sf.get("ai_answers", {})
        c_bundle = AIAnswerBundle(
            main_answer=cg_answers.get("main_answer", ""),
            concise_answer=cg_answers.get("concise_answer", ""),
            brief_analysis=cg_answers.get("brief_analysis", ""),
            monitoring_issues=cg_answers.get("monitoring_issues", ""),
            resolution_recommendations=cg_answers.get("resolution_recommendations", ""),
            kemenko_role=cg_answers.get("kemenko_role", ""),
            field_monitoring_agenda=cg_answers.get("field_monitoring_agenda", ""),
            latest_news=cg_answers.get("latest_news", ""),
            model_version="ChatGPT"
        )
        g_bundle = AIAnswerBundle(
            main_answer=gem_answers.get("main_answer", ""),
            concise_answer=gem_answers.get("concise_answer", ""),
            brief_analysis=gem_answers.get("brief_analysis", ""),
            monitoring_issues=gem_answers.get("monitoring_issues", ""),
            resolution_recommendations=gem_answers.get("resolution_recommendations", ""),
            kemenko_role=gem_answers.get("kemenko_role", ""),
            field_monitoring_agenda=gem_answers.get("field_monitoring_agenda", ""),
            latest_news=gem_answers.get("latest_news", ""),
            model_version="Gemini"
        )
        return DiplomaticResponseSet(
            canonical_question=cq,
            canonical_translation_id=sf.get("translated_indonesian_text", ""),
            chatgpt=c_bundle,
            gemini=g_bundle,
            english_translations={},
            is_live_grounded=True,
            live_sources=[],
            latest_update_time=sf.get("timestamp", ""),
            selected_answer=sf.get("selected_answer", "") or c_bundle.main_answer
        )
    return DIPLOMATIC_SCENARIOS["natuna_unclos"]

@app.post("/api/process", response_model=DiplomaticResponseSet)
async def process_question(payload: ProcessRequest):
    now_str = time.strftime("%H:%M:%S WIB")
    
    if payload.detected_language and payload.detected_language not in ("auto", "null", ""):
        detected_lang = payload.detected_language
        detected_name = get_language_display_name(detected_lang)
    else:
        detected_lang, detected_name = detect_language_universal(payload.question_text)

    # 1. Real-time Live synthesis grounded with authentic web/news data & attached Knowledge AI
    has_knowledge = bool(payload.knowledge_context and payload.knowledge_context.strip())
    canonical_id, chatgpt_bundle, gemini_bundle, english_translations, live_sources, is_grounded, final_lang, final_name, is_knowledge_relevant = await process_live_question_fast(
        payload.question_text,
        detected_lang,
        detected_name,
        knowledge_context=payload.knowledge_context,
        attachment_name=payload.attachment_name
    )
    
    canonical_q = CanonicalQuestion(
        id=f"live-{int(time.time())}",
        original_text=payload.question_text,
        detected_language=final_lang,
        detected_language_name=final_name,
        timestamp=now_str,
        speaker=payload.speaker or "Delegasi / Penanya",
        uncertain_words=[]
    )

    result = DiplomaticResponseSet(
        canonical_question=canonical_q,
        canonical_translation_id=canonical_id,
        chatgpt=chatgpt_bundle,
        gemini=gemini_bundle,
        english_translations=english_translations,
        is_live_grounded=is_grounded or is_knowledge_relevant,
        live_sources=live_sources,
        latest_update_time=now_str,
        knowledge_applied=is_knowledge_relevant,
        attachment_name=payload.attachment_name if is_knowledge_relevant else None,
        selected_answer=chatgpt_bundle.main_answer or gemini_bundle.main_answer
    )

    # Auto-save to saved_files storage for immediate listed and documented access
    try:
        title_summary = (canonical_id[:60] + "...") if len(canonical_id) > 60 else (canonical_id or canonical_q.original_text[:60])
        saved_file_service.create_file({
            "id": canonical_q.id,
            "title": title_summary or f"Dokumen Sesi {now_str}",
            "timestamp": now_str,
            "speaker": canonical_q.speaker,
            "original_audio_text": canonical_q.original_text,
            "detected_language": final_lang,
            "detected_language_name": final_name,
            "translated_indonesian_text": canonical_id,
            "knowledge_applied": is_knowledge_relevant,
            "attachment_name": payload.attachment_name if is_knowledge_relevant else None,
            "ai_answers": {
                "main_answer": gemini_bundle.main_answer or chatgpt_bundle.main_answer,
                "concise_answer": gemini_bundle.concise_answer or chatgpt_bundle.concise_answer,
                "brief_analysis": gemini_bundle.brief_analysis or chatgpt_bundle.brief_analysis,
                "monitoring_issues": gemini_bundle.monitoring_issues or chatgpt_bundle.monitoring_issues,
                "resolution_recommendations": gemini_bundle.resolution_recommendations or chatgpt_bundle.resolution_recommendations,
                "kemenko_role": gemini_bundle.kemenko_role or chatgpt_bundle.kemenko_role,
                "field_monitoring_agenda": gemini_bundle.field_monitoring_agenda or chatgpt_bundle.field_monitoring_agenda,
                "latest_news": gemini_bundle.latest_news or chatgpt_bundle.latest_news,
                "model_version": "GPT-4o & Gemini 1.5 Pro Hybrid"
            },
            "chatgpt_answers": {
                "main_answer": chatgpt_bundle.main_answer,
                "concise_answer": chatgpt_bundle.concise_answer,
                "brief_analysis": chatgpt_bundle.brief_analysis,
                "monitoring_issues": chatgpt_bundle.monitoring_issues,
                "resolution_recommendations": chatgpt_bundle.resolution_recommendations,
                "kemenko_role": chatgpt_bundle.kemenko_role,
                "field_monitoring_agenda": chatgpt_bundle.field_monitoring_agenda,
                "latest_news": chatgpt_bundle.latest_news,
                "model_version": "ChatGPT"
            },
            "gemini_answers": {
                "main_answer": gemini_bundle.main_answer,
                "concise_answer": gemini_bundle.concise_answer,
                "brief_analysis": gemini_bundle.brief_analysis,
                "monitoring_issues": gemini_bundle.monitoring_issues,
                "resolution_recommendations": gemini_bundle.resolution_recommendations,
                "kemenko_role": gemini_bundle.kemenko_role,
                "field_monitoring_agenda": gemini_bundle.field_monitoring_agenda,
                "latest_news": gemini_bundle.latest_news,
                "model_version": "Gemini"
            },
            "selected_answer": chatgpt_bundle.main_answer or gemini_bundle.main_answer,
            "notes": "Sesi transkripsi otomatis tercatat secara live."
        })
    except Exception as e:
        logger.warning("Auto-save file warning: %s", e)


    for conn in active_connections:
        try:
            await conn.send_text(result.model_dump_json())
        except Exception:
            pass

    return result

class TranslateColumnRequest(BaseModel):
    text: str
    target_lang: Optional[str] = "id"
    source_lang: Optional[str] = "auto"

@app.post("/api/translate")
async def translate_column_text(payload: TranslateColumnRequest):
    """Translates any column text to target_lang from source_lang with markdown format preservation."""
    if not payload.text or not payload.text.strip():
        return {
            "translated_text": "",
            "target_lang": payload.target_lang or "id",
            "source_lang": payload.source_lang or "auto"
        }
    translated = await translate_text_universal(
        payload.text, 
        payload.target_lang or "id",
        payload.source_lang or "auto"
    )
    return {
        "translated_text": translated,
        "target_lang": payload.target_lang or "id",
        "source_lang": payload.source_lang or "auto"
    }

@app.post("/api/translate-selection", response_model=EnglishResponse)
async def translate_selection(payload: SelectAnswerRequest):
    type_labels = {
        "main": "Jawaban Utama",
        "concise": "Jawaban Singkat",
        "analysis": "Analisis Singkat"
    }
    label = type_labels.get(payload.answer_type, "Jawaban")
    translated = await translate_text_universal(payload.indonesian_text, target_lang="en", source_lang="id")
        
    return EnglishResponse(
        card_id=payload.card_id,
        source_ai="ChatGPT" if payload.source_ai.lower() == "chatgpt" else "Gemini",
        answer_type_label=label,
        english_text=translated
    )

@app.post("/api/tts")
async def text_to_speech(payload: TTSRequest):
    wav = await generate_gemini_tts(payload.text, payload.voice or "Kore")
    if not wav:
        raise HTTPException(status_code=500, detail="Gagal mensintesis suara Gemini TTS")
    return Response(content=wav, media_type="audio/wav")

@app.post("/api/document/extract")
async def extract_document(payload: DocumentExtractRequest):
    import base64
    try:
        data = base64.b64decode(payload.file_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Data file base64 tidak valid: {str(e)}")
    
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Ukuran file melebihi batas maksimum 25MB.")
        
    try:
        result = extract_text_from_file_bytes(data, payload.filename)
        return result
    except Exception as e:
        logger.exception("Document extraction error")
        raise HTTPException(status_code=500, detail=f"Gagal memproses dokumen: {str(e)}")

@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            for conn in active_connections:
                if conn != websocket:
                    await conn.send_text(data)
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.websocket("/ws/realtime-session")
async def realtime_voice_session_endpoint(websocket: WebSocket):
    # 1. Strict Origin Validation
    client_host = websocket.client.host if websocket.client else "127.0.0.1"
    headers_dict = dict(websocket.headers)
    client_ip = ip_resolver.resolve_client_ip(headers_dict, client_host)

    origin = websocket.headers.get("origin", "")
    if origin:
        origin_clean = origin.rstrip("/")
        if settings.ENV == "development":
            allowed = any(
                origin_clean == allowed_origin.rstrip("/") or
                origin_clean.startswith("http://localhost:") or
                origin_clean.startswith("http://127.0.0.1:")
                for allowed_origin in settings.CORS_ORIGINS
            )
        else:
            allowed = any(origin_clean == allowed_origin.rstrip("/") for allowed_origin in settings.CORS_ORIGINS)

        if not allowed:
            logger.warning("WebSocket handshake rejected: unauthorized origin '%s' from client_ip=%s", origin, client_ip)
            handshake_tracker.record_failure(client_ip)
            await websocket.close(code=1008, reason="Origin not allowed")
            return

    # 2. Handshake Abuse & Rate Limiting Check
    if handshake_tracker.is_blocked(client_ip):
        logger.warning("WebSocket handshake rejected: client_ip=%s is blocked due to excessive failed attempts", client_ip)
        await websocket.close(code=1008, reason="Rate limit exceeded: too many failed handshake attempts.")
        return

    # 3. Authentication & Single-Use Ticket Redemption
    ticket = websocket.query_params.get("ticket")
    user_id = None
    user_role = "operator"

    if ticket:
        ticket_data = ticket_manager.redeem_ticket(ticket)
        if not ticket_data:
            logger.warning("WebSocket handshake rejected: invalid, expired, or replayed ticket from client_ip=%s", client_ip)
            handshake_tracker.record_failure(client_ip)
            await websocket.close(code=1008, reason="Invalid, expired, or already used connection ticket.")
            return
        user_id = ticket_data["user_id"]
        user_role = ticket_data.get("role", "operator")
    elif settings.AUTH_ENABLED:
        if settings.ALLOW_ANONYMOUS_DEV and settings.ENV == "development":
            user_id = f"dev-anon-{client_ip}"
        else:
            logger.warning("WebSocket handshake rejected: missing connection ticket from client_ip=%s", client_ip)
            handshake_tracker.record_failure(client_ip)
            await websocket.close(code=1008, reason="Authentication required: valid connection ticket missing.")
            return
    else:
        user_id = f"dev-anon-{client_ip}"

    # 4. Per-User Concurrent Connection Limit Check
    if not user_tracker.can_connect(user_id):
        logger.warning("WebSocket handshake rejected: concurrent session cap (%d) exceeded for user='%s'", settings.MAX_CONCURRENT_SESSIONS_PER_USER, user_id)
        await websocket.close(
            code=1008,
            reason=f"Maximum concurrent sessions ({settings.MAX_CONCURRENT_SESSIONS_PER_USER}) exceeded for user '{user_id}'."
        )
        return

    # 5. Handshake Acceptance & Session Creation
    await websocket.accept()
    req_session_id = websocket.query_params.get("session_id")
    try:
        session = session_orchestrator.get_or_create_session(
            session_id=req_session_id,
            user_id=user_id
        )
    except PermissionError as pe:
        logger.warning("WebSocket handshake rejected: cross-user IDOR access attempt for session='%s' by user='%s'", req_session_id, user_id)
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(pe)
        }))
        await websocket.close(code=1008, reason="Unauthorized session access")
        return

    user_tracker.register_connection(user_id, session.session_id)
    logger.info("WebSocket session connected: session_id=%s user_id=%s role=%s mode=%s", session.session_id, user_id, user_role, session.mode)

    # 6. Bounded Audio Output Queue & Backpressure (Items + Bytes Bound)
    audio_out_queue: asyncio.Queue = asyncio.Queue(maxsize=120)
    audio_out_bytes: int = 0
    MAX_AUDIO_QUEUE_BYTES = 512 * 1024  # 512 KB memory budget
    drain_cancelled = False

    async def audio_drain_loop():
        nonlocal drain_cancelled, audio_out_bytes
        while not drain_cancelled:
            try:
                chunk = await audio_out_queue.get()
                audio_out_bytes = max(0, audio_out_bytes - len(chunk))
                await websocket.send_bytes(chunk)
                audio_out_queue.task_done()
            except (asyncio.CancelledError, WebSocketDisconnect):
                break
            except Exception:
                break

    drain_task = asyncio.create_task(audio_drain_loop())
    last_active_time = time.time()

    async def handle_audio_delta(pcm_bytes: bytes):
        nonlocal audio_out_bytes, last_active_time
        last_active_time = time.time()
        try:
            if not session.telemetry["timestamps"].get("first_audio_chunk"):
                session.record_timestamp("first_audio_chunk")
                session.calculate_turn_latency()

            # Enforce dual bound: item count (120) AND byte budget (512 KB)
            while audio_out_queue.full() or (audio_out_bytes + len(pcm_bytes) > MAX_AUDIO_QUEUE_BYTES):
                try:
                    dropped = audio_out_queue.get_nowait()
                    audio_out_bytes = max(0, audio_out_bytes - len(dropped))
                    audio_out_queue.task_done()
                    logger.debug("Session %s backpressure: dropped oldest audio chunk (%d bytes)", session.session_id, len(dropped))
                except Exception:
                    break

            audio_out_bytes += len(pcm_bytes)
            await audio_out_queue.put(pcm_bytes)
        except Exception:
            pass


    async def handle_transcript_delta(role: str, delta: str):
        nonlocal last_active_time
        last_active_time = time.time()
        try:
            await websocket.send_text(json.dumps({
                "type": "transcript_delta",
                "role": role,
                "delta": delta,
                "provider": session.primary_provider_id
            }))
        except Exception:
            pass

    async def handle_turn_complete(details: dict):
        try:
            session.record_timestamp("response_completed")
            latency_ms = session.calculate_turn_latency()
            await websocket.send_text(json.dumps({
                "type": "turn_complete",
                "provider": session.primary_provider_id,
                "provider_status": details.get("status", provider.status),
                "telemetry": {
                    "last_turn_latency_ms": latency_ms,
                    "median_latency_ms": session.telemetry.get("median_latency_ms", latency_ms),
                    "p95_latency_ms": session.telemetry.get("p95_latency_ms", latency_ms),
                    "turn_count": session.telemetry.get("turn_count", 1),
                    "barge_in_count": session.telemetry["barge_in_count"],
                    "last_barge_in_ms": session.telemetry["last_barge_in_ms"]
                },
                "details": details
            }))
            session.telemetry["timestamps"].clear()
        except Exception:
            pass

    async def handle_interrupted():
        nonlocal audio_out_bytes
        try:
            # Clear outgoing audio queue immediately on barge-in
            while not audio_out_queue.empty():
                try:
                    dropped = audio_out_queue.get_nowait()
                    audio_out_bytes = max(0, audio_out_bytes - len(dropped))
                    audio_out_queue.task_done()
                except Exception:
                    break
            audio_out_bytes = 0

            await websocket.send_text(json.dumps({
                "type": "interrupted",
                "provider": session.primary_provider_id,
                "barge_in_latency_ms": session.telemetry.get("last_barge_in_ms", 15.0)
            }))
        except Exception:
            pass

    async def handle_error(err_msg: str):
        logger.warning("Provider error in session %s [provider=%s status=%s]: %s", session.session_id, session.primary_provider_id, provider.status, err_msg)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": err_msg,
                "provider": session.primary_provider_id,
                "provider_status": provider.status
            }))
        except Exception:
            pass

    async def handle_status_change(status: str, detail: str):
        try:
            await websocket.send_text(json.dumps({
                "type": "provider_status_changed",
                "provider": session.primary_provider_id,
                "status": status,
                "detail": detail
            }))
        except Exception:
            pass

    def register_provider_callbacks(prov):
        prov.set_callbacks(
            on_audio_delta=lambda chunk: asyncio.create_task(handle_audio_delta(chunk)),
            on_transcript_delta=lambda role, delta: asyncio.create_task(handle_transcript_delta(role, delta)),
            on_turn_complete=lambda details: asyncio.create_task(handle_turn_complete(details)),
            on_interrupted=lambda: asyncio.create_task(handle_interrupted()),
            on_error=lambda msg: asyncio.create_task(handle_error(msg)),
            on_status_change=lambda status, detail: asyncio.create_task(handle_status_change(status, detail))
        )

    provider = session.get_provider(session.primary_provider_id)
    register_provider_callbacks(provider)

    sys_instruction = (
        "Anda adalah asisten suara analitikal diplomasi & kebijakan MENKOPOLKAM AI HUB. "
        "Berikan respon langsung, tajam, faktual, tanpa basa-basi sama sekali. "
        "Jawab dalam bahasa yang sama dengan pengguna (Indonesia atau English)."
    )
    await provider.connect(system_instruction=sys_instruction)

    await websocket.send_text(json.dumps({
        "type": "session_created",
        "session_id": session.session_id,
        "user_id": user_id,
        "user_role": user_role,
        "provider": session.primary_provider_id,
        "provider_status": provider.status,
        "provider_status_detail": provider.status_detail,
        "mode": session.mode
    }))

    # 7. Idle Session Watchdog Loop
    last_active_time = time.time()
    watchdog_cancelled = False

    async def idle_watchdog_loop():
        nonlocal watchdog_cancelled
        while not watchdog_cancelled:
            await asyncio.sleep(5.0)
            if time.time() - last_active_time > settings.SESSION_IDLE_TIMEOUT_SECONDS:
                logger.info("Session %s idle timeout after %ds inactivity", session.session_id, settings.SESSION_IDLE_TIMEOUT_SECONDS)
                try:
                    await websocket.send_text(json.dumps({
                        "type": "session_timeout",
                        "message": f"Sesi ditutup otomatis karena tidak ada aktivitas selama {settings.SESSION_IDLE_TIMEOUT_SECONDS} detik."
                    }))
                    await websocket.close(code=1000, reason="Session idle timeout")
                except Exception:
                    pass
                break

    watchdog_task = asyncio.create_task(idle_watchdog_loop())

    try:
        while True:
            message = await websocket.receive()
            last_active_time = time.time()

            if "bytes" in message and message["bytes"]:
                raw_bytes = message["bytes"]
                if len(raw_bytes) <= settings.MAX_AUDIO_CHUNK_BYTES:
                    await provider.send_audio_chunk(raw_bytes)
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Audio chunk size {len(raw_bytes)} bytes exceeds maximum allowed limit {settings.MAX_AUDIO_CHUNK_BYTES} bytes."
                    }))
            elif "text" in message and message["text"]:
                if len(message["text"]) > 65536:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Text frame size exceeds maximum limit of 64 KB."
                    }))
                    continue
                try:
                    event = json.loads(message["text"])
                    event_type = event.get("type", "")

                    if event_type == "user_speech_start":
                        session.record_timestamp("speech_start")
                    elif event_type == "user_speech_end":
                        session.record_timestamp("speech_end")
                        user_text = event.get("text", "")
                        if user_text:
                            session.transcript_history.append({"role": "user", "text": user_text})
                        await provider.send_text(user_text)
                    elif event_type == "interrupt":
                        t0 = time.time()
                        await provider.cancel_response()
                        # Purge queued outgoing audio chunks
                        while not audio_out_queue.empty():
                            try:
                                dropped = audio_out_queue.get_nowait()
                                audio_out_bytes = max(0, audio_out_bytes - len(dropped))
                                audio_out_queue.task_done()
                            except Exception:
                                break
                        audio_out_bytes = 0
                        barge_in_ms = round((time.time() - t0) * 1000.0, 1)
                        session.telemetry["barge_in_count"] += 1
                        session.telemetry["last_barge_in_ms"] = barge_in_ms
                        await websocket.send_text(json.dumps({
                            "type": "interrupted",
                            "barge_in_latency_ms": barge_in_ms
                        }))
                    elif event_type == "switch_provider":
                        # Rate limit provider switching
                        if not rate_limiter.check_and_record(f"switch:{session.session_id}", settings.RATE_LIMIT_SWITCH_PROVIDER, 30.0):
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": f"Provider switching rate limit exceeded (Max {settings.RATE_LIMIT_SWITCH_PROVIDER} switches per 30s)."
                            }))
                            continue

                        new_prov = event.get("provider", "gemini_live")
                        # Purge queued audio before switching to prevent stale audio leak
                        while not audio_out_queue.empty():
                            try:
                                dropped = audio_out_queue.get_nowait()
                                audio_out_bytes = max(0, audio_out_bytes - len(dropped))
                                audio_out_queue.task_done()
                            except Exception:
                                break
                        audio_out_bytes = 0

                        switch_res = await session_orchestrator.switch_provider(
                            session.session_id,
                            new_prov,
                            user_id=user_id
                        )
                        provider = session.get_provider(new_prov)
                        register_provider_callbacks(provider)
                        await websocket.send_text(json.dumps({
                            "type": "provider_switched",
                            "provider": new_prov,
                            "provider_status": provider.status,
                            "provider_status_detail": provider.status_detail,
                            "details": switch_res
                        }))
                    elif event_type == "request_dual_analysis":
                        query = event.get("query", "")
                        analysis_res = await session_orchestrator.process_dual_intelligence(
                            session.session_id,
                            query,
                            user_id=user_id
                        )
                        await websocket.send_text(json.dumps({
                            "type": "dual_analysis_result",
                            "data": analysis_res
                        }))
                    elif event_type == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                except json.JSONDecodeError:
                    pass
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception:
        pass
    finally:
        drain_cancelled = True
        watchdog_cancelled = True
        drain_task.cancel()
        watchdog_task.cancel()
        while not audio_out_queue.empty():
            try:
                audio_out_queue.get_nowait()
                audio_out_queue.task_done()
            except Exception:
                break
        audio_out_bytes = 0
        user_tracker.unregister_connection(user_id, session.session_id)
        await session.disconnect_all()
        session_orchestrator.remove_session(session.session_id, user_id=user_id)
        logger.info("Session %s disconnected and cleaned up (user=%s)", session.session_id, user_id)


# ============================================================================
# AUTHENTICATION & CAPTCHA SECURITY ENDPOINTS
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: str
    captcha_answer: str

@app.get("/api/auth/captcha")
async def get_captcha():
    """Generates a dynamic Captcha challenge with SVG and expiration."""
    challenge = captcha_service.generate_captcha()
    return JSONResponse(content=challenge)

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """
    Validates Captcha security challenge and user credentials.
    Returns authenticated user payload and JWT access token.
    """
    # 1. Verify Captcha
    if not captcha_service.verify_captcha(req.captcha_id, req.captcha_answer):
        raise HTTPException(
            status_code=400,
            detail="Kode keamanan captcha tidak valid atau sudah kedaluwarsa. Silakan coba lagi."
        )

    # 2. Authenticate User
    user = user_service.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Username atau password salah."
        )

    # 3. Create Access Token
    token = create_access_token(
        sub=user["username"],
        role=user["role"]
    )

    return JSONResponse(content={
        "status": "success",
        "token": token,
        "user": user
    })

@app.get("/api/auth/me")
async def get_current_user(username: Optional[str] = None):
    """Returns profile for active user."""
    if not username:
        return JSONResponse(status_code=400, content={"detail": "Username parameter required"})
    user = user_service.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return JSONResponse(content=user)

@app.delete("/api/users/{username}")
async def delete_user_account(username: str):
    """
    Attempts to delete user account.
    Superadmin and protected system accounts cannot be deleted.
    """
    success, msg = user_service.delete_user(username)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return JSONResponse(content={"status": "success", "message": msg})

# --- Production Deployment: Static Frontend Serving & SPA Catch-All ---
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST_DIR.exists():
    if (DIST_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_frontend(full_path: str):
        # Do not intercept API or WebSocket routes
        if full_path.startswith("api/") or full_path.startswith("ws/") or full_path == "api" or full_path == "ws":
            raise HTTPException(status_code=404, detail="API endpoint not found")
        target_file = DIST_DIR / full_path
        if target_file.is_file():
            return FileResponse(target_file)
        index_file = DIST_DIR / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend index.html not found")





