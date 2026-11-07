import pytest
import io
import wave
import struct
from utils.audio_parser import (
    parse_and_validate_audio,
    extract_pcm16_samples,
    AudioParserError,
    AudioFormatError
)

def test_empty_audio_bytes():
    pcm, meta = parse_and_validate_audio(b"")
    assert pcm == b""
    assert meta.pcm_bytes_length == 0
    assert extract_pcm16_samples(b"") == b""

def test_raw_pcm16_valid_and_odd_length():
    # 4 samples = 8 bytes
    valid_pcm = b"\x00\x01\x00\x02\x00\x03\x00\x04"
    pcm, meta = parse_and_validate_audio(valid_pcm)
    assert pcm == valid_pcm
    assert not meta.is_wav
    assert meta.pcm_bytes_length == 8

    # Odd length byte array violates 16-bit boundary
    odd_pcm = b"\x00\x01\x00\x02\x00"
    with pytest.raises(AudioParserError, match="odd"):
        parse_and_validate_audio(odd_pcm)
    # extract_pcm16_samples should safely catch and return b""
    assert extract_pcm16_samples(odd_pcm) == b""

def test_standard_pcm16_wav():
    raw_samples = (b"\x12\x34\x56\x78" * 50) # 200 bytes
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(raw_samples)
    wav_bytes = buf.getvalue()

    pcm, meta = parse_and_validate_audio(wav_bytes, expected_sample_rate=24000, expected_channels=1)
    assert pcm == raw_samples
    assert meta.is_wav is True
    assert meta.sample_rate == 24000
    assert meta.channels == 1
    assert meta.bits_per_sample == 16
    assert meta.pcm_bytes_length == 200

def test_wav_with_metadata_and_odd_padding():
    raw_samples = b"\xAA\x55" * 100 # 200 bytes
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(raw_samples)
    base_wav = buf.getvalue()

    # Create an odd-length custom chunk: ID="TEST", size=7, data=b"1234567" + 1 pad byte
    custom_chunk = b"TEST\x07\x00\x00\x001234567\x00" # 4 + 4 + 7 + 1 = 16 bytes
    # Insert before 'data' chunk (at byte 36)
    enhanced_wav = base_wav[:36] + custom_chunk + base_wav[36:]
    # Fix RIFF size header
    enhanced_wav = enhanced_wav[:4] + struct.pack('<I', len(enhanced_wav) - 8) + enhanced_wav[8:]

    pcm, meta = parse_and_validate_audio(enhanced_wav)
    assert pcm == raw_samples
    assert meta.is_wav is True
    assert meta.sample_rate == 16000

def test_malformed_and_truncated_wav():
    # 1. Truncated before 12 bytes
    with pytest.raises(AudioParserError, match="truncated before standard 12-byte header"):
        parse_and_validate_audio(b"RIFF\x10\x00\x00")

    # 2. Missing WAVE format code
    with pytest.raises(AudioParserError, match="expected 'WAVE'"):
        parse_and_validate_audio(b"RIFF\x20\x00\x00\x00AVI \x00\x00\x00\x00\x00\x00\x00\x00")

    # 3. Truncated chunk payload
    bad_chunk_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \xff\x00\x00\x00\x01\x00"
    with pytest.raises(AudioParserError, match="specifies .* bytes but only"):
        parse_and_validate_audio(bad_chunk_wav)

def test_unsupported_audio_format_and_sample_rates():
    # 1. Reject compressed container (e.g. OGG)
    with pytest.raises(AudioFormatError, match="Unsupported compressed audio container"):
        parse_and_validate_audio(b"OggS\x00\x02\x00\x00\x00\x00\x00\x00")

    # 2. Sample rate mismatch validation
    raw_samples = b"\x01\x02" * 50
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(raw_samples)
    wav_8k = buf.getvalue()

    with pytest.raises(AudioFormatError, match="Sample rate mismatch"):
        parse_and_validate_audio(wav_8k, expected_sample_rate=24000)

    # 3. Channel count mismatch validation
    buf_stereo = io.BytesIO()
    with wave.open(buf_stereo, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(raw_samples * 2)
    wav_stereo = buf_stereo.getvalue()

    with pytest.raises(AudioFormatError, match="Channel count mismatch"):
        parse_and_validate_audio(wav_stereo, expected_channels=1)

def test_mime_type_validation_and_rate_extraction():
    # 1. Reject compressed MIME types
    with pytest.raises(AudioFormatError, match="Unsupported compressed audio MIME type"):
        parse_and_validate_audio(b"\x00\x01\x00\x02", mime_type="audio/mp3")

    with pytest.raises(AudioFormatError, match="Unsupported compressed audio MIME type"):
        parse_and_validate_audio(b"\x00\x01\x00\x02", mime_type="audio/ogg; codecs=opus")

    # 2. Extract sample rate from MIME type
    pcm_bytes = b"\x00\x01\x00\x02" * 10
    pcm, meta = parse_and_validate_audio(pcm_bytes, mime_type="audio/pcm;rate=16000")
    assert meta.sample_rate == 16000

    # 3. Mismatch between expected_sample_rate and MIME type rate parameter
    with pytest.raises(AudioFormatError, match="Sample rate mismatch"):
        parse_and_validate_audio(pcm_bytes, expected_sample_rate=24000, mime_type="audio/pcm;rate=16000")
