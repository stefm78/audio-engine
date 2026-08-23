import hashlib
import json
from pathlib import Path

from .effects import acoustic_space_ids

SUPPORTED_SCHEMA_VERSIONS = (1, 2, 3, 4, 5)
PLACEMENTS = ("left", "center", "right")
DUCKING_MODES = ("speech", "off")
EVENT_ROLES_V4 = ("punctuation", "scene")
EVENT_ROLES_V5 = ("punctuation", "scene", "bridge")
MAX_SOUND_LAYERS = 2
MAX_SOUND_EVENTS = 16
MIN_SCENE_SPACE_MS = 750
MAX_SCENE_SPACE_MS = 15000
MIN_BRIDGE_FOREGROUND_MS = 1000
MAX_BRIDGE_FOREGROUND_MS = 10000
MIN_BRIDGE_CARRY_MS = 250
MAX_BRIDGE_CARRY_MS = 10000


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
    return isinstance(value, str) and bool(value.strip())


def _validate_position(value, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    if "pan" in value:
        errors.append(f"{label}.pan is not a public contract field; use placement")
    if "placement" in value and value["placement"] not in PLACEMENTS:
        errors.append(f"{label}.placement must be one of {', '.join(PLACEMENTS)}")


def _validate_acoustic_space(value, label, errors):
    if value not in acoustic_space_ids():
        errors.append(f"{label} must be one of {', '.join(acoustic_space_ids())}")


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


def _validate_non_negative_ms(value, label, errors):
    if not isinstance(value, (int, float)) or value < 0:
        errors.append(f"{label} must be >= 0")


def _validate_ambience(ambience, errors):
    if not isinstance(ambience, dict):
        errors.append("ambience must be an object")
        return
    _validate_local_file(ambience.get("file"), "ambience.file", errors)
    _validate_gain(ambience.get("gain_db", -22), "ambience.gain_db", errors)
    if not isinstance(ambience.get("loop", True), bool):
        errors.append("ambience.loop must be boolean")
    for name, default in (("fade_in_ms", 1000), ("fade_out_ms", 1500)):
        _validate_non_negative_ms(ambience.get(name, default), f"ambience.{name}", errors)
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
        _validate_non_negative_ms(item.get(name, default), f"{label}.{name}", errors)


def _validate_segment_reference(value, label, segment_count, errors, require_next=False):
    upper = segment_count - 1 if require_next else segment_count
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= upper:
        suffix = " with a following segment" if require_next else ""
        errors.append(f"{label} must reference an existing segment{suffix} (1..{upper})")


def _validate_event(item, label, errors, version, segment_count):
    if not _validate_sound_ref(item, label, errors):
        return
    _validate_gain(item.get("gain_db", -18), f"{label}.gain_db", errors)
    placement = item.get("placement", "center")
    if placement not in PLACEMENTS:
        errors.append(f"{label}.placement must be one of {', '.join(PLACEMENTS)}")

    v4_fields = {"role", "after_segment", "space_ms", "fade_in_ms", "fade_out_ms"}
    v5_fields = {"foreground_ms", "carry_under_speech_ms"}
    if version < 4:
        used = sorted((v4_fields | v5_fields) & set(item))
        if used:
            errors.append(f"{label} fields {', '.join(used)} require schema_version 4 or 5")
        at_ms = item.get("at_ms")
        if not isinstance(at_ms, (int, float)) or at_ms < 0:
            errors.append(f"{label}.at_ms must be >= 0")
        return

    if version == 4:
        used = sorted(v5_fields & set(item))
        if used:
            errors.append(f"{label} fields {', '.join(used)} require schema_version 5")
        allowed_roles = EVENT_ROLES_V4
    else:
        allowed_roles = EVENT_ROLES_V5

    role = item.get("role", "punctuation")
    if role not in allowed_roles:
        errors.append(f"{label}.role must be one of {', '.join(allowed_roles)}")
        return

    default_fade_out = 250 if role == "punctuation" else (1200 if role == "bridge" else 500)
    default_fade_in = 0 if role == "punctuation" else (500 if role == "bridge" else 180)
    for name, default in (("fade_in_ms", default_fade_in), ("fade_out_ms", default_fade_out)):
        _validate_non_negative_ms(item.get(name, default), f"{label}.{name}", errors)

    if role == "scene":
        if "at_ms" in item:
            errors.append(f"{label}.scene must use after_segment, not at_ms")
        if "foreground_ms" in item or "carry_under_speech_ms" in item:
            errors.append(f"{label}.scene uses space_ms; foreground/carry are reserved for bridge")
        _validate_segment_reference(item.get("after_segment"), f"{label}.after_segment", segment_count, errors)
        space_ms = item.get("space_ms")
        if not isinstance(space_ms, (int, float)) or not MIN_SCENE_SPACE_MS <= space_ms <= MAX_SCENE_SPACE_MS:
            errors.append(
                f"{label}.space_ms must be between {MIN_SCENE_SPACE_MS} and {MAX_SCENE_SPACE_MS}"
            )
    elif role == "bridge":
        if "at_ms" in item or "space_ms" in item:
            errors.append(f"{label}.bridge uses after_segment + foreground_ms + carry_under_speech_ms")
        _validate_segment_reference(
            item.get("after_segment"),
            f"{label}.after_segment",
            segment_count,
            errors,
            require_next=True,
        )
        foreground_ms = item.get("foreground_ms")
        if not isinstance(foreground_ms, (int, float)) or not MIN_BRIDGE_FOREGROUND_MS <= foreground_ms <= MAX_BRIDGE_FOREGROUND_MS:
            errors.append(
                f"{label}.foreground_ms must be between {MIN_BRIDGE_FOREGROUND_MS} and {MAX_BRIDGE_FOREGROUND_MS}"
            )
        carry_ms = item.get("carry_under_speech_ms")
        if not isinstance(carry_ms, (int, float)) or not MIN_BRIDGE_CARRY_MS <= carry_ms <= MAX_BRIDGE_CARRY_MS:
            errors.append(
                f"{label}.carry_under_speech_ms must be between {MIN_BRIDGE_CARRY_MS} and {MAX_BRIDGE_CARRY_MS}"
            )
    else:
        if "after_segment" in item or "space_ms" in item or "foreground_ms" in item or "carry_under_speech_ms" in item:
            errors.append(f"{label}.punctuation uses at_ms; anchored narrative fields are reserved for scene/bridge")
        at_ms = item.get("at_ms")
        if not isinstance(at_ms, (int, float)) or at_ms < 0:
            errors.append(f"{label}.at_ms must be >= 0")


def _validate_soundscape(soundscape, errors, version, segment_count):
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
            _validate_event(item, f"soundscape.events[{index}]", errors, version, segment_count)


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

    if "acoustic_space" in program:
        if version not in (4, 5):
            errors.append("acoustic_space requires schema_version 4 or 5")
        else:
            _validate_acoustic_space(program["acoustic_space"], "acoustic_space", errors)

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
            if isinstance(actor, dict) and "acoustic_space" in actor:
                if version not in (4, 5):
                    errors.append(f"actors.{actor_id}.acoustic_space requires schema_version 4 or 5")
                else:
                    _validate_acoustic_space(actor["acoustic_space"], f"actors.{actor_id}.acoustic_space", errors)

    segments = program.get("segments")
    segment_count = len(segments) if isinstance(segments, list) else 0
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
            if "acoustic_space" in segment:
                if version not in (4, 5):
                    errors.append(f"segments[{index}].acoustic_space requires schema_version 4 or 5")
                else:
                    _validate_acoustic_space(segment["acoustic_space"], f"segments[{index}].acoustic_space", errors)

    uses_v2 = bool(program.get("ambience") or program.get("actors")) or any(
        isinstance(segment, dict) and ("placement" in segment or "pan" in segment)
        for segment in (segments or [])
    )
    uses_v3 = "soundscape" in program
    if version == 1 and uses_v2:
        errors.append("actors, placement, and ambience require schema_version 2, 3, 4, or 5")
    if version in (1, 2) and uses_v3:
        errors.append("soundscape requires schema_version 3, 4, or 5")
    if "ambience" in program and "soundscape" in program:
        errors.append("use ambience or soundscape, not both")
    if version in (2, 3, 4, 5) and "ambience" in program:
        _validate_ambience(program["ambience"], errors)
    if version in (3, 4, 5) and "soundscape" in program:
        _validate_soundscape(program["soundscape"], errors, version, segment_count)

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
