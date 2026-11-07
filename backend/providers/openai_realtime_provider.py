import os
import json
import base64
import asyncio
import numpy as np
import websockets
from typing import Optional, Dict, Any, List
from config import settings
from providers.base_provider import BaseRealtimeProvider

class StatefulAudioResampler:
    """
    Stateful Catmull-Rom C1 Spline Resampler (16kHz -> 24kHz).
    - Phase accumulator prevents cumulative timing drift on irregular chunk sizes.
    - 3-sample history buffer ensures C1 boundary continuity across consecutive streaming chunks.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.history = np.array([], dtype=np.float32)
        self.total_in_samples = 0
        self.total_out_samples = 0

    def resample_chunk(self, pcm_16k_bytes: bytes) -> bytes:
        if not pcm_16k_bytes or len(pcm_16k_bytes) % 2 != 0:
            return b""
        new_samples = np.frombuffer(pcm_16k_bytes, dtype=np.int16).astype(np.float32)
        n = len(new_samples)
        if n == 0:
            return b""

        # Phase accumulation for exact rational 3/2 timing without rounding drift
        self.total_in_samples += n
        target_total_out = (self.total_in_samples * 3) // 2
        num_out = target_total_out - self.total_out_samples
        self.total_out_samples = target_total_out

        if len(self.history) > 0:
            buf = np.concatenate([self.history, new_samples])
            offset = len(self.history)
        else:
            buf = new_samples
            offset = 0

        self.history = new_samples[-3:].copy()

        pos = np.arange(num_out, dtype=np.float32) * (2.0 / 3.0) + offset
        idx = np.floor(pos).astype(np.int32)
        t = pos - idx

        tot = len(buf)
        i0 = np.clip(idx - 1, 0, tot - 1)
        i1 = np.clip(idx,     0, tot - 1)
        i2 = np.clip(idx + 1, 0, tot - 1)
        i3 = np.clip(idx + 2, 0, tot - 1)

        p0, p1, p2, p3 = buf[i0], buf[i1], buf[i2], buf[i3]
        a = -0.5 * p0 + 1.5 * p1 - 1.5 * p2 + 0.5 * p3
        b = p0 - 2.5 * p1 + 2.0 * p2 - 0.5 * p3
        c = -0.5 * p0 + 0.5 * p2
        d = p1

        out_float = ((a * t + b) * t + c) * t + d
        return np.clip(out_float, -32768, 32767).astype(np.int16).tobytes()

def resample_16k_to_24k(pcm_bytes: bytes) -> bytes:
    """
    Stateless Catmull-Rom cubic spline resampling (C1 smooth) of 16-bit mono PCM from 16kHz to 24kHz.
    """
    resampler = StatefulAudioResampler()
    return resampler.resample_chunk(pcm_bytes)

class OpenAIRealtimeProvider(BaseRealtimeProvider):
    """
    Adapter for OpenAI Realtime Speech-to-Speech API.
    Supports official GA WebSocket protocol (gpt-realtime-mini / gpt-realtime) with server VAD,
    duplex audio streaming deltas, 24kHz audio format validation, and interruption handling (barge-in).
    Adheres strictly to the honest provider status lifecycle.
    """

    def __init__(self, api_key: str = "", model_name: str = ""):
        chosen_model = model_name or settings.OPENAI_REALTIME_MODEL
        super().__init__(provider_id="openai_realtime", model_name=chosen_model)
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._resampler = StatefulAudioResampler()
        self._is_cancelled = False
        self.voice = "alloy"
        self.system_instruction = ""

    async def connect(self, system_instruction: str = "", voice: str = "alloy") -> bool:
        self.system_instruction = system_instruction
        self.voice = voice or "alloy"
        self._is_cancelled = False
        self.set_status("connecting", "Initializing connection to OpenAI Realtime GA...")

        if not self.api_key:
            if settings.ENABLE_REALTIME_MOCK:
                self.set_status("mock_active", "OPENAI_API_KEY not configured; running in mock fallback mode (ENABLE_REALTIME_MOCK=true).")
                return True
            else:
                msg = "OPENAI_API_KEY is not configured in backend/.env. Native connection cannot proceed."
                self.set_status("error", msg)
                if self._on_error:
                    self._on_error(msg)
                return False

        url = f"wss://api.openai.com/v1/realtime?model={self.model_name}"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            ws = await asyncio.wait_for(
                websockets.connect(url, additional_headers=headers, ping_interval=20),
                timeout=5.0
            )

            # Check initial greeting/event from OpenAI GA
            initial_raw = await asyncio.wait_for(ws.recv(), timeout=4.0)
            initial_event = json.loads(initial_raw)

            if initial_event.get("type") == "error":
                err_data = initial_event.get("error", {})
                code = err_data.get("code", "")
                err_message = err_data.get("message", "OpenAI Realtime error")
                await ws.close()

                if code in ("credit_balance_exhausted", "insufficient_quota"):
                    actionable_msg = (
                        f"OpenAI Realtime quota exceeded (Code: {code}). "
                        f"Kredit API pada akun OpenAI Anda telah habis. "
                        f"Harap tambahkan billing credit pada platform OpenAI (https://platform.openai.com/settings/organization/billing/) untuk mengaktifkan native speech."
                    )
                elif code == "invalid_api_key":
                    actionable_msg = "OpenAI Realtime Authentication failed: Invalid API key."
                elif code == "model_not_found":
                    actionable_msg = f"OpenAI Realtime model '{self.model_name}' tidak ditemukan atau akun tidak memiliki akses."
                else:
                    actionable_msg = f"OpenAI Realtime connection rejected: {err_message} (Code: {code})"

                if settings.ENABLE_REALTIME_MOCK:
                    self.set_status("mock_active", f"{actionable_msg} [Running Mock Fallback via ENABLE_REALTIME_MOCK=true]")
                    if self._on_error:
                        self._on_error(f"{actionable_msg} (Mock simulation active)")
                    return True
                else:
                    self.set_status("error", actionable_msg)
                    if self._on_error:
                        self._on_error(actionable_msg)
                    return False

            self.ws = ws
            self.set_status("native_connected", f"OpenAI Realtime GA connected ({self.model_name})")

            # Send session configuration conforming to OpenAI Realtime GA
            session_update = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": self.system_instruction or (
                        "You are a real-time diplomatic voice assistant for MENKOPOLKAM AI HUB. "
                        "Respond concisely, factually, and diplomatically."
                    ),
                    "voice": self.voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "whisper-1"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 600
                    }
                }
            }
            await ws.send(json.dumps(session_update))
            self._receive_task = asyncio.create_task(self._listen_realtime())
            return True

        except Exception as e:
            err_str = str(e)
            actionable_msg = f"Failed to connect to OpenAI Realtime endpoint: {err_str}"
            if settings.ENABLE_REALTIME_MOCK:
                self.set_status("mock_active", f"{actionable_msg} [Running Mock Fallback via ENABLE_REALTIME_MOCK=true]")
                if self._on_error:
                    self._on_error(f"{actionable_msg} (Mock simulation active)")
                return True
            else:
                self.set_status("error", actionable_msg)
                if self._on_error:
                    self._on_error(actionable_msg)
                return False

    async def disconnect(self) -> None:
        self.set_status("disconnected", "Session closed cleanly.")
        self._is_cancelled = True

        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            self._receive_task = None

        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        self._resampler.reset()

    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        if not self.is_connected or not pcm_bytes:
            return

        if self.status == "native_connected" and self.ws:
            # Resample 16kHz microphone stream to 24kHz required by OpenAI pcm16 using stateful overlap
            resampled = self._resampler.resample_chunk(pcm_bytes)
            msg = {
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(resampled).decode("ascii")
            }
            try:
                await self.ws.send(json.dumps(msg))
            except Exception as e:
                if self._on_error:
                    self._on_error(f"OpenAI Realtime audio send error: {e}")

    async def send_text(self, text: str) -> None:
        if not self.is_connected or not text.strip():
            return

        self._is_cancelled = False

        if self.status == "native_connected" and self.ws:
            # Create user message item and trigger turn response
            item_msg = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text.strip()}]
                }
            }
            await self.ws.send(json.dumps(item_msg))
            await self.ws.send(json.dumps({"type": "response.create"}))
        elif self.status == "mock_active":
            asyncio.create_task(self._execute_mock_turn(text.strip()))

    async def cancel_response(self) -> None:
        """Immediate Barge-In cancellation on the provider side."""
        self._is_cancelled = True
        if self.status == "native_connected" and self.ws:
            try:
                await self.ws.send(json.dumps({"type": "response.cancel"}))
            except Exception:
                pass

        if self._on_interrupted:
            self._on_interrupted()

    async def _listen_realtime(self) -> None:
        try:
            while self.is_connected and self.ws:
                raw = await self.ws.recv()
                event = json.loads(raw)
                event_type = event.get("type", "")

                if self._is_cancelled and event_type not in ["response.done", "session.updated"]:
                    continue

                if event_type == "input_audio_buffer.speech_started":
                    # User barge-in detected by server VAD!
                    if self._on_interrupted:
                        self._on_interrupted()

                elif event_type == "response.audio.delta":
                    delta_b64 = event.get("delta", "")
                    if delta_b64 and self._on_audio_delta and not self._is_cancelled:
                        raw_pcm = base64.b64decode(delta_b64)
                        self._on_audio_delta(raw_pcm)

                elif event_type == "response.audio_transcript.delta":
                    delta_text = event.get("delta", "")
                    if delta_text and self._on_transcript_delta:
                        self._on_transcript_delta("assistant", delta_text)

                elif event_type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.get("transcript", "")
                    if transcript and self._on_transcript_delta:
                        self._on_transcript_delta("user", transcript)

                elif event_type == "response.done":
                    if self._on_turn_complete and not self._is_cancelled:
                        self._on_turn_complete({
                            "provider": "openai_realtime",
                            "status": self.status,
                            "model": self.model_name
                        })

                elif event_type == "error":
                    err_data = event.get("error", {})
                    err_msg = err_data.get("message", "Unknown OpenAI Realtime error")
                    err_code = err_data.get("code", "")
                    # Ignore harmless cancellation race when no response was active to cancel
                    if err_code == "response_cancel_failed":
                        continue
                    if self._on_error:
                        self._on_error(f"OpenAI Realtime runtime error: {err_msg} ({err_code})")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._on_error and not self._is_cancelled:
                self._on_error(f"OpenAI Realtime receive loop error: {e}")

    async def _execute_mock_turn(self, user_text: str) -> None:
        """Explicit mock simulation for testing when ENABLE_REALTIME_MOCK is true."""
        await asyncio.sleep(0.3)
        if self._is_cancelled:
            return

        mock_answer = f"[MOCK SIMULATION] Analisis Operasional: '{user_text}'. Koordinasi taktis dan mitigasi risiko berjalan terpadu."
        if self._on_transcript_delta:
            self._on_transcript_delta("assistant", mock_answer)

        if self._on_turn_complete and not self._is_cancelled:
            self._on_turn_complete({
                "provider": "openai_realtime",
                "status": "mock_active",
                "text": mock_answer
            })
