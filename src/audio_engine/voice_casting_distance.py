"""Cheap acoustic pre-filter for Voice Casting Lab.

This module is deliberately heuristic. It does not prove speaker identity and must
never promote a voice. Its purpose is only to reject obviously too-similar anchor
pairs before expensive expressive rendering and human review.

The implementation uses only the Python standard library so the pre-filter adds no
model download, no network dependency and negligible CI cost.
"""
from __future__ import annotations

import math
import statistics
import struct
import wave
from pathlib import Path

BAND_FREQUENCIES_HZ = (200.0, 400.0, 700.0, 1100.0, 1700.0, 2500.0, 3500.0)
MAX_ANALYSIS_SECONDS = 8.0


class CastingDistanceError(ValueError):
    pass


def _read_pcm16_mono(path: Path, *, max_seconds: float = MAX_ANALYSIS_SECONDS):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    with wave.open(str(path), "rb") as stream:
        channels = stream.getnchannels()
        sample_width = stream.getsampwidth()
        sample_rate = stream.getframerate()
        compression = stream.getcomptype()
        total_frames = stream.getnframes()
        if channels != 1 or sample_width != 2 or compression != "NONE":
            raise CastingDistanceError("casting distance expects mono PCM16 WAV anchors")
        if sample_rate < 8000:
            raise CastingDistanceError("sample rate is too low for the acoustic pre-filter")
        frame_count = min(total_frames, int(sample_rate * max_seconds))
        raw = stream.readframes(frame_count)
    if not raw:
        raise CastingDistanceError("empty WAV anchor")
    sample_count = len(raw) // 2
    samples = list(struct.unpack(f"<{sample_count}h", raw[: sample_count * 2]))
    mean = sum(samples) / len(samples)
    centered = [sample - mean for sample in samples]
    return centered, sample_rate, total_frames / sample_rate


def _estimate_f0(samples, sample_rate):
    # Downsample to roughly 6 kHz: enough for 75-350 Hz pitch while keeping the
    # autocorrelation cheap. Prefer the shortest lag close to the best peak to
    # reduce common octave errors.
    factor = max(1, round(sample_rate / 6000))
    down = samples[::factor]
    rate = sample_rate / factor
    frame_len = max(64, int(rate * 0.04))
    min_lag = max(2, int(rate / 350))
    max_lag = min(frame_len // 2, int(rate / 75))
    if len(down) < frame_len or max_lag <= min_lag:
        return None
    global_rms = math.sqrt(sum(value * value for value in down) / len(down))
    estimates = []
    for start in range(0, len(down) - frame_len + 1, frame_len):
        frame = down[start : start + frame_len]
        mean = sum(frame) / len(frame)
        frame = [value - mean for value in frame]
        rms = math.sqrt(sum(value * value for value in frame) / len(frame))
        if rms < global_rms * 0.2:
            continue
        correlations = []
        for lag in range(min_lag, max_lag + 1):
            left = frame[:-lag]
            right = frame[lag:]
            dot = sum(a * b for a, b in zip(left, right))
            left_energy = sum(value * value for value in left)
            right_energy = sum(value * value for value in right)
            if left_energy and right_energy:
                correlations.append((dot / math.sqrt(left_energy * right_energy), lag))
        if not correlations:
            continue
        best = max(value for value, _ in correlations)
        threshold = max(0.55, best - 0.02)
        plausible = [lag for value, lag in correlations if value >= threshold]
        if plausible:
            estimates.append(rate / min(plausible))
    return statistics.median(estimates) if estimates else None


def _goertzel_power(samples, sample_rate, frequency):
    # At most the first three seconds are needed for a cheap, stable timbre proxy.
    factor = max(1, int(sample_rate // 10000))
    values = samples[: int(sample_rate * 3.0) : factor]
    rate = sample_rate / factor
    if not values or frequency >= rate / 2:
        return 0.0
    omega = 2.0 * math.pi * frequency / rate
    coefficient = 2.0 * math.cos(omega)
    s1 = s2 = 0.0
    for value in values:
        current = value + coefficient * s1 - s2
        s2 = s1
        s1 = current
    return max(0.0, s1 * s1 + s2 * s2 - coefficient * s1 * s2)


def acoustic_profile(path):
    samples, sample_rate, duration = _read_pcm16_mono(Path(path))
    rms = math.sqrt(sum(value * value for value in samples) / len(samples)) / 32768.0
    zero_crossings = sum(
        1
        for left, right in zip(samples, samples[1:])
        if (left < 0 <= right) or (right < 0 <= left)
    )
    zcr = zero_crossings / max(1, len(samples) - 1)
    f0_hz = _estimate_f0(samples, sample_rate)
    powers = [_goertzel_power(samples, sample_rate, freq) for freq in BAND_FREQUENCIES_HZ]
    total_power = sum(powers) or 1.0
    spectral_shape = [power / total_power for power in powers]
    return {
        "duration_seconds": round(duration, 6),
        "sample_rate": sample_rate,
        "rms": rms,
        "zero_crossing_rate": zcr,
        "f0_hz": f0_hz,
        "spectral_shape": spectral_shape,
    }


def profile_distance(left, right):
    left_f0, right_f0 = left.get("f0_hz"), right.get("f0_hz")
    if left_f0 and right_f0:
        pitch = min(abs(math.log2(left_f0 / right_f0)) / 0.5, 1.0)
    else:
        pitch = 0.5

    left_duration = max(float(left["duration_seconds"]), 1e-6)
    right_duration = max(float(right["duration_seconds"]), 1e-6)
    duration = min(abs(math.log(left_duration / right_duration)) / math.log(1.5), 1.0)

    zcr = min(
        abs(float(left["zero_crossing_rate"]) - float(right["zero_crossing_rate"])) / 0.08,
        1.0,
    )

    left_rms = max(float(left["rms"]), 1e-9)
    right_rms = max(float(right["rms"]), 1e-9)
    rms_db = abs(20.0 * math.log10(left_rms / right_rms))
    rms = min(rms_db / 12.0, 1.0)

    left_shape = left["spectral_shape"]
    right_shape = right["spectral_shape"]
    if len(left_shape) != len(right_shape):
        raise CastingDistanceError("spectral profile dimensions do not match")
    spectral = math.sqrt(sum((a - b) ** 2 for a, b in zip(left_shape, right_shape))) / math.sqrt(2.0)

    components = {
        "pitch": pitch,
        "spectral": spectral,
        "duration": duration,
        "zero_crossing": zcr,
        "rms": rms,
    }
    score = 100.0 * (
        0.30 * pitch
        + 0.45 * spectral
        + 0.10 * duration
        + 0.10 * zcr
        + 0.05 * rms
    )
    return {"score": round(score, 3), "components": components}


def compare_anchors(left_path, right_path):
    left = acoustic_profile(left_path)
    right = acoustic_profile(right_path)
    return {"left": left, "right": right, **profile_distance(left, right)}


def contrast_gate(
    candidate_left,
    candidate_right,
    baseline_left,
    baseline_right,
    *,
    minimum_ratio=1.35,
    minimum_margin=8.0,
):
    """Require a candidate pair to be materially farther apart than a bad baseline.

    The known-confusable baseline is intentionally used instead of pretending that
    one universal absolute score can define human speaker identity.
    """
    candidate = compare_anchors(candidate_left, candidate_right)
    baseline = compare_anchors(baseline_left, baseline_right)
    required = max(
        baseline["score"] * float(minimum_ratio),
        baseline["score"] + float(minimum_margin),
    )
    return {
        "schema": "voice-casting-distance-gate-v1",
        "eligible": candidate["score"] >= required,
        "candidate_score": candidate["score"],
        "baseline_score": baseline["score"],
        "required_score": round(required, 3),
        "minimum_ratio": float(minimum_ratio),
        "minimum_margin": float(minimum_margin),
        "candidate": candidate,
        "baseline": baseline,
        "claim": "prefilter-only-not-speaker-identity-qualification",
    }
