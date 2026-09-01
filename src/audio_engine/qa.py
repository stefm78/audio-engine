import hashlib
import json
import re
import subprocess
from pathlib import Path

from .audio import ffmpeg_exe, probe_duration_seconds
from .profiles import get_profile

_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_ffmpeg_analysis(path, filter_value):
    completed = subprocess.run(
        [
            ffmpeg_exe(),
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            filter_value,
            "-f",
            "null",
            "-",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "ffmpeg analysis failed")
    return completed.stderr


def _loudness_metrics(path):
    stderr = _run_ffmpeg_analysis(
        path,
        "loudnorm=I=-16:TP=-2.5:LRA=11:print_format=json",
    )
    matches = re.findall(r"\{\s*\"input_i\".*?\}", stderr, flags=re.DOTALL)
    if not matches:
        raise RuntimeError("Could not parse loudnorm metrics")
    data = json.loads(matches[-1])
    return {
        "integrated_lufs": float(data["input_i"]),
        "true_peak_dbtp": float(data["input_tp"]),
        "lra_lu": float(data["input_lra"]),
        "threshold_lufs": float(data["input_thresh"]),
    }


def _silence_metrics(path, duration_seconds, noise_db=-45, minimum_seconds=0.8):
    stderr = _run_ffmpeg_analysis(
        path,
        f"silencedetect=noise={noise_db}dB:d={minimum_seconds}",
    )
    starts = [float(value) for value in re.findall(r"silence_start:\s*([0-9.]+)", stderr)]
    ends = [
        (float(end), float(duration))
        for end, duration in re.findall(
            r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)",
            stderr,
        )
    ]
    intervals = []
    for index, start in enumerate(starts):
        if index < len(ends):
            end, measured = ends[index]
        else:
            end = float(duration_seconds)
            measured = max(0.0, end - start)
        intervals.append({
            "start_seconds": round(start, 3),
            "end_seconds": round(end, 3),
            "duration_seconds": round(measured, 3),
        })
    total = sum(item["duration_seconds"] for item in intervals)
    longest = max((item["duration_seconds"] for item in intervals), default=0.0)
    ratio = (total / duration_seconds) if duration_seconds and duration_seconds > 0 else 0.0
    return {
        "threshold_db": noise_db,
        "minimum_event_seconds": minimum_seconds,
        "interval_count": len(intervals),
        "total_seconds": round(total, 3),
        "longest_seconds": round(longest, 3),
        "ratio": round(ratio, 4),
        "intervals": intervals,
    }


def _check(checks, check_id, passed, summary, evidence=None):
    checks.append({
        "id": check_id,
        "status": "PASS" if passed else "FAIL",
        "summary": summary,
        "evidence": evidence or {},
    })


def _timeline_checks(manifest, transcript, duration_seconds):
    timeline = (manifest.get("mix") or {}).get("timeline")
    segments = transcript.get("segments") or []
    if not timeline:
        return {
            "available": False,
            "valid": manifest.get("program_schema_version", 1) < 4,
            "gaps": [],
            "max_declared_pause_ms": 0.0,
            "summary": "timeline unavailable for pre-v4 program" if manifest.get("program_schema_version", 1) < 4 else "timeline missing",
        }

    gaps = []
    valid = len(timeline) == len(segments)
    max_pause = 0.0
    previous = None
    for sequence in range(1, len(segments) + 1):
        item = timeline.get(str(sequence), timeline.get(sequence))
        if not isinstance(item, dict):
            valid = False
            continue
        start = float(item["start_ms"])
        end = float(item["end_ms"])
        pause = float(item.get("pause_after_ms", 0))
        max_pause = max(max_pause, pause)
        if end < start:
            valid = False
        if previous is not None:
            actual_gap = start - previous["end_ms"]
            expected_gap = previous["pause_after_ms"]
            delta = actual_gap - expected_gap
            if actual_gap < -1.0 or abs(delta) > 150.0:
                valid = False
            gaps.append({
                "after_sequence": sequence - 1,
                "expected_ms": round(expected_gap, 3),
                "actual_ms": round(actual_gap, 3),
                "delta_ms": round(delta, 3),
            })
        previous = {"end_ms": end, "pause_after_ms": pause}

    if previous is not None:
        expected_end = previous["end_ms"] + previous["pause_after_ms"]
        if abs((duration_seconds * 1000.0) - expected_end) > 250.0:
            valid = False

    return {
        "available": True,
        "valid": valid,
        "gaps": gaps,
        "max_declared_pause_ms": round(max_pause, 3),
        "summary": "timeline and declared gaps are coherent" if valid else "timeline/gap inconsistency detected",
    }


def qa_render(render_dir):
    render_dir = Path(render_dir)
    checks = []
    manifest_path = render_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing render manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    audio_name = (manifest.get("audio") or {}).get("file")
    transcript_name = manifest.get("transcript")
    audio_path = render_dir / audio_name if audio_name else None
    transcript_path = render_dir / transcript_name if transcript_name else None

    files_ok = bool(
        audio_path and audio_path.is_file()
        and transcript_path and transcript_path.is_file()
        and manifest.get("status") == "success"
    )
    _check(
        checks,
        "files",
        files_ok,
        "render manifest, audio and transcript are present" if files_ok else "required rendered files are missing",
        {
            "manifest": str(manifest_path),
            "audio": str(audio_path) if audio_path else None,
            "transcript": str(transcript_path) if transcript_path else None,
        },
    )
    if not files_ok:
        report = {
            "schema_version": 1,
            "status": "FAIL",
            "render_id": manifest.get("id"),
            "checks": checks,
        }
        (render_dir / "qa-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report

    transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    duration = probe_duration_seconds(audio_path)
    declared_duration = (manifest.get("audio") or {}).get("duration_seconds")
    duration_ok = (
        isinstance(duration, (int, float))
        and duration > 0.2
        and isinstance(declared_duration, (int, float))
        and abs(float(duration) - float(declared_duration)) <= 0.15
    )
    _check(
        checks,
        "duration",
        duration_ok,
        "measured duration matches manifest" if duration_ok else "duration is missing or differs from manifest",
        {"measured_seconds": duration, "manifest_seconds": declared_duration},
    )

    file_hashes = {
        "audio_sha256": _sha256(audio_path),
        "transcript_sha256": _sha256(transcript_path),
        "manifest_sha256": _sha256(manifest_path),
    }
    _check(
        checks,
        "sha256",
        all(_HASH_RE.fullmatch(value) for value in file_hashes.values()),
        "SHA-256 digests computed for rendered evidence",
        file_hashes,
    )

    segments = transcript.get("segments") or []
    mix = manifest.get("mix") or {}
    clip_count = mix.get("voice_clip_count")
    fingerprints = mix.get("voice_fingerprints") or []
    segment_ok = (
        isinstance(segments, list)
        and len(segments) > 0
        and clip_count == len(segments)
        and len(fingerprints) == len(segments)
        and all(isinstance(value, str) and _HASH_RE.fullmatch(value) for value in fingerprints)
    )
    speakers = sorted({
        str(segment.get("speaker"))
        for segment in segments
        if isinstance(segment, dict) and segment.get("speaker")
    })
    characters = sorted({
        str(segment.get("character_id"))
        for segment in segments
        if isinstance(segment, dict) and segment.get("character_id")
    })
    _check(
        checks,
        "segments",
        segment_ok,
        "segment count and voice fingerprints are coherent" if segment_ok else "segment/fingerprint mismatch",
        {
            "transcript_segments": len(segments),
            "manifest_voice_clip_count": clip_count,
            "voice_fingerprint_count": len(fingerprints),
            "speaker_count": len(speakers),
            "speakers": speakers,
            "character_count": len(characters),
            "characters": characters,
        },
    )

    timeline = _timeline_checks(manifest, transcript, float(duration or 0))
    _check(
        checks,
        "timing",
        timeline["valid"],
        timeline["summary"],
        {
            "available": timeline["available"],
            "max_declared_pause_ms": timeline["max_declared_pause_ms"],
            "gap_count": len(timeline["gaps"]),
            "gaps": timeline["gaps"],
        },
    )

    profile_name = manifest.get("profile", "speech")
    channels = int((manifest.get("audio") or {}).get("channels") or 1)
    profile = get_profile(profile_name, stereo=channels == 2)
    loudness = _loudness_metrics(audio_path)
    clipping_ok = loudness["true_peak_dbtp"] <= -0.1
    _check(
        checks,
        "clipping",
        clipping_ok,
        "no near-zero-dBTP clipping detected" if clipping_ok else "true peak is at or near clipping",
        loudness,
    )

    loudness_delta = abs(loudness["integrated_lufs"] - float(profile["loudness_lufs"]))
    peak_margin = loudness["true_peak_dbtp"] - float(profile["true_peak_db"])
    levels_ok = loudness_delta <= 2.0 and peak_margin <= 1.5
    _check(
        checks,
        "levels",
        levels_ok,
        "spoken-word loudness is within production tolerance" if levels_ok else "loudness or true peak is outside production tolerance",
        {
            **loudness,
            "target_lufs": profile["loudness_lufs"],
            "target_true_peak_dbtp": profile["true_peak_db"],
            "loudness_delta_lu": round(loudness_delta, 3),
            "true_peak_margin_db": round(peak_margin, 3),
        },
    )

    silence = _silence_metrics(audio_path, float(duration or 0))
    allowed_longest = max(3.0, (timeline["max_declared_pause_ms"] / 1000.0) + 1.5)
    silence_ok = silence["longest_seconds"] <= allowed_longest and silence["ratio"] <= 0.55
    _check(
        checks,
        "silence",
        silence_ok,
        "no abnormal long/total silence detected" if silence_ok else "abnormal silence exceeds declared-cadence tolerance",
        {**silence, "allowed_longest_seconds": round(allowed_longest, 3)},
    )

    provenance_fields = {
        "source_sha256": manifest.get("source_sha256"),
        "voice_config_sha256": manifest.get("voice_config_sha256"),
        "engine_code_sha256": manifest.get("engine_code_sha256"),
        "render_fingerprint": manifest.get("render_fingerprint"),
        "engine_version": manifest.get("engine_version"),
        "provider_name": (manifest.get("provider") or {}).get("name"),
    }
    provenance_ok = (
        all(_HASH_RE.fullmatch(str(provenance_fields[key] or "")) for key in (
            "source_sha256",
            "voice_config_sha256",
            "engine_code_sha256",
            "render_fingerprint",
        ))
        and bool(provenance_fields["engine_version"])
        and bool(provenance_fields["provider_name"])
    )
    _check(
        checks,
        "provenance",
        provenance_ok,
        "render is strongly traceable to source, voice config, engine code and provider" if provenance_ok else "required render provenance is incomplete",
        provenance_fields,
    )

    failed = [check["id"] for check in checks if check["status"] != "PASS"]
    report = {
        "schema_version": 1,
        "status": "PASS" if not failed else "FAIL",
        "render_id": manifest.get("id"),
        "failed_checks": failed,
        "reproducibility": {
            "grade": "traceable",
            "bit_exact_rerender_verified": False,
            "note": "QA verifies immutable provenance and rendered evidence; it does not claim bit-exact repeatability from remote synthesis providers.",
        },
        "checks": checks,
    }
    (render_dir / "qa-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report
