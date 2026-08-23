import hashlib
import json
from pathlib import Path

SUPPORTED_SCHEMA_VERSIONS = (1, 2, 3)
PLACEMENTS = ("left", "center", "right")
DUCKING_MODES = ("speech", "off")
MAX_SOUND_LAYERS = 2
MAX_SOUND_EVENTS = 16


class ContractError(ValueError):
    pass


def load_json(path):
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ContractError(f"{path}: invalid JSON ({exc})") from exc


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _non_empty_string(value):
    return isinstance(value, str) and value.strip()


def _validate_position(value, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    if "pan" in value:
        errors.append(f"{label}.pan is not a public contract field; use placement")
    if "placement" in value and value["placement"] not in PLACEMENTS:
        errors.append(f"{label}.placement must be one of {', '.join(PLACEMENTS)}")


def _validate_local_file(value, label, errors):
    if not _non_empty_string(value):
        errors.append(f"{label} is required")
        return
    if "://" in value:
        errors.append(f"{label} must be a local relative path, not a URL")
    if Path(value).is_absolute():
        errors.append(f"{label} must be relative")


def _validate_gain(value, label, errors):
    if not isinstance(value, (int, float)) or not -60 <= value <= 6:
        errors.append(f"{label} must be between -60 and 6")


def _validate_ambience(ambience, errors):
    if not isinstance(ambience, dict):
        errors.append("ambience must be an object")
        return
    _validate_local_file(ambience.get("file"), "ambience.file", errors)
    _validate_gain(ambience.get("gain_db", -22), "ambience.gain_db", errors)
    if not isinstance(ambience.get("loop", True), bool):
        errors.append("ambience.loop must be boolean")
    for name, default in (("fade_in_ms", 1000), ("fade_out_ms", 1500)):
        value = ambience.get(name, default)
        if not isinstance(value, (int, float)) or value < 0:
            errors.append(f"ambience.{name} must be >= 0")
    if ambience.get("ducking", "speech") not in DUCKING_MODES:
        errors.append(f"ambience.ducking must be one of {', '.join(DUCKING_MODES)}")


def _validate_sound_ref(item, label, errors):
    if not isinstance(item, dict):
        errors.append(f"{label} must be an object")
        return False
    has_sound = _non_empty_string(item.get("sound"))
    has_file = _non_empty_string(item.get("file"))
    if has_sound == has_file:
        errors.append(f"{label} needs exactly one of sound or file")
    if has_file:
        _validate_local_file(item.get("file"), f"{label}.file", errors)
    return True


def _validate_continuous_sound(item, label, default_gain, errors):
    if not _validate_sound_ref(item, label, errors):
        return
    _validate_gain(item.get("gain_db", default_gain), f"{label}.gain_db", errors)
    if not isinstance(item.get("loop", True), bool):
        errors.append(f"{label}.loop must be boolean")
    for name, default in (("fade_in_ms", 1000), ("fade_out_ms", 1500)):
        value = item.get(name, default)
        if not isinstance(value, (int, float)) or value < 0:
            errors.append(f"{label}.{name} must be >= 0")


def _validate_event(item, label, errors):
    if not _validate_sound_ref(item, label, errors):
        return
    _validate_gain(item.get("gain_db", -18), f"{label}.gain_db", errors)
    at_ms = item.get("at_ms")
    if not isinstance(at_ms, (int, float)) or at_ms < 0:
        errors.append(f"{label}.at_ms must be >= 0")
    placement = item.get("placement", "center")
    if placement not in PLACEMENTS:
        errors.append(f"{label}.placement must be one of {', '.join(PLACEMENTS)}")


def _validate_soundscape(soundscape, errors):
    if not isinstance(soundscape, dict):
        errors.append("soundscape must be an object")
        return
    if soundscape.get("ducking", "speech") not in DUCKING_MODES:
        errors.append(f"soundscape.ducking must be one of {', '.join(DUCKING_MODES)}")
    bed = soundscape.get("bed")
    layers = soundscape.get("layers", [])
    events = soundscape.get("events", [])
    if bed is None and not layers and not events:
        errors.append("soundscape needs bed, layers, or events")
    if bed is not None:
        _validate_continuous_sound(bed, "soundscape.bed", -22, errors)
    if not isinstance(layers, list):
        errors.append("soundscape.layers must be an array")
    else:
        if len(layers) > MAX_SOUND_LAYERS:
            errors.append(f"soundscape.layers supports at most {MAX_SOUND_LAYERS} items")
        for index, item in enumerate(layers, start=1):
            _validate_continuous_sound(item, f"soundscape.layers[{index}]", -28, errors)
    if not isinstance(events, list):
        errors.append("soundscape.events must be an array")
    else:
        if len(events) > MAX_SOUND_EVENTS:
            errors.append(f"soundscape.events supports at most {MAX_SOUND_EVENTS} items")
        for index, item in enumerate(events, start=1):
            _validate_event(item, f"soundscape.events[{index}]", errors)


def validate_program(program):
    errors = []
    version = program.get("schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append(f"schema_version must be one of {', '.join(map(str, SUPPORTED_SCHEMA_VERSIONS))}")
    if not _non_empty_string(program.get("id")):
        errors.append("id is required")
    if not _non_empty_string(program.get("title")):
        errors.append("title is required")
    if not _non_empty_string(program.get("profile", "speech")):
        errors.append("profile must be a non-empty string")

    actors = program.get("actors", {})
    if actors and not isinstance(actors, dict):
        errors.append("actors must be an object keyed by character_id")
        actors = {}
    elif isinstance(actors, dict):
        for actor_id, actor in actors.items():
            if not _non_empty_string(actor_id):
                errors.append("actor ids must be non-empty strings")
                continue
            _validate_position(actor, f"actors.{actor_id}", errors)

    segments = program.get("segments")
    if not isinstance(segments, list) or not segments:
        errors.append("segments must be a non-empty array")
    else:
        for index, segment in enumerate(segments, start=1):
            if not isinstance(segment, dict):
                errors.append(f"segments[{index}] must be an object")
                continue
            if not _non_empty_string(segment.get("text")):
                errors.append(f"segments[{index}].text is required")
            if not (segment.get("voice") or segment.get("preset") or segment.get("target")):
                errors.append(f"segments[{index}] needs voice, preset, or target")
            pause = segment.get("pause_after_ms", 350)
            if not isinstance(pause, (int, float)) or pause < 0:
                errors.append(f"segments[{index}].pause_after_ms must be >= 0")
            if "placement" in segment or "pan" in segment:
                _validate_position(segment, f"segments[{index}]", errors)

    uses_v2 = bool(program.get("ambience") or program.get("actors")) or any(
        isinstance(segment, dict) and ("placement" in segment or "pan" in segment)
        for segment in (segments or [])
    )
    uses_v3 = "soundscape" in program
    if version == 1 and uses_v2:
        errors.append("actors, placement, and ambience require schema_version 2 or 3")
    if version in (1, 2) and uses_v3:
        errors.append("soundscape requires schema_version 3")
    if "ambience" in program and "soundscape" in program:
        errors.append("use ambience or soundscape, not both")
    if version in (2, 3) and "ambience" in program:
        _validate_ambience(program["ambience"], errors)
    if version == 3 and "soundscape" in program:
        _validate_soundscape(program["soundscape"], errors)

    if errors:
        raise ContractError("; ".join(errors))
    return program


def validate_assembly(plan):
    errors = []
    if plan.get("schema_version") != 1:
        errors.append("assembly schema_version must be 1")
    if not _non_empty_string(plan.get("id")):
        errors.append("id is required")
    inputs = plan.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        errors.append("inputs must be a non-empty array")
    else:
        for index, item in enumerate(inputs, start=1):
            if not isinstance(item, dict) or not _non_empty_string(item.get("file")):
                errors.append(f"inputs[{index}].file is required")
    if errors:
        raise ContractError("; ".join(errors))
    return plan
