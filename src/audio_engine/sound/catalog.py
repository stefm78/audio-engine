import json
import re
from pathlib import Path

SOUND_TYPES = ("ambience", "event")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def default_catalog_path():
    return Path(__file__).parent.parent / "sounds.json"


def _non_empty(value):
    return isinstance(value, str) and bool(value.strip())


def _validate_entry(entry, index):
    label = f"sounds[{index}]"
    if not isinstance(entry, dict):
        raise ValueError(f"{label} must be an object")
    if not _non_empty(entry.get("id")):
        raise ValueError(f"{label}.id is required")
    if entry.get("type") not in SOUND_TYPES:
        raise ValueError(f"{label}.type must be one of {', '.join(SOUND_TYPES)}")
    if entry.get("status") != "validated":
        raise ValueError(f"{label}.status must be validated in the public catalog")
    tags = entry.get("tags", [])
    if not isinstance(tags, list) or any(not _non_empty(tag) for tag in tags):
        raise ValueError(f"{label}.tags must be an array of non-empty strings")
    sha = entry.get("content_sha256")
    if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
        raise ValueError(f"{label}.content_sha256 must be a lowercase SHA-256")
    license_info = entry.get("license")
    if not isinstance(license_info, dict) or license_info.get("verified") is not True:
        raise ValueError(f"{label}.license.verified must be true")
    if not _non_empty(license_info.get("id")):
        raise ValueError(f"{label}.license.id is required")
    asset = entry.get("asset")
    if not isinstance(asset, dict):
        raise ValueError(f"{label}.asset is required")
    if not (_non_empty(asset.get("file")) or _non_empty(asset.get("location"))):
        raise ValueError(f"{label}.asset needs file or location")
    if _non_empty(asset.get("file")):
        if "://" in asset["file"] or Path(asset["file"]).is_absolute():
            raise ValueError(f"{label}.asset.file must be a local relative path")


def load_catalog(path=None):
    source = Path(path) if path else default_catalog_path()
    data = json.loads(source.read_text(encoding="utf-8"))
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Sound catalog entries must be an array")
    for index, entry in enumerate(entries, start=1):
        _validate_entry(entry, index)
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Sound catalog ids must be unique")
    return data, source


def public_catalog(path=None, tags=None, sound_type=None):
    catalog, _ = load_catalog(path)
    entries = catalog.get("entries", [])
    requested = set(tags or [])
    if requested:
        entries = [entry for entry in entries if requested.issubset(set(entry.get("tags", [])))]
    if sound_type:
        if sound_type not in SOUND_TYPES:
            raise ValueError(f"sound type must be one of {', '.join(SOUND_TYPES)}")
        entries = [entry for entry in entries if entry.get("type") == sound_type]
    return {
        "version": catalog.get("version"),
        "description": catalog.get("description"),
        "policy": catalog.get("policy", {}),
        "count": len(entries),
        "entries": entries,
    }


def sound_info(sound_id, path=None):
    catalog, source = load_catalog(path)
    for entry in catalog.get("entries", []):
        if entry.get("id") == sound_id:
            return entry, source
    raise ValueError(f"Unknown sound: {sound_id}")
