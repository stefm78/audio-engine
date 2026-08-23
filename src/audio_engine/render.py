import hashlib
import json
import tempfile
from pathlib import Path

from . import __version__
from .ambience.prepare import ambience_source_sha256, prepare_ambience
from .audio import probe_duration_seconds
from .contract import load_json, sha256_file, validate_program
from .mix.render import render_master, render_speech_track, stereo_required
from .profiles import get_profile
from .providers.edge import EdgeProvider
from .sound.render import render_soundscape, soundscape_source_sha256
from .voice.render import render_voice_clip
from .voices import load_voice_config, resolve_segments


def engine_code_sha256():
    root = Path(__file__).parent
    files = [
        root / "render.py",
        root / "audio.py",
        root / "contract.py",
        root / "profiles.py",
        root / "voices.py",
        root / "providers" / "edge.py",
        root / "voice" / "render.py",
        root / "ambience" / "prepare.py",
        root / "sound" / "catalog.py",
        root / "sound" / "render.py",
        root / "mix" / "render.py",
    ]
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def render_fingerprint(
    source_sha,
    voice_config_sha,
    engine_code_sha,
    provider_name,
    profile_name,
    ambience_source_sha=None,
    soundscape_source_sha=None,
):
    payload = {
        "source_sha256": source_sha,
        "voice_config_sha256": voice_config_sha,
        "engine_code_sha256": engine_code_sha,
        "provider": provider_name,
        "profile": profile_name,
        "ambience_source_sha256": ambience_source_sha,
        "soundscape_source_sha256": soundscape_source_sha,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def cached_manifest(output_dir, expected_fingerprint):
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if manifest.get("render_fingerprint") != expected_fingerprint:
        return None
    audio_file = manifest.get("audio", {}).get("file")
    transcript_file = manifest.get("transcript")
    if not audio_file or not (output_dir / audio_file).exists():
        return None
    if not transcript_file or not (output_dir / transcript_file).exists():
        return None
    if manifest.get("status") != "success":
        return None
    return manifest


def render_program(program_path, output_root, voices_path=None, provider=None, sounds_path=None):
    program_path = Path(program_path)
    program = validate_program(load_json(program_path))
    profile_name = program.get("profile", "speech")
    needs_stereo = stereo_required(program)
    profile = get_profile(profile_name, stereo=needs_stereo)
    voice_config, voice_config_path = load_voice_config(voices_path)
    provider = provider or EdgeProvider()

    source_sha = sha256_file(program_path)
    voice_config_sha = sha256_file(voice_config_path)
    engine_sha = engine_code_sha256()
    ambience_sha = None
    soundscape_sha = None
    if program.get("ambience"):
        ambience_sha = ambience_source_sha256(program["ambience"], program_path)
    if program.get("soundscape"):
        soundscape_sha = soundscape_source_sha256(
            program["soundscape"], program_path, sounds_path
        )
    fingerprint = render_fingerprint(
        source_sha,
        voice_config_sha,
        engine_sha,
        provider.name,
        profile_name,
        ambience_sha,
        soundscape_sha,
    )

    output_root = Path(output_root)
    output_dir = output_root / program["id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    cached = cached_manifest(output_dir, fingerprint)
    if cached:
        return {**cached, "cache_hit": True}

    resolved = resolve_segments(program, voice_config)
    voice_cache_root = output_root / ".cache" / "voices"
    voice_clips = []
    voice_cache_hits = 0
    voice_fingerprints = []
    for segment in resolved:
        clip, cache_hit, voice_fingerprint = render_voice_clip(
            segment,
            provider,
            voice_cache_root,
        )
        voice_clips.append(clip)
        voice_fingerprints.append(voice_fingerprint)
        if cache_hit:
            voice_cache_hits += 1

    audio_path = output_dir / "audio.mp3"
    ambience_manifest = None
    ambience_cache_hit = None
    soundscape_manifest = None
    soundscape_cache_hit = None

    with tempfile.TemporaryDirectory() as temp_value:
        temp_dir = Path(temp_value)
        speech_path = render_speech_track(
            program,
            resolved,
            voice_clips,
            temp_dir,
            profile,
        )
        duration = probe_duration_seconds(speech_path)
        if duration is None:
            raise RuntimeError("Could not determine rendered speech duration")

        environment_path = None
        ducking = "speech"
        if program.get("ambience"):
            environment_path, ambience_cache_hit, ambience_manifest = prepare_ambience(
                program["ambience"],
                program_path,
                output_root / ".cache" / "ambience",
                duration,
                profile["sample_rate_hz"],
                channels=2,
            )
            ducking = program["ambience"].get("ducking", "speech")
        elif program.get("soundscape"):
            environment_path, soundscape_cache_hit, soundscape_manifest = render_soundscape(
                program["soundscape"],
                program_path,
                output_root / ".cache" / "soundscapes",
                duration,
                profile["sample_rate_hz"],
                sounds_path=sounds_path,
                channels=2,
            )
            ducking = program["soundscape"].get("ducking", "speech")

        render_master(
            speech_path,
            audio_path,
            profile,
            ambience_path=environment_path,
            ducking=ducking,
        )

    transcript = {
        "schema_version": 1,
        "program_schema_version": program["schema_version"],
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

    mix_ducking = None
    if program.get("ambience"):
        mix_ducking = program["ambience"].get("ducking", "speech")
    elif program.get("soundscape"):
        mix_ducking = program["soundscape"].get("ducking", "speech")

    manifest = {
        "schema_version": 1,
        "program_schema_version": program["schema_version"],
        "id": program["id"],
        "status": "success",
        "source_sha256": source_sha,
        "voice_config_sha256": voice_config_sha,
        "engine_code_sha256": engine_sha,
        "render_fingerprint": fingerprint,
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
        "mix": {
            "stereo": needs_stereo,
            "voice_clip_count": len(resolved),
            "voice_cache_hits": voice_cache_hits,
            "voice_fingerprints": voice_fingerprints,
            "ambience": ambience_manifest,
            "ambience_cache_hit": ambience_cache_hit,
            "soundscape": soundscape_manifest,
            "soundscape_cache_hit": soundscape_cache_hit,
            "ducking": mix_ducking,
        },
        "transcript": "transcript.json",
        "warnings": [],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {**manifest, "cache_hit": False}
