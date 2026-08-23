import hashlib
import json
from pathlib import Path

SUPPORTED_SCHEMA_VERSIONS = (1, 2)
PLACEMENTS = ("left", "center", "right")
DUCKING_MODES = ("speech", "off")


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
    if "placement" in value and "pan" in value:
        errors.append(f"{label} may use placement or pan, not both")
    if "placement" in value and value["placement"] not in PLACEMENTS:
        errors.append(f"{label}.placement must be one of {', '.join(PLACEMENTS)}")
    if "pan" in value:
        pan = value["pan"]
        if not isinstance(pan, (int, float)) or not -1 <= pan <= 1:
            errors.append(f"{label}.pan must be between -1 and 1")


def _validate_ambience(ambience, errors):
    if not isinstance(ambience, dict):
        errors.append("ambience must be an object")
        return
    file_value = ambience.get("file")
    if not _non_empty_string(file_value):
        errors.append("ambience.file is required")
    elif "://" in file_value:
        errors.append("ambience.file must be a local file path, not a URL")
    gain = ambience.get("gain_db", -22)
    if not isinstance(gain, (int, float)) or not -60 <= gain <= 6:
        errors.append("ambience.gain_db must be between -60 and 6")
    if not isinstance(ambience.get("loop", True), bool):
        errors.append("ambience.loop must be boolean")
    for name, default in (("fade_in_ms", 1000), ("fade_out_ms", 1500)):
        value = ambience.get(name, default)
        if not isinstance(value, (int, float)) or value < 0:
            errors.append(f"ambience.{name} must be >= 0")
    if ambience.get("ducking", "speech") not in DUCKING_MODES:
        errors.append(f"ambience.ducking must be one of {', '.join(DUCKING_MODES)}")


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
    if version == 1 and uses_v2:
        errors.append("actors, placement, pan, and ambience require schema_version 2")
    if version == 2 and "ambience" in program:
        _validate_ambience(program["ambience"], errors)

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
