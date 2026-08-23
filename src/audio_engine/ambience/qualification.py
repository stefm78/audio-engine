import hashlib
import re
import subprocess
from pathlib import Path

from ..audio import ffmpeg_exe
from ..sound.source_policy import assess_source_license


PREVIEW_BITRATE_KBPS = 160
PREVIEW_SAMPLE_RATE_HZ = 44100


def _slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return value or "sound-candidate"


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
        channels = {"5.1": 6, "7.1": 8}.get(layout_match.group(1)) if layout_match else None
    return {
        "codec": codec_match.group(1),
        "sample_rate_hz": int(rate_match.group(1)),
        "channels": channels,
        "duration_seconds": duration,
    }


def _make_listening_preview(path, preview_dir=None):
    source = Path(path)
    destination_dir = Path(preview_dir) if preview_dir else source.parent
    destination_dir.mkdir(parents=True, exist_ok=True)
    preview = destination_dir / f"{source.stem}.preview.mp3"
    result = subprocess.run(
        [
            ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source), "-vn", "-c:a", "libmp3lame",
            "-b:a", f"{PREVIEW_BITRATE_KBPS}k", "-ar", str(PREVIEW_SAMPLE_RATE_HZ), str(preview),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 or not preview.exists():
        detail = result.stderr.strip() or "unknown ffmpeg error"
        raise ValueError(f"Unable to create audit preview for {source}: {detail}")
    preview_audio = _probe_audio(preview)
    return {
        "purpose": "audit-only",
        "canonical": False,
        "path": str(preview),
        "name": preview.name,
        "format": "mp3",
        "bitrate_kbps": PREVIEW_BITRATE_KBPS,
        "sample_rate_hz": preview_audio["sample_rate_hz"],
        "channels": preview_audio["channels"],
        "duration_seconds": preview_audio["duration_seconds"],
        "size_bytes": preview.stat().st_size,
        "content_sha256": _sha256(preview),
        "note": "Universal audit derivative; never use this hash as the production asset identity.",
    }


def _automated_quality(audio, candidate_type):
    duration = float(audio.get("duration_seconds") or 0)
    rate = int(audio.get("sample_rate_hz") or 0)
    channels = audio.get("channels")
    reasons = []
    passed = True
    if rate < 22050:
        passed = False
        reasons.append("sample-rate-too-low")
    if channels not in {1, 2}:
        passed = False
        reasons.append("unsupported-channel-layout")
    if candidate_type == "ambience" and duration < 20:
        passed = False
        reasons.append("ambience-too-short")
    if candidate_type == "event" and (duration <= 0 or duration > 120):
        passed = False
        reasons.append("event-duration-out-of-policy")
    return {"status": "passed" if passed else "failed", "reasons": reasons}


def qualify_candidate(
    file_path,
    *,
    candidate_id=None,
    candidate_type="ambience",
    source_provider=None,
    source_page=None,
    source_identifier=None,
    license_id=None,
    attribution=None,
    raw_redistribution="unknown",
    tags=None,
    preview_dir=None,
    source_metadata_verified=False,
):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise ValueError(f"Sound candidate is not a file: {path}")
    if candidate_type not in {"ambience", "event"}:
        raise ValueError("candidate_type must be ambience or event")
    if raw_redistribution not in {"unknown", "allowed", "embedded-only", "forbidden"}:
        raise ValueError("raw_redistribution must be unknown, allowed, embedded-only, or forbidden")

    audio = _probe_audio(path)
    canonical_sha256 = _sha256(path)
    preview = _make_listening_preview(path, preview_dir)
    source_complete = bool(source_provider and source_page)
    licence = assess_source_license(
        source_provider,
        source_page,
        license_id,
        machine_observed=bool(source_metadata_verified),
    )
    quality = _automated_quality(audio, candidate_type)
    effective_redistribution = raw_redistribution
    if effective_redistribution == "unknown" and licence.get("policy_raw_redistribution"):
        effective_redistribution = licence["policy_raw_redistribution"]

    return {
        "schema_version": 2,
        "status": "candidate",
        "id": candidate_id or _slug(path.stem),
        "type": candidate_type,
        "file": {
            "name": path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "content_sha256": canonical_sha256,
            "canonical": True,
        },
        "preview": preview,
        "audio": audio,
        "tags": list(tags or []),
        "source": {
            "provider": licence.get("provider") or source_provider,
            "page": source_page,
            "identifier": source_identifier,
            "provenance_complete": source_complete,
            "provider_known": licence.get("provider_known", False),
            "provider_verified": licence.get("provider_verified", False),
            "metadata_machine_observed": bool(source_metadata_verified),
        },
        "license": {
            "id": license_id,
            "declared": license_id,
            "verified": licence.get("verified", False),
            "verification_method": licence.get("verification_method"),
            "attribution": attribution,
            "raw_redistribution": effective_redistribution,
        },
        "review": {
            "technical_probe": "passed",
            "audit_preview": "generated",
            "automated_quality": quality["status"],
            "automated_quality_reasons": quality["reasons"],
        },
        "snapshot": {
            "status": "pending",
            "note": "Durable materialization is automated by the consumer/storage workflow after selection.",
        },
        "promotion": {
            "eligible": bool(licence.get("verified") and quality["status"] == "passed"),
            "decision_mode": "automatic",
            "required": ["autonomous selection", "durable snapshot materialization"],
            "evidence": {
                "technical_probe": True,
                "audit_preview_generated": True,
                "provenance_declared": source_complete,
                "source_metadata_machine_observed": bool(source_metadata_verified),
                "license_machine_verified": licence.get("verified", False),
                "automated_quality": quality["status"],
            },
        },
    }
