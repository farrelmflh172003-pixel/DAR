import pytest
import asyncio
import io
import wave
import base64
import httpx
from unittest.mock import patch, MagicMock
from config import settings
from providers.gemini_live_provider import GeminiLiveProvider

def _generate_synthetic_pcm16_wav(num_samples: int = 4800, sample_rate: int = 24000) -> bytes:
    """Generate in-memory mono PCM16 WAV audio fixture (200ms of audio)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # Synthetic 400Hz sine-ish wave
        raw_samples = bytearray()
        for i in range(num_samples):
            val = int(10000 * (1 if (i % 60) < 30 else -1))
            raw_samples.extend(val.to_bytes(2, byteorder="little", signed=True))
        wf.writeframes(bytes(raw_samples))
    return buf.getvalue()

@pytest.mark.asyncio
async def test_gemini_tts_successful_audio_response_and_frame_pacing():
    """Verify successful audio response parsing, extraction, and 80ms paced chunk delivery."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    wav_bytes = _generate_synthetic_pcm16_wav(num_samples=4800, sample_rate=24000)
    b64_audio = base64.b64encode(wav_bytes).decode("ascii")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "audio/wav",
                                "data": b64_audio
                            }
                        }
                    ]
                }
            }
        ]
    }

    transcript_received = ""
    received_chunks = []
    turn_completed_data = None

    def on_transcript(role, text):
        nonlocal transcript_received
        transcript_received = text

    def on_audio(chunk):
        received_chunks.append(chunk)

    def on_turn_complete(turn):
        nonlocal turn_completed_data
        turn_completed_data = turn

    provider.set_callbacks(
        on_transcript_delta=on_transcript,
        on_audio_delta=on_audio,
        on_turn_complete=on_turn_complete
    )

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp) as mock_post:
        await provider._stream_tts_audio("Halo, Menkopolkam AI Hub siap membantu.")

    assert mock_post.call_count == 1
    call_url = mock_post.call_args[0][0]
    call_headers = mock_post.call_args[1].get("headers", {})
    assert "gemini-3.8-flash-lite-tts:generateContent" in call_url
    assert "key=" not in call_url
    assert call_headers.get("x-goog-api-key") == "test_key"

    assert transcript_received == "Halo, Menkopolkam AI Hub siap membantu."
    assert len(received_chunks) > 0
    total_bytes = sum(len(c) for c in received_chunks)
    assert total_bytes == 4800 * 2  # 9600 bytes of PCM16
    assert all(len(c) <= 3840 for c in received_chunks)

    assert turn_completed_data is not None
    assert turn_completed_data["status"] == "bridge_active"
    assert "gemini-3.8-flash-lite-tts" in turn_completed_data["model"]

@pytest.mark.asyncio
async def test_gemini_tts_quota_exhaustion_sanitized_and_no_retry_loop():
    """Verify HTTP 429 fails fast with sanitized error and zero repeated retries."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = {
        "error": {
            "code": 429,
            "message": "Quota exceeded on Free Tier. Please retry later.",
            "status": "RESOURCE_EXHAUSTED"
        }
    }

    error_received = ""
    turn_completed = False
    audio_received = 0

    provider.set_callbacks(
        on_error=lambda err: setattr(provider, "_last_err", err),
        on_audio_delta=lambda c: setattr(provider, "_had_audio", True),
        on_turn_complete=lambda t: setattr(provider, "_turn_done", True)
    )

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp) as mock_post:
        await provider._stream_tts_audio("Pertanyaan diplomatis.")

    # Must NOT retry other models in a loop
    assert mock_post.call_count == 1
    assert provider.status == "error"
    assert "429" in provider.status_detail
    assert "quota" in provider.status_detail.lower()
    assert getattr(provider, "_turn_done", False) is False
    assert getattr(provider, "_had_audio", False) is False

@pytest.mark.asyncio
async def test_gemini_tts_permission_denied_sanitized():
    """Verify HTTP 403 permission denial is sanitized and halts immediately."""
    provider = GeminiLiveProvider(api_key="invalid_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "The caller does not have permission"

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp) as mock_post:
        await provider._stream_tts_audio("Pertanyaan.")

    assert mock_post.call_count == 1
    assert provider.status == "error"
    assert "403" in provider.status_detail
    assert "permission" in provider.status_detail.lower()

@pytest.mark.asyncio
async def test_gemini_tts_unsupported_model_404_sanitized():
    """Verify HTTP 404 model not found is handled cleanly."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="non-existent-tts-model")
    provider.status = "bridge_active"

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Model not found"

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        await provider._stream_tts_audio("Pertanyaan.")

    assert provider.status == "error"
    assert "404" in provider.status_detail
    assert "not found" in provider.status_detail.lower()

@pytest.mark.asyncio
async def test_gemini_tts_empty_payload_and_missing_inline_data():
    """Verify empty candidates or missing inlineData does not report fake success."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"candidates": []}

    turn_completed = False
    provider.set_callbacks(on_turn_complete=lambda t: setattr(provider, "_turn_done", True))

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        await provider._stream_tts_audio("Pertanyaan.")

    assert provider.status == "error"
    assert "no candidates" in provider.status_detail.lower() or "empty" in provider.status_detail.lower()
    assert getattr(provider, "_turn_done", False) is False

@pytest.mark.asyncio
async def test_gemini_tts_zero_pcm_samples_rejection():
    """Verify corrupt/empty base64 audio yielding 0 samples is rejected cleanly."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "audio/wav",
                                "data": ""  # Empty audio data
                            }
                        }
                    ]
                }
            }
        ]
    }

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        await provider._stream_tts_audio("Pertanyaan.")

    assert provider.status == "error"
    assert "empty" in provider.status_detail.lower()

@pytest.mark.asyncio
async def test_gemini_tts_barge_in_cancellation_and_cleanup():
    """Verify cancellation immediately halts streaming and invokes on_interrupted."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    wav_bytes = _generate_synthetic_pcm16_wav(num_samples=24000, sample_rate=24000)  # 1 full second
    b64_audio = base64.b64encode(wav_bytes).decode("ascii")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"inlineData": {"mimeType": "audio/wav", "data": b64_audio}}]}}
        ]
    }

    interrupted_called = False
    delivered_chunks = []

    def on_interrupted():
        nonlocal interrupted_called
        interrupted_called = True

    def on_audio(chunk):
        delivered_chunks.append(chunk)

    provider.set_callbacks(on_interrupted=on_interrupted, on_audio_delta=on_audio)

    async def cancel_midway():
        await asyncio.sleep(0.03)  # Wait for first 2-3 chunks
        await provider.cancel_response()

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        await asyncio.gather(
            provider._stream_tts_audio("Kalimat panjang untuk pengujian pembatalan."),
            cancel_midway()
        )

    assert interrupted_called is True
    # Delivery was interrupted before completing all 24000 samples (48000 bytes // 3840 = 13 chunks)
    assert len(delivered_chunks) < 13
    assert provider._is_cancelled is True

@pytest.mark.asyncio
async def test_gemini_tts_configurable_model_override():
    """Verify that tts_model argument overrides the default configuration."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="custom-preview-tts")
    assert provider.tts_model == "custom-preview-tts"

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Model not found"

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp) as mock_post:
        await provider._stream_tts_audio("Cek model URL.")

    call_url = mock_post.call_args[0][0]
    assert "models/custom-preview-tts:generateContent" in call_url

@pytest.mark.asyncio
async def test_gemini_tts_raw_pcm16_payload_without_wav_header():
    """Verify provider processes raw PCM16 (audio/pcm;rate=24000) without failing or assuming WAV header."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    # 4800 samples = 9600 bytes of raw PCM16 (no RIFF header)
    raw_pcm_bytes = bytearray()
    for i in range(4800):
        val = int(8000 * (1 if (i % 40) < 20 else -1))
        raw_pcm_bytes.extend(val.to_bytes(2, byteorder="little", signed=True))
    raw_pcm_data = bytes(raw_pcm_bytes)
    b64_pcm = base64.b64encode(raw_pcm_data).decode("ascii")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "audio/pcm;rate=24000",
                                "data": b64_pcm
                            }
                        }
                    ]
                }
            }
        ]
    }

    received_chunks = []
    turn_completed = False

    provider.set_callbacks(
        on_audio_delta=lambda chunk: received_chunks.append(chunk),
        on_turn_complete=lambda turn: setattr(provider, "_turn_done", True)
    )

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        await provider._stream_tts_audio("Raw PCM audio test.")

    assert len(received_chunks) > 0
    total_received = sum(len(c) for c in received_chunks)
    assert total_received == len(raw_pcm_data)
    assert getattr(provider, "_turn_done", False) is True

@pytest.mark.asyncio
async def test_gemini_tts_compressed_audio_rejection():
    """Verify that compressed MIME types (e.g. audio/mp3) or MP3/OGG headers are rejected cleanly."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    b64_fake_mp3 = base64.b64encode(b"ID3\x03\x00\x00\x00\x00\x00#TCON\x00\x00\x00").decode("ascii")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "audio/mp3",
                                "data": b64_fake_mp3
                            }
                        }
                    ]
                }
            }
        ]
    }

    provider.set_callbacks(
        on_turn_complete=lambda t: setattr(provider, "_turn_done", True)
    )

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        await provider._stream_tts_audio("Compressed audio rejection test.")

    assert provider.status == "error"
    assert "compressed" in provider.status_detail.lower() or "invalid" in provider.status_detail.lower()
    assert getattr(provider, "_turn_done", False) is False

@pytest.mark.asyncio
async def test_gemini_tts_sample_rate_mismatch_rejection():
    """Verify that WAV files with unexpected sample rate (e.g. 48kHz instead of 24kHz) are rejected."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    # Create 48kHz WAV
    wav_48k = _generate_synthetic_pcm16_wav(num_samples=2400, sample_rate=48000)
    b64_audio = base64.b64encode(wav_48k).decode("ascii")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"inlineData": {"mimeType": "audio/wav", "data": b64_audio}}
                    ]
                }
            }
        ]
    }

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        await provider._stream_tts_audio("Sample rate mismatch test.")

    assert provider.status == "error"
    assert "sample rate mismatch" in provider.status_detail.lower() or "48000" in provider.status_detail

@pytest.mark.asyncio
async def test_gemini_tts_odd_length_pcm_rejection():
    """Verify that raw PCM with an odd byte count (violating 16-bit boundary) is rejected cleanly."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    odd_pcm = b"\x00\x01\x00\x02\x00"  # 5 bytes (odd)
    b64_audio = base64.b64encode(odd_pcm).decode("ascii")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"inlineData": {"mimeType": "audio/pcm", "data": b64_audio}}
                    ]
                }
            }
        ]
    }

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        await provider._stream_tts_audio("Odd PCM length test.")

    assert provider.status == "error"
    assert "odd" in provider.status_detail.lower() or "boundary" in provider.status_detail.lower()

@pytest.mark.asyncio
async def test_gemini_tts_retry_delay_extraction():
    """Verify that RetryInfo delay is accurately extracted from Google API 429 response without inventing values."""
    provider = GeminiLiveProvider(api_key="test_key", tts_model="gemini-3.8-flash-lite-tts")
    provider.status = "bridge_active"

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = {
        "error": {
            "code": 429,
            "message": "Daily free tier limit exceeded.",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.RetryInfo",
                    "retryDelay": "9360s"
                }
            ]
        }
    }

    with patch.object(httpx.AsyncClient, "post", return_value=mock_resp):
        await provider._stream_tts_audio("Cek retry delay extraction.")

    assert provider.status == "error"
    assert "retry delay: 9360s" in provider.status_detail
    assert "429" in provider.status_detail

