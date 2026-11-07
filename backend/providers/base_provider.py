from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any, List
import asyncio

class BaseRealtimeProvider(ABC):
    """
    Abstract Base Class for Real-Time Speech-to-Speech / Streaming Audio Providers.
    Standardizes Gemini Live and OpenAI Realtime event interfaces.
    """

    def __init__(self, provider_id: str, model_name: str):
        self.provider_id = provider_id
        self.model_name = model_name
        self.is_connected = False
        self.status = "disconnected"  # 'disconnected', 'connecting', 'native_connected', 'bridge_active', 'mock_active', 'error'
        self.status_detail = ""
        self._on_audio_delta: Optional[Callable[[bytes], Any]] = None
        self._on_transcript_delta: Optional[Callable[[str, str], Any]] = None  # (role, text)
        self._on_turn_complete: Optional[Callable[[Dict[str, Any]], Any]] = None
        self._on_interrupted: Optional[Callable[[], Any]] = None
        self._on_error: Optional[Callable[[str], Any]] = None
        self._on_status_change: Optional[Callable[[str, str], Any]] = None  # (status, detail)

    def set_status(self, status: str, detail: str = "") -> None:
        self.status = status
        self.status_detail = detail
        if status in ("native_connected", "bridge_active", "mock_active"):
            self.is_connected = True
        elif status in ("disconnected", "error"):
            self.is_connected = False
        if self._on_status_change:
            self._on_status_change(status, detail)

    def set_callbacks(
        self,
        on_audio_delta: Optional[Callable[[bytes], Any]] = None,
        on_transcript_delta: Optional[Callable[[str, str], Any]] = None,
        on_turn_complete: Optional[Callable[[Dict[str, Any]], Any]] = None,
        on_interrupted: Optional[Callable[[], Any]] = None,
        on_error: Optional[Callable[[str], Any]] = None,
        on_status_change: Optional[Callable[[str, str], Any]] = None,
    ):
        self._on_audio_delta = on_audio_delta
        self._on_transcript_delta = on_transcript_delta
        self._on_turn_complete = on_turn_complete
        self._on_interrupted = on_interrupted
        self._on_error = on_error
        self._on_status_change = on_status_change

    @abstractmethod
    async def connect(self, system_instruction: str = "", voice: str = "") -> bool:
        """Initialize connection/session with the provider."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly close session and free resources."""
        pass

    @abstractmethod
    async def send_audio_chunk(self, pcm_bytes: bytes) -> None:
        """Stream an incoming PCM audio chunk (16kHz or 24kHz) from user microphone."""
        pass

    @abstractmethod
    async def send_text(self, text: str) -> None:
        """Inject text directly into the live conversation turn."""
        pass

    @abstractmethod
    async def cancel_response(self) -> None:
        """Trigger immediate barge-in cancellation on the provider side."""
        pass
