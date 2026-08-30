from pathlib import Path

from .ambience.prepare import ambience_source_sha256
from .contract import load_json, validate_program
from .profiles import get_profile
from .sound.render import soundscape_source_sha256
from .voices import load_voice_config, resolve_segments


def preflight_program(program_path, voices_path=None, sounds_path=None):
    """Resolve every cheap, local prerequisite without synthesizing audio.

    This deliberately performs no provider discovery, TTS, Web access or
    rendering. Explicit provider voice names are therefore not checked against
    the provider's live catalog; validated preset ids are resolved locally.
    """
    program_path = Path(program_path)
    program = validate_program(load_json(program_path))

    profile_name = program.get("profile", "speech")
    get_profile(profile_name)

    voice_config, _ = load_voice_config(voices_path)
    resolved = resolve_segments(program, voice_config)

    ambience_sha256 = None
    soundscape_sha256 = None
    if program.get("ambience"):
        ambience_sha256 = ambience_source_sha256(program["ambience"], program_path)
    if program.get("soundscape"):
        soundscape_sha256 = soundscape_source_sha256(
            program["soundscape"],
            program_path,
            sounds_path,
        )

    preset_segments = sum(1 for segment in program["segments"] if segment.get("preset"))
    explicit_voice_segments = sum(1 for segment in program["segments"] if segment.get("voice"))

    return {
        "status": "ready",
        "program_id": program["id"],
        "schema_version": program["schema_version"],
        "profile": profile_name,
        "segment_count": len(resolved),
        "resolved_voice_count": len({segment["voice"] for segment in resolved}),
        "preset_segments": preset_segments,
        "explicit_provider_voice_segments": explicit_voice_segments,
        "provider_voice_availability": "not-network-checked",
        "ambience_resolved": ambience_sha256 is not None,
        "soundscape_resolved": soundscape_sha256 is not None,
        "static_inputs_resolved": True,
        "network_access": False,
        "tts_calls": 0,
    }
