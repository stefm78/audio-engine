import hashlib
import json
from pathlib import Path

SUPPORTED_SCHEMA_VERSION = 1

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

def validate_program(program):
    errors = []
    if program.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"schema_version must be {SUPPORTED_SCHEMA_VERSION}")
    if not _non_empty_string(program.get("id")):
        errors.append("id is required")
    if not _non_empty_string(program.get("title")):
        errors.append("title is required")
    if not _non_empty_string(program.get("profile", "speech")):
        errors.append("profile must be a non-empty string")
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
    if errors:
        raise ContractError("; ".join(errors))
    return program

def validate_assembly(plan):
    errors = []
    if plan.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"schema_version must be {SUPPORTED_SCHEMA_VERSION}")
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
