import json
from pathlib import Path

_CAPABILITIES_PATH = Path(__file__).with_name("capabilities.json")

# Intentionally restrained. These are synthetic early-reflection approximations,
# not authentic impulse responses of named rooms.
_ACOUSTIC_FILTERS = {
    "dry": None,
    "outdoor-open": None,
    "small-stone-room": "aecho=0.96:0.92:45|90:0.10|0.05",
    "large-stone-interior": "aecho=0.96:0.90:90|180|360:0.10|0.06|0.03",
    "confined-stone": "aecho=0.96:0.92:28|58:0.12|0.06,lowpass=f=9000",
}


def load_capabilities():
    return json.loads(_CAPABILITIES_PATH.read_text(encoding="utf-8"))


def public_capabilities(category=None, engine_version=None):
    data = load_capabilities()
    result = {**data}
    if engine_version is not None:
        result["engine_version"] = engine_version
    if category is None:
        return result
    effects = data.get("effects", {})
    if category not in effects:
        raise ValueError(f"Unknown capability category: {category}")
    return {
        "version": data.get("version"),
        "feature_level": data.get("feature_level"),
        "engine_version": engine_version,
        "category": category,
        "value": effects[category],
    }


def acoustic_space_ids():
    return tuple(_ACOUSTIC_FILTERS)


def acoustic_space_filter(space_id):
    if space_id not in _ACOUSTIC_FILTERS:
        raise ValueError(f"Unknown acoustic space: {space_id}")
    return _ACOUSTIC_FILTERS[space_id]


def scene_transition_defaults():
    return load_capabilities()["effects"]["transitions"]["scene"]


def punctuation_transition_defaults():
    return load_capabilities()["effects"]["transitions"]["punctuation"]
