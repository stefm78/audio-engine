import hashlib
import inspect
import json
import shutil
from pathlib import Path

from ..audio import probe_duration_seconds

_SYNTHESIS_CONTRACT = "voice-synthesis-v1"


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


def _timing_metadata(segment, provider, fingerprint, path):
    duration = probe_duration_seconds(path)
    if duration is None:
        raise RuntimeError("Could not determine rendered voice duration")
    text = segment.get("text", "")
    return {
        "version": 1,
        "fingerprint": fingerprint,
        "provider": provider.name,
        "voice": segment["voice"],
        "rate": segment.get("rate", "+0%"),
        "pitch": segment.get("pitch", "+0Hz"),
        "volume": segment.get("volume", "+0%"),
        "text_chars": len(text),
        "text_words": len(text.split()),
        "measured_duration_ms": round(duration * 1000.0, 3),
    }


def _ensure_timing_metadata(segment, provider, fingerprint, path):
    metadata_path = _metadata_path(path)
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            if data.get("fingerprint") == fingerprint and data.get("measured_duration_ms"):
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
            shutil.copyfile(legacy, path)
            _ensure_timing_metadata(segment, provider, fingerprint, path)
            return path, True, fingerprint

    temporary = path.with_suffix(".tmp.mp3")
    temporary.unlink(missing_ok=True)
    provider.synthesize(segment, temporary)
    if not temporary.exists() or temporary.stat().st_size <= 0:
        raise RuntimeError("Voice provider produced no audio")
    temporary.replace(path)
    _ensure_timing_metadata(segment, provider, fingerprint, path)
    return path, False, fingerprint
