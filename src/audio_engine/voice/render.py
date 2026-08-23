import hashlib
import inspect
import json
from pathlib import Path


def _provider_code_sha256(provider):
    digest = hashlib.sha256()
    try:
        source = Path(inspect.getfile(provider.__class__))
        if source.exists():
            digest.update(source.read_bytes())
    except (TypeError, OSError):
        digest.update(provider.__class__.__name__.encode("utf-8"))
    digest.update(Path(__file__).read_bytes())
    return digest.hexdigest()


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


def render_voice_clip(segment, provider, cache_root):
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    fingerprint = voice_fingerprint(segment, provider)
    path = cache_root / f"{fingerprint}.mp3"
    if path.exists() and path.stat().st_size > 0:
        return path, True, fingerprint

    temporary = path.with_suffix(".tmp.mp3")
    temporary.unlink(missing_ok=True)
    provider.synthesize(segment, temporary)
    if not temporary.exists() or temporary.stat().st_size <= 0:
        raise RuntimeError("Voice provider produced no audio")
    temporary.replace(path)
    return path, False, fingerprint
