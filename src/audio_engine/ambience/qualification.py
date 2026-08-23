import hashlib
import re
import subprocess
from pathlib import Path

from ..audio import ffmpeg_exe


def _slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return value or "ambience-candidate"


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe_audio(path):
    result = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stderr = result.stderr
    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if not duration_match:
        raise ValueError(f"Unable to read audio duration from {path}")
    hours, minutes, seconds = duration_match.groups()
    duration = round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)

    audio_line = next((line for line in stderr.splitlines() if "Audio:" in line), None)
    if not audio_line:
        raise ValueError(f"No audio stream found in {path}")

    codec_match = re.search(r"Audio:\s*([^,\s]+)", audio_line)
    rate_match = re.search(r",\s*(\d+)\s*Hz", audio_line)
    if not codec_match or not rate_match:
        raise ValueError(f"Unable to read audio stream properties from {path}")

    if re.search(r"\bmono\b", audio_line):
        channels = 1
    elif re.search(r"\bstereo\b", audio_line):
        channels = 2
    else:
        layout_match = re.search(r"\b(\d+(?:\.\d+)?)\b", audio_line.split("Hz", 1)[-1])
        channels = None
        if layout_match:
            layout = layout_match.group(1)
            channels = {"5.1": 6, "7.1": 8}.get(layout)

    return {
        "codec": codec_match.group(1),
        "sample_rate_hz": int(rate_match.group(1)),
        "channels": channels,
        "duration_seconds": duration,
    }


def qualify_candidate(
    file_path,
    *,
    candidate_id=None,
    source_provider=None,
    source_page=None,
    source_identifier=None,
    license_id=None,
    attribution=None,
    raw_redistribution="unknown",
    tags=None,
):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise ValueError(f"Ambience candidate is not a file: {path}")
    if raw_redistribution not in {"unknown", "allowed", "embedded-only", "forbidden"}:
        raise ValueError("raw_redistribution must be unknown, allowed, embedded-only, or forbidden")

    audio = _probe_audio(path)
    source_complete = bool(source_provider and source_page)
    license_declared = bool(license_id)

    return {
        "schema_version": 1,
        "status": "candidate",
        "id": candidate_id or _slug(path.stem),
        "file": {
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "content_sha256": _sha256(path),
        },
        "audio": audio,
        "tags": list(tags or []),
        "source": {
            "provider": source_provider,
            "page": source_page,
            "identifier": source_identifier,
            "provenance_complete": source_complete,
        },
        "license": {
            "declared": license_id,
            "verified": False,
            "attribution": attribution,
            "raw_redistribution": raw_redistribution,
        },
        "review": {
            "technical_probe": "passed",
            "listening_quality": "pending",
            "background_suitability": "pending",
            "loopability": "pending",
            "speech_masking": "pending",
        },
        "snapshot": {
            "status": "pending",
            "note": "Choose a durable production snapshot compatible with the asset licence before promotion.",
        },
        "promotion": {
            "eligible": False,
            "required": [
                "licence verification",
                "listening quality review",
                "background suitability review",
                "snapshot strategy",
            ],
            "evidence": {
                "technical_probe": True,
                "provenance_declared": source_complete,
                "license_declared": license_declared,
            },
        },
    }
