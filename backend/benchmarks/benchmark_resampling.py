"""
Comprehensive, Rigorous Audio Resampling Benchmark & Verification Suite
Phase 5 Independent Validation.

Compares:
1. Legacy Linear Interpolation
2. Production Catmull-Rom C1 Spline (Stateless & Stateful Overlap)
3. Standard Polyphase Kaiser-Windowed Sinc FIR (via scipy.signal.resample_poly)

Signal Test Matrix:
- Multi-frequency sinusoid passband: 300Hz, 1000Hz, 2500Hz, 4000Hz, 6000Hz
- Nyquist boundary frequencies: 7000Hz, 7500Hz (Fs_in = 16kHz, Nyquist = 8kHz)
- Wideband swept sine (chirp: 200Hz to 7500Hz)
- Unit impulse response: delta[n]
- Synthetic speech-like formant fixture (F0=130Hz, F1=700Hz, F2=1220Hz, F3=2600Hz)
- Irregular streaming chunks: [193, 333, 512, 193, 1024, 333] testing cumulative timing drift
"""

import time
import json
import numpy as np
import scipy.signal

# ---------------------------------------------------------
# Algorithms under Test
# ---------------------------------------------------------

def resample_linear(pcm_16k_bytes: bytes) -> bytes:
    """Legacy Linear Interpolation."""
    if not pcm_16k_bytes or len(pcm_16k_bytes) % 2 != 0:
        return pcm_16k_bytes
    in_arr = np.frombuffer(pcm_16k_bytes, dtype=np.int16).astype(np.float32)
    n = len(in_arr)
    if n == 0:
        return b""
    num_out = int(n * 1.5)
    t_in = np.linspace(0, 1, n, endpoint=False)
    t_out = np.linspace(0, 1, num_out, endpoint=False)
    out_arr = np.interp(t_out, t_in, in_arr).astype(np.int16)
    return out_arr.tobytes()

def resample_catmull_rom_stateless(pcm_16k_bytes: bytes) -> bytes:
    """Stateless Catmull-Rom C1 Spline."""
    if not pcm_16k_bytes or len(pcm_16k_bytes) % 2 != 0:
        return pcm_16k_bytes
    in_arr = np.frombuffer(pcm_16k_bytes, dtype=np.int16).astype(np.float32)
    n = len(in_arr)
    if n == 0:
        return b""
    if n < 4:
        num_out = int(n * 1.5)
        return np.interp(np.linspace(0, 1, num_out, endpoint=False), np.linspace(0, 1, n, endpoint=False), in_arr).astype(np.int16).tobytes()

    num_out = int(n * 1.5)
    pos = np.arange(num_out, dtype=np.float32) * (2.0 / 3.0)
    idx = np.floor(pos).astype(np.int32)
    t = pos - idx

    i0 = np.clip(idx - 1, 0, n - 1)
    i1 = np.clip(idx,     0, n - 1)
    i2 = np.clip(idx + 1, 0, n - 1)
    i3 = np.clip(idx + 2, 0, n - 1)

    p0, p1, p2, p3 = in_arr[i0], in_arr[i1], in_arr[i2], in_arr[i3]
    a = -0.5 * p0 + 1.5 * p1 - 1.5 * p2 + 0.5 * p3
    b = p0 - 2.5 * p1 + 2.0 * p2 - 0.5 * p3
    c = -0.5 * p0 + 0.5 * p2
    d = p1

    out_float = ((a * t + b) * t + c) * t + d
    return np.clip(out_float, -32768, 32767).astype(np.int16).tobytes()

class StatefulAudioResampler:
    """
    Production Stateful Resampler with:
    - Phase accumulator preventing cumulative timing drift on irregular chunks.
    - C1 continuous Catmull-Rom spline with history overlap for zero boundary steps.
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

        # Save last 3 samples as overlap context for next chunk
        self.history = new_samples[-3:].copy()

        # Output sample times relative to start of new_samples
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

def resample_scipy_polyphase(pcm_16k_bytes: bytes) -> bytes:
    """Standard SciPy Kaiser-Windowed Polyphase Sinc FIR Resampler (L=3, M=2)."""
    if not pcm_16k_bytes or len(pcm_16k_bytes) % 2 != 0:
        return pcm_16k_bytes
    in_arr = np.frombuffer(pcm_16k_bytes, dtype=np.int16).astype(np.float32)
    if len(in_arr) == 0:
        return b""
    out_arr = scipy.signal.resample_poly(in_arr, 3, 2)
    return np.clip(out_arr, -32768, 32767).astype(np.int16).tobytes()

# ---------------------------------------------------------
# Benchmark Execution Engine
# ---------------------------------------------------------

def compute_snr_and_rmse(est: np.ndarray, ref: np.ndarray, trim: int = 40):
    min_len = min(len(est), len(ref))
    if min_len <= 2 * trim:
        trim = 0
    e_trim = est[trim : min_len - trim].astype(np.float64)
    r_trim = ref[trim : min_len - trim].astype(np.float64)

    # Cross-correlation delay alignment check
    xcorr = np.correlate(e_trim[:1000], r_trim[:1000], mode='full')
    delay = np.argmax(xcorr) - (len(r_trim[:1000]) - 1)
    if delay != 0 and abs(delay) < 10:
        if delay > 0:
            e_trim = e_trim[delay:]
            r_trim = r_trim[:-delay]
        else:
            e_trim = e_trim[:delay]
            r_trim = r_trim[-delay:]

    err = e_trim - r_trim
    p_sig = np.mean(r_trim ** 2)
    p_noise = np.mean(err ** 2)
    snr = 10 * np.log10(max(p_sig, 1e-12) / max(p_noise, 1e-12))
    rmse = np.sqrt(p_noise)
    return float(round(snr, 2)), float(round(rmse, 2)), int(delay)

def run_comprehensive_benchmark():
    fs_in = 16000
    fs_out = 24000
    dur = 0.25 # 250ms per signal test
    t_in = np.arange(int(fs_in * dur)) / fs_in
    t_out = np.arange(int(fs_out * dur)) / fs_out

    results = {
        "frequency_response": {},
        "chirp_sweep": {},
        "speech_formant_fixture": {},
        "impulse_response": {},
        "streaming_continuity_and_drift": {},
        "latency_by_chunk_size": {}
    }

    test_freqs = [300, 1000, 2500, 4000, 6000, 7000, 7500]

    for freq in test_freqs:
        sig_in = (np.sin(2 * np.pi * freq * t_in) * 28000).astype(np.int16).tobytes()
        sig_ref = (np.sin(2 * np.pi * freq * t_out) * 28000).astype(np.float32)

        lin_out = np.frombuffer(resample_linear(sig_in), dtype=np.int16)
        cat_out = np.frombuffer(resample_catmull_rom_stateless(sig_in), dtype=np.int16)
        sci_out = np.frombuffer(resample_scipy_polyphase(sig_in), dtype=np.int16)

        snr_lin, rmse_lin, _ = compute_snr_and_rmse(lin_out, sig_ref)
        snr_cat, rmse_cat, _ = compute_snr_and_rmse(cat_out, sig_ref)
        snr_sci, rmse_sci, delay_sci = compute_snr_and_rmse(sci_out, sig_ref)

        results["frequency_response"][str(freq)] = {
            "linear": {"snr_db": snr_lin, "rmse": rmse_lin},
            "catmull_rom": {"snr_db": snr_cat, "rmse": rmse_cat},
            "scipy_polyphase": {"snr_db": snr_sci, "rmse": rmse_sci, "delay_samples": delay_sci}
        }

    # Chirp sweep (200Hz to 7500Hz)
    chirp_in = (scipy.signal.chirp(t_in, f0=200, t1=dur, f1=7500) * 28000).astype(np.int16).tobytes()
    chirp_ref = (scipy.signal.chirp(t_out, f0=200, t1=dur, f1=7500) * 28000).astype(np.float32)

    c_lin = np.frombuffer(resample_linear(chirp_in), dtype=np.int16)
    c_cat = np.frombuffer(resample_catmull_rom_stateless(chirp_in), dtype=np.int16)
    c_sci = np.frombuffer(resample_scipy_polyphase(chirp_in), dtype=np.int16)

    results["chirp_sweep"] = {
        "linear": compute_snr_and_rmse(c_lin, chirp_ref)[:2],
        "catmull_rom": compute_snr_and_rmse(c_cat, chirp_ref)[:2],
        "scipy_polyphase": compute_snr_and_rmse(c_sci, chirp_ref)[:2]
    }

    # Synthetic Speech Formant Fixture: F0=130Hz, F1=700Hz, F2=1220Hz, F3=2600Hz
    speech_in_f = (
        0.5 * np.sin(2 * np.pi * 130 * t_in) +
        0.3 * np.sin(2 * np.pi * 700 * t_in) +
        0.15 * np.sin(2 * np.pi * 1220 * t_in) +
        0.05 * np.sin(2 * np.pi * 2600 * t_in)
    )
    speech_in_bytes = (speech_in_f * 28000).astype(np.int16).tobytes()

    speech_ref_f = (
        0.5 * np.sin(2 * np.pi * 130 * t_out) +
        0.3 * np.sin(2 * np.pi * 700 * t_out) +
        0.15 * np.sin(2 * np.pi * 1220 * t_out) +
        0.05 * np.sin(2 * np.pi * 2600 * t_out)
    ) * 28000

    sp_lin = np.frombuffer(resample_linear(speech_in_bytes), dtype=np.int16)
    sp_cat = np.frombuffer(resample_catmull_rom_stateless(speech_in_bytes), dtype=np.int16)
    sp_sci = np.frombuffer(resample_scipy_polyphase(speech_in_bytes), dtype=np.int16)

    results["speech_formant_fixture"] = {
        "linear": compute_snr_and_rmse(sp_lin, speech_ref_f)[:2],
        "catmull_rom": compute_snr_and_rmse(sp_cat, speech_ref_f)[:2],
        "scipy_polyphase": compute_snr_and_rmse(sp_sci, speech_ref_f)[:2]
    }

    # Impulse Response: Delta at sample 100
    impulse_in = np.zeros(len(t_in), dtype=np.float32)
    impulse_in[100] = 30000.0
    imp_bytes = impulse_in.astype(np.int16).tobytes()

    imp_lin = np.frombuffer(resample_linear(imp_bytes), dtype=np.int16)
    imp_cat = np.frombuffer(resample_catmull_rom_stateless(imp_bytes), dtype=np.int16)
    imp_sci = np.frombuffer(resample_scipy_polyphase(imp_bytes), dtype=np.int16)

    results["impulse_response"] = {
        "linear_peak": float(np.max(imp_lin)),
        "catmull_rom_peak": float(np.max(imp_cat)),
        "scipy_polyphase_peak": float(np.max(imp_sci)),
        "catmull_rom_overshoot": float(round((np.max(imp_cat) - 30000.0) / 30000.0 * 100.0, 2)),
        "scipy_overshoot": float(round((np.max(imp_sci) - 30000.0) / 30000.0 * 100.0, 2))
    }

    # Irregular Streaming Chunks & Cumulative Drift Verification
    irregular_chunk_sizes = [193, 333, 512, 193, 1024, 333, 400]
    total_input_len = sum(irregular_chunk_sizes)
    t_stream_in = np.arange(total_input_len) / fs_in
    full_audio_in = (np.sin(2 * np.pi * 1000 * t_stream_in) * 25000).astype(np.int16)

    # 1. Stateless Catmull-Rom streaming (naive)
    stateless_chunks = []
    idx_ptr = 0
    for sz in irregular_chunk_sizes:
        c = full_audio_in[idx_ptr : idx_ptr + sz].tobytes()
        stateless_chunks.append(np.frombuffer(resample_catmull_rom_stateless(c), dtype=np.int16))
        idx_ptr += sz
    stateless_streamed = np.concatenate(stateless_chunks)

    # 2. Stateful Resampler streaming
    stateful_resampler = StatefulAudioResampler()
    stateful_chunks = []
    idx_ptr = 0
    for sz in irregular_chunk_sizes:
        c = full_audio_in[idx_ptr : idx_ptr + sz].tobytes()
        stateful_chunks.append(np.frombuffer(stateful_resampler.resample_chunk(c), dtype=np.int16))
        idx_ptr += sz
    stateful_streamed = np.concatenate(stateful_chunks)

    # 3. SciPy streaming
    scipy_chunks = []
    idx_ptr = 0
    for sz in irregular_chunk_sizes:
        c = full_audio_in[idx_ptr : idx_ptr + sz].tobytes()
        scipy_chunks.append(np.frombuffer(resample_scipy_polyphase(c), dtype=np.int16))
        idx_ptr += sz
    scipy_streamed = np.concatenate(scipy_chunks)

    expected_out_samples = int(total_input_len * 1.5)
    results["streaming_continuity_and_drift"] = {
        "total_in_samples": total_input_len,
        "expected_out_samples": expected_out_samples,
        "stateless_out_samples": len(stateless_streamed),
        "stateless_timing_drift_samples": expected_out_samples - len(stateless_streamed),
        "stateful_out_samples": len(stateful_streamed),
        "stateful_timing_drift_samples": expected_out_samples - len(stateful_streamed),
        "scipy_out_samples": len(scipy_streamed),
        "scipy_timing_drift_samples": expected_out_samples - len(scipy_streamed)
    }

    # Latency comparison across chunk sizes
    bench_sizes = [193, 256, 512, 1024, 2048, 4096]
    for sz in bench_sizes:
        raw_test = (np.sin(np.linspace(0, 5, sz)) * 20000).astype(np.int16).tobytes()
        iters = 50

        # Linear
        t0 = time.perf_counter()
        for _ in range(iters):
            resample_linear(raw_test)
        dt_lin = ((time.perf_counter() - t0) / iters) * 1000.0

        # Catmull-Rom
        t0 = time.perf_counter()
        for _ in range(iters):
            resample_catmull_rom_stateless(raw_test)
        dt_cat = ((time.perf_counter() - t0) / iters) * 1000.0

        # Stateful Catmull-Rom
        s_res = StatefulAudioResampler()
        t0 = time.perf_counter()
        for _ in range(iters):
            s_res.resample_chunk(raw_test)
        dt_state = ((time.perf_counter() - t0) / iters) * 1000.0

        # SciPy Polyphase
        t0 = time.perf_counter()
        for _ in range(iters):
            resample_scipy_polyphase(raw_test)
        dt_sci = ((time.perf_counter() - t0) / iters) * 1000.0

        results["latency_by_chunk_size"][str(sz)] = {
            "linear_ms": round(dt_lin, 3),
            "catmull_rom_stateless_ms": round(dt_cat, 3),
            "stateful_catmull_rom_ms": round(dt_state, 3),
            "scipy_polyphase_ms": round(dt_sci, 3)
        }

    return results

if __name__ == "__main__":
    benchmark_data = run_comprehensive_benchmark()
    print(json.dumps(benchmark_data, indent=2))
