import hashlib
import json
from pathlib import Path

from ..audio import run_ffmpeg
from ..contract import sha256_file


def _resolve_local_source(program_path, value):
    if "://" in value:
        raise ValueError("ambience.file must be a local file path, not a URL")
    source = (Path(program_path).parent / value).resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Ambience input not found: {source}")
    return source


def _fingerprint(source_sha, config, duration_seconds, sample_rate_hz, channels):
    payload = {
        "source_sha256": source_sha,
        "gain_db": config.get("gain_db", -22),
        "loop": config.get("loop", True),
        "fade_in_ms": config.get("fade_in_ms", 1000),
        "fade_out_ms": config.get("fade_out_ms", 1500),
        "duration_seconds": round(float(duration_seconds), 3),
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def prepare_ambience(config, program_path, cache_root, duration_seconds, sample_rate_hz, channels=2):
    source = _resolve_local_source(program_path, config["file"])
    source_sha = sha256_file(source)
    fingerprint = _fingerprint(source_sha, config, duration_seconds, sample_rate_hz, channels)
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    output = cache_root / f"{fingerprint}.wav"
    if output.exists() and output.stat().st_size > 0:
        return output, True, {
            "file": config["file"],
            "source_sha256": source_sha,
            "fingerprint": fingerprint,
        }

    duration = max(0.001, float(duration_seconds))
    fade_in = max(0.0, min(float(config.get("fade_in_ms", 1000)) / 1000.0, duration))
    fade_out = max(0.0, min(float(config.get("fade_out_ms", 1500)) / 1000.0, duration))
    filters = [f"volume={float(config.get('gain_db', -22))}dB"]
    if fade_in > 0:
        filters.append(f"afade=t=in:st=0:d={fade_in:.3f}")
    if fade_out > 0:
        start = max(0.0, duration - fade_out)
        filters.append(f"afade=t=out:st={start:.3f}:d={fade_out:.3f}")

    args = []
    if config.get("loop", True):
        args.extend(["-stream_loop", "-1"])
    args.extend([
        "-i", str(source),
        "-t", f"{duration:.3f}",
        "-af", ",".join(filters),
        "-ar", str(sample_rate_hz),
        "-ac", str(channels),
        "-c:a", "pcm_s16le",
        str(output),
    ])
    run_ffmpeg(args)
    return output, False, {
        "file": config["file"],
        "source_sha256": source_sha,
        "fingerprint": fingerprint,
    }
