"""Deterministic WORLD source/filter prosody restoration for Voice Casting Lab.

The target waveform supplies the spectral envelope (identity/content carrier). The
expressive source supplies only relative F0 motion, voiced/unvoiced timing,
aperiodicity and relative frame-energy motion. Absolute target F0 and loudness
centres are retained. There are deliberately no blend-strength parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RestoreDiagnostics:
    source_sample_rate: int
    target_sample_rate: int
    source_seconds: float
    target_seconds: float
    output_seconds: float
    source_voiced_fraction: float
    target_voiced_fraction: float
    output_voiced_fraction: float
    source_median_f0: float
    target_median_f0: float
    output_median_f0: float
    peak_normalization_scale: float


def _interp_time(values, frame_count):
    import numpy as np

    values = np.asarray(values, dtype=np.float64)
    if values.shape[0] == frame_count:
        return values.copy()
    if values.shape[0] < 1 or frame_count < 1:
        raise ValueError("WORLD tracks must contain at least one frame")
    old = np.linspace(0.0, 1.0, values.shape[0])
    new = np.linspace(0.0, 1.0, frame_count)
    if values.ndim == 1:
        return np.interp(new, old, values)
    if values.ndim != 2:
        raise ValueError(f"unsupported WORLD track rank: {values.ndim}")
    out = np.empty((frame_count, values.shape[1]), dtype=np.float64)
    for column in range(values.shape[1]):
        out[:, column] = np.interp(new, old, values[:, column])
    return out


def _voiced_median(f0):
    import numpy as np

    voiced = np.asarray(f0, dtype=np.float64)
    voiced = voiced[np.isfinite(voiced) & (voiced > 0.0)]
    if voiced.size == 0:
        raise ValueError("WORLD F0 track has no voiced frames")
    return float(np.median(voiced))


def transfer_world_parameters(source_f0, source_sp, source_ap, target_f0, target_sp, target_ap):
    """Return output F0/SP/AP with target filter and source excitation dynamics.

    No tunable interpolation coefficient is accepted by design.
    """
    import numpy as np

    source_f0 = np.asarray(source_f0, dtype=np.float64)
    source_sp = np.asarray(source_sp, dtype=np.float64)
    source_ap = np.asarray(source_ap, dtype=np.float64)
    target_f0 = np.asarray(target_f0, dtype=np.float64)
    target_sp = np.asarray(target_sp, dtype=np.float64)
    target_ap = np.asarray(target_ap, dtype=np.float64)
    if source_sp.ndim != 2 or target_sp.ndim != 2 or source_ap.ndim != 2 or target_ap.ndim != 2:
        raise ValueError("WORLD SP/AP tracks must be 2-D")
    if target_sp.shape != target_ap.shape:
        raise ValueError("target WORLD SP/AP shapes differ")
    if source_sp.shape != source_ap.shape:
        raise ValueError("source WORLD SP/AP shapes differ")
    if source_sp.shape[1] != target_sp.shape[1]:
        raise ValueError("source/target WORLD frequency bins differ; resample audio before analysis")
    if len(target_f0) != target_sp.shape[0] or len(source_f0) != source_sp.shape[0]:
        raise ValueError("WORLD F0 and spectral frame counts differ")

    frame_count = len(target_f0)
    src_f0 = _interp_time(source_f0, frame_count)
    src_sp = _interp_time(source_sp, frame_count)
    src_ap = _interp_time(source_ap, frame_count)

    src_median = _voiced_median(source_f0)
    tgt_median = _voiced_median(target_f0)
    voiced = src_f0 > 0.0
    out_f0 = np.zeros(frame_count, dtype=np.float64)
    out_f0[voiced] = tgt_median * (src_f0[voiced] / src_median)
    if not np.isfinite(out_f0).all():
        raise ValueError("non-finite transferred F0")

    # WORLD spectral envelopes are power-like. Move only the source's relative
    # frame-energy trajectory onto the target envelope, preserving target median
    # level and target frequency-envelope shape frame by frame.
    eps = np.finfo(np.float64).tiny
    src_log_amp = 0.5 * np.log(np.maximum(np.mean(src_sp, axis=1), eps))
    tgt_log_amp = 0.5 * np.log(np.maximum(np.mean(target_sp, axis=1), eps))
    desired_log_amp = float(np.median(tgt_log_amp)) + (src_log_amp - float(np.median(src_log_amp)))
    amplitude_ratio = np.exp(desired_log_amp - tgt_log_amp)
    out_sp = target_sp * np.square(amplitude_ratio[:, None])

    # Aperiodicity belongs to the excitation rather than the vocal-tract filter.
    out_ap = np.clip(src_ap, 0.0, 1.0)

    if not np.isfinite(out_sp).all() or not np.isfinite(out_ap).all():
        raise ValueError("non-finite transferred WORLD parameters")
    return out_f0, out_sp, out_ap


def restore_with_world(source_wav, target_wav, output_wav) -> RestoreDiagnostics:
    """Restore expressive excitation onto a target-identity waveform."""
    import math
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    import pyworld

    source_wav = Path(source_wav)
    target_wav = Path(target_wav)
    output_wav = Path(output_wav)
    source, source_sr = sf.read(source_wav, dtype="float64", always_2d=False)
    target, target_sr = sf.read(target_wav, dtype="float64", always_2d=False)
    if source.ndim == 2:
        source = source.mean(axis=1)
    if target.ndim == 2:
        target = target.mean(axis=1)
    if source.size == 0 or target.size == 0:
        raise ValueError("source/target WAV must be non-empty")
    if source_sr != target_sr:
        divisor = math.gcd(int(source_sr), int(target_sr))
        source = resample_poly(source, target_sr // divisor, source_sr // divisor).astype(np.float64)
    source = np.ascontiguousarray(source, dtype=np.float64)
    target = np.ascontiguousarray(target, dtype=np.float64)

    source_f0, source_sp, source_ap = pyworld.wav2world(source, target_sr)
    target_f0, target_sp, target_ap = pyworld.wav2world(target, target_sr)
    out_f0, out_sp, out_ap = transfer_world_parameters(
        source_f0, source_sp, source_ap, target_f0, target_sp, target_ap
    )
    output = pyworld.synthesize(out_f0, out_sp, out_ap, target_sr)
    peak = float(np.max(np.abs(output))) if output.size else 0.0
    scale = 1.0
    if peak > 0.99:
        scale = 0.99 / peak
        output = output * scale
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_wav, output, target_sr, subtype="PCM_16")

    def frac(f0):
        return float(np.mean(np.asarray(f0) > 0.0))

    return RestoreDiagnostics(
        source_sample_rate=int(source_sr),
        target_sample_rate=int(target_sr),
        source_seconds=float(len(source) / target_sr),
        target_seconds=float(len(target) / target_sr),
        output_seconds=float(len(output) / target_sr),
        source_voiced_fraction=frac(source_f0),
        target_voiced_fraction=frac(target_f0),
        output_voiced_fraction=frac(out_f0),
        source_median_f0=_voiced_median(source_f0),
        target_median_f0=_voiced_median(target_f0),
        output_median_f0=_voiced_median(out_f0),
        peak_normalization_scale=scale,
    )
