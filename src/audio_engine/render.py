import json
import tempfile
from pathlib import Path

from . import __version__
from .audio import encode_concat, probe_duration_seconds, silence_file
from .contract import load_json, sha256_file, validate_program
from .profiles import get_profile
from .providers.edge import EdgeProvider
from .voices import load_voice_config, resolve_segments

def render_program(program_path, output_root, voices_path=None, provider=None):
    program_path = Path(program_path)
    program = validate_program(load_json(program_path))
    profile_name = program.get("profile", "speech")
    profile = get_profile(profile_name)
    voice_config, voice_config_path = load_voice_config(voices_path)
    resolved = resolve_segments(program, voice_config)
    provider = provider or EdgeProvider()

    output_dir = Path(output_root) / program["id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "audio.mp3"

    with tempfile.TemporaryDirectory() as temp_value:
        temp_dir = Path(temp_value)
        parts = []
        silence_cache = {}
        lead = silence_file(temp_dir, program.get("lead_in_ms", 250), silence_cache)
        if lead:
            parts.append(lead)
        for segment in resolved:
            clip = temp_dir / f"{segment['sequence']:03d}.mp3"
            provider.synthesize(segment, clip)
            parts.append(clip)
            pause = silence_file(
                temp_dir,
                segment.get("pause_after_ms", 350),
                silence_cache,
            )
            if pause:
                parts.append(pause)
        encode_concat(parts, audio_path, profile)

    transcript = {
        "schema_version": 1,
        "id": program["id"],
        "title": program["title"],
        "language": program.get("language"),
        "sources": program.get("sources", []),
        "segments": resolved,
    }
    transcript_path = output_dir / "transcript.json"
    transcript_path.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": 1,
        "id": program["id"],
        "status": "success",
        "source_sha256": sha256_file(program_path),
        "voice_config_sha256": sha256_file(voice_config_path),
        "engine_version": __version__,
        "provider": {
            "name": provider.name,
            "processing": getattr(provider, "processing", "unknown"),
        },
        "profile": profile_name,
        "audio": {
            "file": "audio.mp3",
            "codec": "mp3",
            "bitrate_kbps": profile["bitrate_kbps"],
            "sample_rate_hz": profile["sample_rate_hz"],
            "channels": profile["channels"],
            "duration_seconds": probe_duration_seconds(audio_path),
        },
        "transcript": "transcript.json",
        "warnings": [],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
