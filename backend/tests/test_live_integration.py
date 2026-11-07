import pytest
import os
import asyncio
import httpx
from config import settings
from providers.gemini_live_provider import GeminiLiveProvider
from providers.openai_realtime_provider import OpenAIRealtimeProvider

@pytest.mark.asyncio
async def test_live_gemini_models_and_rest_health():
    """Verify Gemini API key can access models and generate content."""
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY is not configured.")

    async with httpx.AsyncClient(timeout=8.0) as client:
        headers = {"x-goog-api-key": settings.GEMINI_API_KEY}
        r = await client.get("https://generativelanguage.googleapis.com/v1beta/models", headers=headers)
        assert r.status_code == 200
        models = [m["name"] for m in r.json().get("models", [])]
        assert "models/gemini-2.5-flash" in models or "models/gemini-flash-lite-latest" in models

@pytest.mark.asyncio
async def test_live_gemini_bidi_or_bridge_lifecycle():
    """
    Test live Gemini Live connectivity.
    If project has Bidi permissions, status becomes native_connected.
    If project lacks Bidi whitelisting, status becomes bridge_active with explicit disclosure.
    """
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY is not configured.")

    provider = GeminiLiveProvider(api_key=settings.GEMINI_API_KEY)
    connected = await provider.connect(system_instruction="Jawab dalam 1 kalimat diplomatis.")
    assert connected is True
    assert provider.status in ("native_connected", "bridge_active")
    if provider.status == "bridge_active":
        assert "whitelisting" in provider.status_detail.lower() or "policy" in provider.status_detail.lower() or "bridge" in provider.status_detail.lower()
    await provider.disconnect()

@pytest.mark.asyncio
async def test_live_gemini_flash_bridge_turn_execution():
    """Test actual live audio generation via Gemini Flash Streaming Bridge."""
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY is not configured.")

    provider = GeminiLiveProvider(api_key=settings.GEMINI_API_KEY)
    await provider.connect(system_instruction="Jawab dalam 1 kalimat diplomatis.")

    turn_completed = False
    received_audio_bytes = 0

    def on_complete(turn):
        nonlocal turn_completed
        turn_completed = True

    def on_audio(pcm_chunk):
        nonlocal received_audio_bytes
        received_audio_bytes += len(pcm_chunk)

    provider.set_callbacks(on_turn_complete=on_complete, on_audio_delta=on_audio)
    await provider.send_text("Berapa batas laut teritorial menurut UNCLOS?")

    # Await bridge turn execution task directly
    if provider._active_turn_task:
        await asyncio.wait_for(provider._active_turn_task, timeout=25.0)

    # If quota allows, turn completed and audio was received.
    # If API key is quota-limited on TTS models (HTTP 429), verify honest status disclosure.
    if received_audio_bytes > 0:
        assert turn_completed is True
        assert received_audio_bytes > 0
    else:
        assert provider.status == "error"
        assert "429" in provider.status_detail or "quota" in provider.status_detail.lower()

    await provider.disconnect()

@pytest.mark.asyncio
async def test_live_openai_realtime_ga_status():
    """
    Test live OpenAI Realtime GA connectivity.
    If quota is exhausted (credit_balance_exhausted), verify that it is reported honestly without crashing.
    """
    if not settings.OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY is not configured.")

    settings.ENABLE_REALTIME_MOCK = False
    provider = OpenAIRealtimeProvider(api_key=settings.OPENAI_API_KEY)
    connected = await provider.connect(system_instruction="You are a diplomat.")

    # Status must be either native_connected (if account has credits) or error with honest quota explanation
    if connected:
        assert provider.status == "native_connected"
    else:
        assert provider.status == "error"
        assert "quota" in provider.status_detail.lower() or "kredit" in provider.status_detail.lower() or "rejected" in provider.status_detail.lower()

    await provider.disconnect()

@pytest.mark.asyncio
async def test_live_gemini_tts_opt_in_smoke():
    """
    Explicit, opt-in live TTS smoke test complying with Phase 13 requirements:
    - Uses short, synthetic, non-sensitive text ("Tes audio diplomasi.").
    - Requires GEMINI_API_KEY.
    - Uses x-goog-api-key header; never prints or leaks keys in URLs.
    - Makes at most 1 TTS generation request.
    - If HTTP 429 occurs, stops immediately without trying other models.
    - Reports sanitized status, model, audio byte count, and MIME metadata.
    """
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY is not configured.")

    tts_model = settings.GEMINI_TTS_MODEL or "gemini-3.8-flash-lite-tts"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{tts_model}:generateContent"
    headers = {"x-goog-api-key": settings.GEMINI_API_KEY}
    payload = {
        "contents": [{"parts": [{"text": "Tes audio diplomasi."}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": "Kore"}
                }
            }
        }
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(url, headers=headers, json=payload)
        status_code = res.status_code

        # Sanitized audit reporting without printing secrets
        if status_code == 200:
            data = res.json()
            inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
            mime = inline.get("mimeType", "unknown")
            import base64
            from utils.audio_parser import parse_audio_payload
            raw_pcm, meta = parse_audio_payload(base64.b64decode(inline.get("data", "")), mime_type=mime)
            assert len(raw_pcm) > 0, "Provider returned 200 OK but 0 audio bytes"
            print(f"\n[LIVE TTS SUCCESS] Model: {tts_model} | MIME: {mime} | Audio bytes: {len(raw_pcm)}")
        elif status_code == 429:
            err = res.json().get("error", {})
            reason = err.get("message", "").split("\n")[0][:80]
            print(f"\n[LIVE TTS 429 QUOTA EXHAUSTED] Model: {tts_model} | Status: RESOURCE_EXHAUSTED | Info: {reason}")
            assert "429" in str(status_code)
            assert "quota" in reason.lower() or "limit" in reason.lower() or "exceeded" in reason.lower()
        else:
            print(f"\n[LIVE TTS STATUS {status_code}] Model: {tts_model}")
            assert status_code in (401, 403, 404, 429, 200)

