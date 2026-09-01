import hashlib
import inspect
import json
from pathlib import Path

from ..audio import probe_duration_seconds, run_ffmpeg

_SYNTHESIS_CONTRACT = "voice-synthesis-v2-edge-silence-normalized"
_EDGE_FILTER = (
    "silenceremove="
    "start_periods=1:start_duration=0.02:start_threshold=-45dB:start_silence=0.06,"
    "areverse,"
    "silenceremove="
    "start_periods=1:start_duration=0.02:start_threshold=-45dB:start_silence=0.10,"
    "areverse"
)


def _provider_code_sha256(provider):
    """Fingerprint synthesis semantics, not cache/timing wrapper code."""
    digest = hashlib.sha256()
    try:
        source = Path(inspect.getfile(provider.__class__))
        if source.exists():
            digest.update(source.read_bytes())
        else:
            digest.update(provider.__class__.__name__.encode("utf-8"))
    except (TypeError, OSError):
        digest.update(provider.__class__.__name__.encode("utf-8"))
    digest.update(_SYNTHESIS_CONTRACT.encode("utf-8"))
    return digest.hexdigest()


def voice_content_key(segment, provider_name):
    """Stable identity used to migrate unchanged clips across engine releases."""
    payload = {
        "provider": provider_name,
        "text": segment["text"],
        "voice": segment["voice"],
        "rate": segment.get("rate", "+0%"),
        "pitch": segment.get("pitch", "+0Hz"),
        "volume": segment.get("volume", "+0%"),
        "provider_parameters": segment.get("provider_parameters"),
        "provider_seed": segment.get("provider_seed"),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def voice_fingerprint(segment, provider):
    payload = {
        "provider": provider.name,
        "provider_code_sha256": _provider_code_sha256(provider),
        "text": segment["text"],
        "voice": segment["voice"],
        "rate": segment.get("rate", "+0%"),
        "pitch": segment.get("pitch", "+0Hz"),
        "volume": segment.get("volume", "+0%"),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _metadata_path(path):
    return Path(path).with_suffix(".json")


def _normalize_voice_edges(source, destination):
    """Remove provider padding at clip edges while preserving internal pauses.

    Edge TTS commonly emits around a second of terminal digital silence. That
    padding is transport noise, not authored cadence: `pause_after_ms` remains
    the only explicit inter-segment pause. Reverse + start-only trimming keeps
    internal hesitations untouched and retains a small safety cushion at both
    clip boundaries.
    """
    source = Path(source)
    destination = Path(destination)
    destination.unlink(missing_ok=True)
    run_ffmpeg([
        "-i", str(source),
        "-af", _EDGE_FILTER,
        "-map_metadata", "-1",
        "-ac", "1",
        "-c:a", "libmp3lame",
        "-b:a", "96k",
        str(destination),
    ])
    duration = probe_duration_seconds(destination)
    if duration is None or duration <= 0.05:
        destination.unlink(missing_ok=True)
        raise RuntimeError("Voice edge normalization produced no usable audio")


def _timing_metadata(segment, provider, fingerprint, path):
    duration = probe_duration_seconds(path)
    if duration is None:
        raise RuntimeError("Could not determine rendered voice duration")
    text = segment.get("text", "")
    return {
        "version": 2,
        "fingerprint": fingerprint,
        "provider": provider.name,
        "voice": segment["voice"],
        "rate": segment.get("rate", "+0%"),
        "pitch": segment.get("pitch", "+0Hz"),
        "volume": segment.get("volume", "+0%"),
        "text_chars": len(text),
        "text_words": len(text.split()),
        "edge_silence_normalized": True,
        "measured_duration_ms": round(duration * 1000.0, 3),
    }


def _ensure_timing_metadata(segment, provider, fingerprint, path):
    metadata_path = _metadata_path(path)
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            if (
                data.get("fingerprint") == fingerprint
                and data.get("measured_duration_ms")
                and data.get("edge_silence_normalized") is True
            ):
                return data
        except Exception:
            pass
    data = _timing_metadata(segment, provider, fingerprint, path)
    metadata_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def cached_voice_timing(segment, provider, cache_root):
    cache_root = Path(cache_root)
    fingerprint = voice_fingerprint(segment, provider)
    path = cache_root / f"{fingerprint}.mp3"
    if not path.exists() or path.stat().st_size <= 0:
        return None
    return _ensure_timing_metadata(segment, provider, fingerprint, path)


def render_voice_clip(segment, provider, cache_root, fallback_fingerprints=None):
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    fingerprint = voice_fingerprint(segment, provider)
    path = cache_root / f"{fingerprint}.mp3"
    if path.exists() and path.stat().st_size > 0:
        _ensure_timing_metadata(segment, provider, fingerprint, path)
        return path, True, fingerprint

    for fallback in fallback_fingerprints or ():
        if not fallback or fallback == fingerprint:
            continue
        legacy = cache_root / f"{fallback}.mp3"
        if legacy.exists() and legacy.stat().st_size > 0:
            _normalize_voice_edges(legacy, path)
            _ensure_timing_metadata(segment, provider, fingerprint, path)
            return path, True, fingerprint

    raw = path.with_suffix(".raw.tmp.mp3")
    normalized = path.with_suffix(".normalized.tmp.mp3")
    raw.unlink(missing_ok=True)
    normalized.unlink(missing_ok=True)
    try:
        provider.synthesize(segment, raw)
        if not raw.exists() or raw.stat().st_size <= 0:
            raise RuntimeError("Voice provider produced no audio")
        _normalize_voice_edges(raw, normalized)
        normalized.replace(path)
    finally:
        raw.unlink(missing_ok=True)
        normalized.unlink(missing_ok=True)
    _ensure_timing_metadata(segment, provider, fingerprint, path)
    return path, False, fingerprint