"""Deterministic suprasegmental prosody restoration for Voice Casting Lab.

FACodec target audio retains the identity-bearing WORLD spectral envelope,
voiced/unvoiced mask and aperiodicity. The expressive source contributes only
continuous relative log-F0 motion and relative frame-energy motion. Both source
motions are re-centred on the target frame support, so target median F0 and
median spectral energy remain fixed. There are deliberately no blend-strength
parameters.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SuprasegmentalDiagnostics:
    source_sample_rate: int
    target_sample_rate: int
    source_seconds: float
    target_seconds: float
    output_seconds: float
    target_voiced_fraction: float
    output_voiced_fraction: float
    target_median_f0: float
    output_median_f0: float
    target_aperiodicity_preserved: bool
    peak_normalization_scale: float


def _voiced_median(f0):
    import numpy as np

    values = np.asarray(f0, dtype=np.float64)
    values = values[np.isfinite(values) & (values > 0.0)]
    if values.size == 0:
        raise ValueError("WORLD F0 track has no voiced frames")
    return float(np.median(values))


def _continuous_source_log_f0_motion(source_f0, target_frame_count):
    """Interpolate source relative log-F0 across unvoiced gaps and target time."""
    import numpy as np

    source_f0 = np.asarray(source_f0, dtype=np.float64)
    if source_f0.ndim != 1 or source_f0.size < 2 or target_frame_count < 1:
        raise ValueError("invalid F0 track")
    voiced = np.isfinite(source_f0) & (source_f0 > 0.0)
    if int(voiced.sum()) < 2:
        raise ValueError("source requires at least two voiced F0 frames")
    median = _voiced_median(source_f0)
    source_time = np.linspace(0.0, 1.0, source_f0.size)
    voiced_time = source_time[voiced]
    relative = np.log(source_f0[voiced] / median)
    target_time = np.linspace(0.0, 1.0, target_frame_count)
    return np.interp(target_time, voiced_time, relative)


def _relative_source_log_energy(source_sp, target_frame_count):
    import numpy as np

    source_sp = np.asarray(source_sp, dtype=np.float64)
    if source_sp.ndim != 2 or source_sp.shape[0] < 1 or target_frame_count < 1:
        raise ValueError("invalid WORLD spectral envelope")
    eps = np.finfo(np.float64).tiny
    source_log_amp = 0.5 * np.log(np.maximum(np.mean(source_sp, axis=1), eps))
    source_log_amp -= float(np.median(source_log_amp))
    old = np.linspace(0.0, 1.0, source_log_amp.size)
    new = np.linspace(0.0, 1.0, target_frame_count)
    return np.interp(new, old, source_log_amp)


def transfer_suprasegmental_world_parameters(
    source_f0,
    source_sp,
    source_ap,
    target_f0,
    target_sp,
    target_ap,
):
    """Keep target excitation identity; transfer only source F0/energy motion.

    `source_ap` is accepted only to enforce compatible WORLD analysis shapes;
    its values never enter the output. No tunable interpolation coefficient is
    accepted by design.
    """
    import numpy as np

    source_f0 = np.asarray(source_f0, dtype=np.float64)
    source_sp = np.asarray(source_sp, dtype=np.float64)
    source_ap = np.asarray(source_ap, dtype=np.float64)
    target_f0 = np.asarray(target_f0, dtype=np.float64)
    target_sp = np.asarray(target_sp, dtype=np.float64)
    target_ap = np.asarray(target_ap, dtype=np.float64)
    if source_sp.ndim != 2 or source_ap.ndim != 2 or target_sp.ndim != 2 or target_ap.ndim != 2:
        raise ValueError("WORLD SP/AP tracks must be 2-D")
    if source_sp.shape != source_ap.shape or target_sp.shape != target_ap.shape:
        raise ValueError("WORLD SP/AP shapes differ")
    if source_sp.shape[1] != target_sp.shape[1]:
        raise ValueError("source/target WORLD frequency bins differ")
    if source_sp.shape[0] != source_f0.size or target_sp.shape[0] != target_f0.size:
        raise ValueError("WORLD F0 and spectral frame counts differ")

    frame_count = target_f0.size
    target_voiced = np.isfinite(target_f0) & (target_f0 > 0.0)
    if int(target_voiced.sum()) < 1:
        raise ValueError("target requires voiced F0 frames")
    target_median = _voiced_median(target_f0)

    # Source controls only relative pitch motion. Interpolate through its
    # unvoiced gaps, then recenter the sampled motion on TARGET voiced frames.
    relative_log_f0 = _continuous_source_log_f0_motion(source_f0, frame_count)
    relative_log_f0 -= float(np.median(relative_log_f0[target_voiced]))
    out_f0 = np.zeros(frame_count, dtype=np.float64)
    out_f0[target_voiced] = target_median * np.exp(relative_log_f0[target_voiced])

    # Source controls only relative energy motion. Target spectral-envelope
    # shape is preserved frame-by-frame, with target median amplitude retained.
    eps = np.finfo(np.float64).tiny
    target_log_amp = 0.5 * np.log(np.maximum(np.mean(target_sp, axis=1), eps))
    target_median_log_amp = float(np.median(target_log_amp))
    relative_log_energy = _relative_source_log_energy(source_sp, frame_count)
    relative_log_energy -= float(np.median(relative_log_energy))
    desired_log_amp = target_median_log_amp + relative_log_energy
    amplitude_ratio = np.exp(desired_log_amp - target_log_amp)
    out_sp = target_sp * np.square(amplitude_ratio[:, None])

    # Crucial identity boundary: target aperiodicity is immutable.
    out_ap = target_ap.copy()

    if not np.isfinite(out_f0).all() or not np.isfinite(out_sp).all() or not np.isfinite(out_ap).all():
        raise ValueError("non-finite transferred WORLD parameters")
    return out_f0, out_sp, out_ap


def restore_suprasegmental_with_world(source_wav, target_wav, output_wav) -> SuprasegmentalDiagnostics:
    import math
    import numpy as np
    import pyworld
    import soundfile as sf
    from scipy.signal import resample_poly

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
    out_f0, out_sp, out_ap = transfer_suprasegmental_world_parameters(
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

    return SuprasegmentalDiagnostics(
        source_sample_rate=int(source_sr),
        target_sample_rate=int(target_sr),
        source_seconds=float(len(source) / target_sr),
        target_seconds=float(len(target) / target_sr),
        output_seconds=float(len(output) / target_sr),
        target_voiced_fraction=float(np.mean(target_f0 > 0.0)),
        output_voiced_fraction=float(np.mean(out_f0 > 0.0)),
        target_median_f0=_voiced_median(target_f0),
        output_median_f0=_voiced_median(out_f0),
        target_aperiodicity_preserved=bool(np.array_equal(out_ap, target_ap)),
        peak_normalization_scale=scale,
    )
