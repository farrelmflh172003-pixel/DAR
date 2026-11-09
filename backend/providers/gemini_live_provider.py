import os
import io
import json
import wave
import base64
import asyncio
import httpx
import websockets
from typing import Optional, Dict, Any, List
from config import settings
from providers.base_provider import BaseRealtimeProvider

from utils.audio_parser import (
    extract_pcm16_samples,
    parse_audio_payload,
    AudioParserError,
    AudioFormatError
)

class GeminiLiveProvider(BaseRealtimeProvider):
    """
    Adapter for Google Gemini Live Multimodal Real-Time API.
    Attempts official BidiGenerateContent WebSocket session first (gemini-2.0-flash-exp / gemini-2.0-flash),
    with explicit status separation between 'native_connected', 'bridge_active', 'disconnected', and 'error'.
    Maintains Flash Streaming Bridge as a high-fidelity fallback when Bidi requires enterprise whitelisting.
    """

    def __init__(self, api_key: str = "", model_name: str = "", tts_model: str = ""):
        chosen_model = model_name or settings.GEMINI_LIVE_MODEL
        super().__init__(provider_id="gemini_live", model_name=chosen_model)
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.tts_model = tts_model or settings.GEMINI_TTS_MODEL
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._active_turn_task: Optional[asyncio.Task] = None
        self._is_cancelled = False
        self._buffered_pcm_bytes = bytearray()
        self.system_instruction = ""
        self.voice = "Aoede"

    async def connect(self, system_instruction: str = "", voice: str = "Aoede") -> bool:
        self.system_instruction = system_instruction
        self.voice = voice or "Aoede"
        self._is_cancelled = False
        self._buffered_pcm_bytes.clear()
        self.set_status("connecting", "Initializing Gemini Live connection...")

        if not self.api_key:
            msg = "GEMINI_API_KEY is not configured in backend/.env."
            self.set_status("error", msg)
            if self._on_error:
                self._on_error(msg)
            return False

        # 1. Attempt Native Bidi WebSocket connection (fast direct probe)
        native_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={self.api_key}"
        connected_native = False
        last_native_error = ""

        try:
            ws = await asyncio.wait_for(websockets.connect(native_url, ping_interval=20), timeout=2.5)
            setup_msg = {
                "setup": {
                    "model": self.model_name,
                    "generationConfig": {
                        "responseModalities": ["AUDIO", "TEXT"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": self.voice}
                            }
                        }
                    },
                    "systemInstruction": {
                        "parts": [{"text": self.system_instruction}]
                    }
                }
            }
            await ws.send(json.dumps(setup_msg))
            first_msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            ack = json.loads(first_msg)
            if "setupComplete" in ack or "serverContent" in ack:
                self.ws = ws
                self.set_status("native_connected", f"Gemini Live Native Bidi WebSocket connected ({self.model_name})")
                self._receive_task = asyncio.create_task(self._listen_native())
                connected_native = True
            else:
                await ws.close()
        except Exception as e:
            last_native_error = str(e)

        if not connected_native:
            # Explicitly activate Flash Streaming Bridge fallback with honest disclosure
            clean_err = last_native_error.replace('\n', ' ')[:75]
            detail_msg = (
                f"Gemini Flash Streaming Bridge active (Native Bidi WebSocket policy rejected / requires enterprise whitelisting: {clean_err}). "
                f"Audio streaming generated via Flash Lite and 24kHz Neural TTS."
            )
            self.set_status("bridge_active", detail_msg)

        return True

    async def disconnect(self) -> None:
        self.set_status("disconnected", "Session closed cleanly.")
        self._is_cancelled = True
        self._buffered_pcm_bytes.clear()

        if self._active_turn_task and not self._active_turn_task.done():
            self._active_turn_task.cancel()
            self._active_turn_task = None

        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            self._receive_task = None

        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Stream PCM audio chunk into session."""
        if not self.is_connected or not pcm_bytes:
            return

        if self.status == "native_connected" and self.ws:
            msg = {
                "realtimeInput": {
                    "mediaChunks": [
                        {
                            "mimeType": "audio/pcm;rate=16000",
                            "data": base64.b64encode(pcm_bytes).decode("ascii")
                        }
                    ]
                }
            }
            try:
                await self.ws.send(json.dumps(msg))
            except Exception as e:
                if self._on_error:
                    self._on_error(f"Gemini Live native stream error: {e}")
        elif self.status == "bridge_active":
            # Buffer incoming 16kHz microphone chunks for audio understanding
            self._buffered_pcm_bytes.extend(pcm_bytes)

    async def send_text(self, text: str) -> None:
        """Send user text or transcribed speech into the live turn."""
        if not self.is_connected:
            return

        self._is_cancelled = False
        user_query = text.strip()

        if self.status == "native_connected" and self.ws:
            if not user_query:
                return
            msg = {
                "clientContent": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [{"text": user_query}]
                        }
                    ],
                    "turnComplete": True
                }
            }
            await self.ws.send(json.dumps(msg))
        elif self.status == "bridge_active":
            if self._active_turn_task and not self._active_turn_task.done():
                self._active_turn_task.cancel()
            
            # If text is provided, use it directly. If empty but audio was buffered, transcribe audio first!
            if not user_query and len(self._buffered_pcm_bytes) > 0:
                audio_data = bytes(self._buffered_pcm_bytes)
                self._buffered_pcm_bytes.clear()
                self._active_turn_task = asyncio.create_task(self._execute_bridge_turn_from_audio(audio_data))
            elif user_query:
                self._buffered_pcm_bytes.clear()
                self._active_turn_task = asyncio.create_task(self._execute_bridge_turn(user_query))

    async def cancel_response(self) -> None:
        """Trigger immediate barge-in cancellation."""
        self._is_cancelled = True
        self._buffered_pcm_bytes.clear()

        if self._active_turn_task and not self._active_turn_task.done():
            self._active_turn_task.cancel()
            self._active_turn_task = None

        if self.status == "native_connected" and self.ws:
            try:
                await self.ws.send(json.dumps({"interrupted": True}))
            except Exception:
                pass

        if self._on_interrupted:
            self._on_interrupted()

    async def _listen_native(self) -> None:
        """Receive streaming events from native Bidi WebSocket."""
        try:
            while self.is_connected and self.ws:
                raw = await self.ws.recv()
                data = json.loads(raw)

                if self._is_cancelled:
                    continue

                server_content = data.get("serverContent", {})
                if server_content.get("interrupted"):
                    if self._on_interrupted:
                        self._on_interrupted()

                model_turn = server_content.get("modelTurn", {})
                parts = model_turn.get("parts", [])
                for part in parts:
                    if "text" in part:
                        if self._on_transcript_delta:
                            self._on_transcript_delta("assistant", part["text"])
                    if "inlineData" in part:
                        audio_b64 = part["inlineData"].get("data", "")
                        if audio_b64 and self._on_audio_delta and not self._is_cancelled:
                            raw_pcm = base64.b64decode(audio_b64)
                            self._on_audio_delta(raw_pcm)

                if server_content.get("turnComplete"):
                    if self._on_turn_complete:
                        self._on_turn_complete({
                            "provider": "gemini_live",
                            "status": "native_connected",
                            "model": self.model_name
                        })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._on_error and not self._is_cancelled:
                self._on_error(f"Gemini Live native receive error: {e}")

    async def _execute_bridge_turn_from_audio(self, pcm_bytes: bytes) -> None:
        """Transcribe and process speech when raw microphone audio was streamed in bridge mode."""
        try:
            # Build valid 16kHz WAV container in-memory
            buf = io.BytesIO()
            with wave.open(buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(pcm_bytes)
            wav_bytes = buf.getvalue()
            b64_wav = base64.b64encode(wav_bytes).decode("ascii")

            url_audio = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"inlineData": {"mimeType": "audio/wav", "data": b64_wav}},
                            {"text": f"{self.system_instruction}\nDengarkan audio ini, transkripsikan pertanyaan secara singkat, lalu berikan jawaban diplomatis to the point."}
                        ]
                    }
                ]
            }

            headers = {"x-goog-api-key": self.api_key} if self.api_key else {}
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url_audio, headers=headers, json=payload)
                if self._is_cancelled:
                    return

                if res.status_code == 200:
                    text_resp = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    await self._stream_tts_audio(text_resp)
                else:
                    if self._on_error:
                        self._on_error(f"Gemini bridge audio processing returned status {res.status_code}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._on_error and not self._is_cancelled:
                self._on_error(f"Gemini audio bridge error: {e}")

    async def _execute_bridge_turn(self, user_text: str) -> None:
        """High-speed real-time streaming bridge: Text Generation + 24kHz Neural TTS streaming."""
        try:
            # 1. Generate textual response from Gemini Flash Lite
            url_text = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-lite-latest:generateContent"
            prompt = (
                f"{self.system_instruction}\n\n"
                f"Pertanyaan/Pernyataan: {user_text}\n"
                f"Jawaban langsung diplomatis to the point tanpa basa-basi:"
            )
            payload_text = {
                "contents": [{"parts": [{"text": prompt}]}]
            }

            self.set_status("bridge_active", "Mensintesis teks respons via Gemini Flash Lite...")
            headers = {"x-goog-api-key": self.api_key} if self.api_key else {}
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url_text, headers=headers, json=payload_text)
                if self._is_cancelled:
                    return

                if res.status_code == 200:
                    text_resp = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    self.set_status("bridge_active", f"Teks respons selesai ({len(text_resp)} karakter). Menghasilkan audio 24kHz via {self.tts_model}...")
                    await self._stream_tts_audio(text_resp)
                else:
                    if self._on_error:
                        self._on_error(f"Gemini API returned status {res.status_code}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._on_error and not self._is_cancelled:
                self._on_error(f"Gemini bridge error: {e}")

    async def _stream_tts_audio(self, text_resp: str) -> None:
        """Generate and stream 24kHz PCM16 audio with sanitized error handling."""
        if self._is_cancelled or not text_resp:
            return

        if self._on_transcript_delta:
            self._on_transcript_delta("assistant", text_resp)

        payload_tts = {
            "contents": [{"parts": [{"text": text_resp}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": self.voice}
                    }
                }
            }
        }

        tts_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.tts_model}:generateContent"
        raw_pcm = b""
        tts_error: Optional[str] = None
        headers = {"x-goog-api-key": self.api_key} if self.api_key else {}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res_tts = await client.post(tts_url, headers=headers, json=payload_tts)
                
                if res_tts.status_code == 200:
                    try:
                        res_json = res_tts.json()
                        candidates = res_json.get("candidates", [])
                        if not candidates:
                            tts_error = f"Gemini TTS returned no candidates (blocked or empty on {self.tts_model})."
                        else:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            inline_part = next((p for p in parts if "inlineData" in p), None)
                            if not inline_part:
                                tts_error = f"Gemini TTS response missing inlineData audio payload on {self.tts_model}."
                            else:
                                b64_audio = inline_part["inlineData"].get("data", "")
                                mime_type = inline_part["inlineData"].get("mimeType", "")
                                if not b64_audio:
                                    tts_error = f"Gemini TTS returned empty audio payload on {self.tts_model}."
                                else:
                                    try:
                                        raw_data = base64.b64decode(b64_audio)
                                        raw_pcm, _meta = parse_audio_payload(
                                            raw_data,
                                            mime_type=mime_type,
                                            expected_sample_rate=24000,
                                            expected_channels=1,
                                            allow_raw_pcm=True
                                        )
                                        if len(raw_pcm) == 0:
                                            tts_error = f"Gemini TTS audio extraction yielded 0 PCM samples on {self.tts_model}."
                                    except (AudioParserError, AudioFormatError) as audio_err:
                                        tts_error = f"Gemini TTS invalid audio format on {self.tts_model}: {audio_err}"
                    except Exception as parse_err:
                        tts_error = f"Gemini TTS response parsing failed: {parse_err}"

                elif res_tts.status_code == 429:
                    # Sanitize quota exhaustion message and halt immediately without retrying in a loop
                    try:
                        err_json = res_tts.json().get("error", {})
                        details = err_json.get("details", [])
                        retry_delay = None
                        for d in details:
                            if "RetryInfo" in d.get("@type", ""):
                                retry_delay = d.get("retryDelay")
                        delay_msg = f" (retry delay: {retry_delay})" if retry_delay else ""
                        tts_error = (
                            f"Gemini TTS quota exceeded (HTTP 429 on {self.tts_model}){delay_msg}. "
                            f"Free Tier limit reached. Please retry after quota reset."
                        )
                    except Exception:
                        tts_error = (
                            f"Gemini TTS quota exceeded (HTTP 429 on {self.tts_model}). "
                            f"Free Tier limit reached. Please retry after quota reset."
                        )
                elif res_tts.status_code in (401, 403):
                    tts_error = (
                        f"Gemini TTS access denied (HTTP {res_tts.status_code} on {self.tts_model}). "
                        f"Verify GEMINI_API_KEY and API project permissions."
                    )
                elif res_tts.status_code == 404:
                    tts_error = (
                        f"Gemini TTS model not found (HTTP 404 on {self.tts_model}). "
                        f"Verify that model is supported by Google AI Generative Language API."
                    )
                elif res_tts.status_code == 400:
                    tts_error = (
                        f"Gemini TTS request rejected (HTTP 400 on {self.tts_model}). "
                        f"Malformed request or unsupported audio modality parameters."
                    )
                else:
                    tts_error = f"Gemini TTS provider error: HTTP {res_tts.status_code} on {self.tts_model}."

        except httpx.TimeoutException:
            tts_error = f"Gemini TTS request timed out connecting to {self.tts_model}."
        except httpx.RequestError as req_err:
            tts_error = f"Gemini TTS network transport error: {type(req_err).__name__}."
        except Exception as e:
            tts_error = f"Gemini TTS unexpected error: {str(e)[:80]}."

        if self._is_cancelled:
            return

        # If audio generation failed or yielded no audio, report honest failure
        if not raw_pcm or tts_error:
            final_err = tts_error or f"Gemini TTS generated 0 audio bytes on {self.tts_model}."
            if self._on_error:
                self._on_error(final_err)
            self.set_status("error", f"Streaming bridge audio generation failed: {final_err}")
            return

        # Deliver audio chunks
        if self._on_audio_delta:
            chunk_size = 3840  # 1920 samples @ 24kHz = 80ms
            for i in range(0, len(raw_pcm), chunk_size):
                if self._is_cancelled:
                    return
                chunk = raw_pcm[i:i + chunk_size]
                self._on_audio_delta(chunk)
                await asyncio.sleep(0.01)

        if self._on_turn_complete and not self._is_cancelled:
            self._on_turn_complete({
                "provider": "gemini_live",
                "status": "bridge_active",
                "model": f"gemini-flash-lite + {self.tts_model}",
                "text": text_resp
            })
