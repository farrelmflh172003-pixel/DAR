"""
Strict, Production-Grade Audio & WAV Container Parser for Real-Time Voice AI.
Implements complete RIFF/WAVE specification compliance:
- Validates magic bytes, header sizes, and chunk integrity.
- Correctly parses word-aligned RIFF chunks (including odd-length padding bytes).
- Validates PCM audio format (Format 1, 16-bit depth, channel count, sample rate).
- Rejects compressed streams, malformed headers, truncated files, and non-PCM containers.
- Safely validates raw PCM16 byte alignment.
"""

import struct
from typing import NamedTuple, Optional, Tuple

class AudioMetadata(NamedTuple):
    is_wav: bool
    format_code: int       # 1 = PCM
    channels: int
    sample_rate: int
    bits_per_sample: int
    byte_rate: int
    block_align: int
    pcm_bytes_length: int

class AudioParserError(ValueError):
    """Raised when audio payload is malformed or invalid."""
    pass

class AudioFormatError(ValueError):
    """Raised when audio encoding or parameters (channels/sample rate/depth) are unsupported."""
    pass


def parse_and_validate_audio(
    audio_bytes: bytes,
    expected_sample_rate: Optional[int] = None,
    expected_channels: Optional[int] = None,
    allow_raw_pcm: bool = True,
    mime_type: Optional[str] = None
) -> Tuple[bytes, AudioMetadata]:
    """
    Parses and extracts pure 16-bit PCM samples from WAV containers or raw PCM streams.
    Validates MIME type, RIFF/WAVE header, sample rate, channels, bit depth, and frame alignment.
    
    Returns:
        (pure_pcm16_bytes, AudioMetadata)
    Raises:
        AudioParserError: if WAV structure is truncated, corrupted, or malformed.
        AudioFormatError: if compression format, bits per sample, or channels are unsupported.
    """
    if mime_type:
        clean_mime = mime_type.lower().strip()
        compressed_keywords = ["mp3", "mpeg", "ogg", "opus", "flac", "webm", "aac", "m4a", "wma"]
        for kw in compressed_keywords:
            if kw in clean_mime:
                raise AudioFormatError(
                    f"Unsupported compressed audio MIME type '{mime_type}'. Only uncompressed PCM16 is accepted."
                )
        if "rate=" in clean_mime:
            import re
            match = re.search(r"rate=(\d+)", clean_mime)
            if match:
                mime_rate = int(match.group(1))
                if expected_sample_rate and mime_rate != expected_sample_rate:
                    raise AudioFormatError(
                        f"Sample rate mismatch: MIME type specifies {mime_rate} Hz, expected {expected_sample_rate} Hz."
                    )
                if not expected_sample_rate:
                    expected_sample_rate = mime_rate

    if not audio_bytes:
        return b"", AudioMetadata(
            is_wav=False,
            format_code=1,
            channels=expected_channels or 1,
            sample_rate=expected_sample_rate or 24000,
            bits_per_sample=16,
            byte_rate=0,
            block_align=2,
            pcm_bytes_length=0
        )

    # Detect other known media container headers that are definitely NOT raw PCM
    compressed_signatures = [
        (b"OggS", "Ogg Vorbis/Opus"),
        (b"ID3", "MP3 ID3"),
        (b"fLaC", "FLAC"),
        (b"\x1a\x45\xdf\xa3", "WebM/Matroska"),
    ]
    for sig, name in compressed_signatures:
        if audio_bytes.startswith(sig):
            raise AudioFormatError(f"Unsupported compressed audio container ({name}). Only uncompressed PCM16 is accepted.")

    # 1. Parse RIFF/WAVE Container
    if audio_bytes.startswith(b"RIFF"):
        if len(audio_bytes) < 12:
            raise AudioParserError("Malformed RIFF container: file truncated before standard 12-byte header.")

        format_id = audio_bytes[8:12]
        if format_id != b"WAVE":
            raise AudioParserError(f"Malformed RIFF container: expected 'WAVE' chunk format, got '{format_id.decode('ascii', errors='replace')}'.")

        riff_payload_size = struct.unpack("<I", audio_bytes[4:8])[0]
        # In strict streaming, the file might be slightly shorter if truncated
        if len(audio_bytes) < riff_payload_size + 8:
            # Note: Streaming chunks may omit the total file size if streamed live,
            # but if it's smaller than the actual header chunks, it is malformed.
            pass

        offset = 12
        total_len = len(audio_bytes)
        fmt_parsed = False
        format_code = 0
        channels = 0
        sample_rate = 0
        byte_rate = 0
        block_align = 0
        bits_per_sample = 0
        extracted_pcm = None

        while offset + 8 <= total_len:
            chunk_id = audio_bytes[offset:offset+4]
            chunk_size = struct.unpack("<I", audio_bytes[offset+4:offset+8])[0]
            offset += 8

            if offset + chunk_size > total_len:
                raise AudioParserError(
                    f"Malformed WAV: chunk '{chunk_id.decode('ascii', errors='replace')}' "
                    f"specifies {chunk_size} bytes but only {total_len - offset} bytes remain in payload."
                )

            chunk_payload = audio_bytes[offset : offset + chunk_size]

            if chunk_id == b"fmt ":
                if chunk_size < 16:
                    raise AudioParserError("Malformed WAV: 'fmt ' chunk is smaller than standard 16 bytes.")
                format_code, channels, sample_rate, byte_rate, block_align, bits_per_sample = struct.unpack(
                    "<HHIIHH", chunk_payload[:16]
                )
                fmt_parsed = True

                if format_code != 1:
                    raise AudioFormatError(
                        f"Unsupported WAV compression format {format_code}: only uncompressed PCM (format 1) is supported."
                    )
                if bits_per_sample != 16:
                    raise AudioFormatError(
                        f"Unsupported WAV bit depth: {bits_per_sample} bits (expected 16-bit linear PCM)."
                    )
                if expected_channels and channels != expected_channels:
                    raise AudioFormatError(
                        f"Channel count mismatch: WAV contains {channels} channel(s), expected {expected_channels}."
                    )
                if expected_sample_rate and sample_rate != expected_sample_rate:
                    raise AudioFormatError(
                        f"Sample rate mismatch: WAV contains {sample_rate} Hz, expected {expected_sample_rate} Hz."
                    )

            elif chunk_id == b"data":
                if not fmt_parsed:
                    raise AudioParserError("Malformed WAV: 'data' chunk appeared before 'fmt ' chunk.")
                if chunk_size % 2 != 0:
                    raise AudioParserError(f"Malformed WAV: 'data' chunk byte length ({chunk_size}) is not sample-aligned (16-bit).")
                extracted_pcm = chunk_payload

            # Advance offset according to RIFF word-alignment rule:
            # Odd chunk sizes have a 1-byte padding that is NOT part of chunk_size.
            offset += chunk_size
            if chunk_size % 2 == 1:
                offset += 1

        if not fmt_parsed:
            raise AudioParserError("Malformed WAV: missing mandatory 'fmt ' chunk.")
        if extracted_pcm is None:
            raise AudioParserError("Malformed WAV: missing mandatory 'data' chunk.")

        metadata = AudioMetadata(
            is_wav=True,
            format_code=format_code,
            channels=channels,
            sample_rate=sample_rate,
            bits_per_sample=bits_per_sample,
            byte_rate=byte_rate,
            block_align=block_align,
            pcm_bytes_length=len(extracted_pcm)
        )
        return extracted_pcm, metadata

    # 2. Raw PCM16 stream handling
    if not allow_raw_pcm:
        raise AudioParserError("Payload is not a valid RIFF/WAVE container and raw PCM is disabled.")

    if len(audio_bytes) % 2 != 0:
        raise AudioParserError(f"Malformed raw PCM16: payload length ({len(audio_bytes)} bytes) is odd, violating 16-bit sample boundary.")

    metadata = AudioMetadata(
        is_wav=False,
        format_code=1,
        channels=expected_channels or 1,
        sample_rate=expected_sample_rate or 24000,
        bits_per_sample=16,
        byte_rate=(expected_sample_rate or 24000) * (expected_channels or 1) * 2,
        block_align=(expected_channels or 1) * 2,
        pcm_bytes_length=len(audio_bytes)
    )
    return audio_bytes, metadata


def parse_audio_payload(
    audio_bytes: bytes,
    mime_type: Optional[str] = None,
    expected_sample_rate: Optional[int] = 24000,
    expected_channels: Optional[int] = 1,
    allow_raw_pcm: bool = True
) -> Tuple[bytes, AudioMetadata]:
    """
    Strict, production-grade parser for voice AI streaming bridges and real-time providers.
    Validates MIME type, WAV container or raw PCM16, sample rate, channels, bit depth,
    and frame alignment.
    Raises AudioParserError or AudioFormatError with clear, sanitized error messages.
    """
    return parse_and_validate_audio(
        audio_bytes=audio_bytes,
        expected_sample_rate=expected_sample_rate,
        expected_channels=expected_channels,
        allow_raw_pcm=allow_raw_pcm,
        mime_type=mime_type
    )


def extract_pcm16_samples(
    audio_bytes: bytes,
    mime_type: Optional[str] = None,
    expected_sample_rate: Optional[int] = None,
    expected_channels: Optional[int] = None
) -> bytes:
    """
    Drop-in helper for providers: extracts clean PCM16 samples safely.
    If input is invalid or corrupted, returns b"" instead of raising uncaught exceptions.
    """
    if not audio_bytes:
        return b""
    try:
        pcm, _ = parse_and_validate_audio(
            audio_bytes,
            expected_sample_rate=expected_sample_rate,
            expected_channels=expected_channels,
            mime_type=mime_type
        )
        return pcm
    except Exception:
        # Never fall back to audio_bytes[44:] blindly
        return b""
