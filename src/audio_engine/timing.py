import json
import re
from pathlib import Path
from statistics import median

from .contract import load_json, validate_program
from .providers.edge import EdgeProvider
from .voice.render import cached_voice_timing
from .voices import load_voice_config, resolve_segments

_RATE_RE = re.compile(r"^([+-]?\d+(?:\.\d+)?)%$")
_GENERIC_MS_PER_WORD = 400.0


def _rate_factor(value):
    match = _RATE_RE.match(str(value or "+0%"))
    if not match:
        return 1.0
    return max(0.5, min(2.0, 1.0 + (float(match.group(1)) / 100.0)))


def _load_samples(cache_root):
    samples = []
    cache_root = Path(cache_root)
    if not cache_root.exists():
        return samples
    for path in cache_root.glob("*.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        words = item.get("text_words")
        duration = item.get("measured_duration_ms")
        voice = item.get("voice")
        if not voice or not isinstance(words, int) or words <= 0 or not isinstance(duration, (int, float)) or duration <= 0:
            continue
        samples.append(item)
    return samples


def _estimate_from_samples(segment, samples):
    voice = segment["voice"]
    rate = segment.get("rate", "+0%")
    words = max(1, len(segment.get("text", "").split()))

    same_voice_rate = [
        item["measured_duration_ms"] / item["text_words"]
        for item in samples
        if item.get("voice") == voice and item.get("rate") == rate
    ]
    if same_voice_rate:
        return words * median(same_voice_rate), "voice-rate-history", len(same_voice_rate)

    same_voice = [
        (item["measured_duration_ms"] / item["text_words"]) * _rate_factor(item.get("rate"))
        for item in samples
        if item.get("voice") == voice
    ]
    if same_voice:
        base = median(same_voice)
        return (words * base) / _rate_factor(rate), "voice-history", len(same_voice)

    return (words * _GENERIC_MS_PER_WORD) / _rate_factor(rate), "generic-rate-adjusted", 0


def timing_report(program_path, output_root="output", voices_path=None, provider=None):
    program = validate_program(load_json(program_path))
    voice_config, _ = load_voice_config(voices_path)
    resolved = resolve_segments(program, voice_config)
    provider = provider or EdgeProvider()
    cache_root = Path(output_root) / ".cache" / "voices"
    samples = _load_samples(cache_root)

    report = []
    exact_count = 0
    for segment in resolved:
        exact = cached_voice_timing(segment, provider, cache_root)
        if exact:
            duration_ms = float(exact["measured_duration_ms"])
            source = "measured-cache"
            sample_count = 1
            exact_count += 1
        else:
            duration_ms, source, sample_count = _estimate_from_samples(segment, samples)
        report.append({
            "sequence": segment["sequence"],
            "voice": segment["voice"],
            "preset": segment.get("resolved_preset"),
            "rate": segment.get("rate", "+0%"),
            "words": len(segment.get("text", "").split()),
            "duration_ms": round(duration_ms, 1),
            "timing_source": source,
            "calibration_samples": sample_count,
        })

    return {
        "program_id": program["id"],
        "segments": report,
        "exact_segments": exact_count,
        "estimated_segments": len(report) - exact_count,
        "total_speech_ms": round(sum(item["duration_ms"] for item in report), 1),
        "authority": "measured audio when cached; estimates are design guidance only",
    }
