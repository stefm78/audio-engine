import hashlib
import json
import tempfile
from pathlib import Path

from . import __version__
from .audio import encode_concat, probe_duration_seconds, silence_file
from .contract import load_json, sha256_file, validate_assembly
from .profiles import get_profile

def assemble_plan(plan_path, output_root):
    plan_path = Path(plan_path)
    plan = validate_assembly(load_json(plan_path))
    profile_name = plan.get("profile", "speech")
    profile = get_profile(profile_name)
    output_dir = Path(output_root) / plan["id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "audio.mp3"

    input_evidence = []
    with tempfile.TemporaryDirectory() as temp_value:
        temp_dir = Path(temp_value)
        parts = []
        silence_cache = {}
        for item in plan["inputs"]:
            source = (plan_path.parent / item["file"]).resolve()
            if not source.exists():
                raise FileNotFoundError(f"Assembly input not found: {source}")
            duration = probe_duration_seconds(source)
            if duration is None or duration <= 0:
                raise RuntimeError(f"Assembly input has no measurable audio duration: {source}")
            input_evidence.append({
                "file": item["file"],
                "sha256": sha256_file(source),
                "duration_seconds": duration,
                "pause_after_ms": int(item.get("pause_after_ms", 0)),
            })
            parts.append(source)
            pause = silence_file(temp_dir, item.get("pause_after_ms", 0), silence_cache)
            if pause:
                parts.append(pause)
        peak_guard = encode_concat(parts, audio_path, profile)

    engine_code_sha = sha256_file(Path(__file__))
    fingerprint_payload = {
        "source_sha256": sha256_file(plan_path),
        "engine_code_sha256": engine_code_sha,
        "engine_version": __version__,
        "profile": profile_name,
        "inputs": input_evidence,
    }
    render_fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    manifest = {
        "schema_version": 1,
        "id": plan["id"],
        "status": "success",
        "source_sha256": sha256_file(plan_path),
        "engine_code_sha256": engine_code_sha,
        "render_fingerprint": render_fingerprint,
        "engine_version": __version__,
        "profile": profile_name,
        "audio": {
            "file": "audio.mp3",
            "codec": "mp3",
            "bitrate_kbps": profile["bitrate_kbps"],
            "sample_rate_hz": profile["sample_rate_hz"],
            "channels": profile["channels"],
            "duration_seconds": probe_duration_seconds(audio_path),
        },
        "inputs": plan["inputs"],
        "assembly": {
            "input_count": len(input_evidence),
            "inputs": input_evidence,
            "encoding_peak_guard": peak_guard,
        },
        "warnings": [],
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
