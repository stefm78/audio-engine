import json
from pathlib import Path


def default_catalog_path():
    return Path(__file__).parent.parent / "ambiences.json"


def load_catalog(path=None):
    source = Path(path) if path else default_catalog_path()
    data = json.loads(source.read_text(encoding="utf-8"))
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Ambience catalog entries must be an array")
    ids = [entry.get("id") for entry in entries]
    if any(not isinstance(value, str) or not value.strip() for value in ids):
        raise ValueError("Every ambience catalog entry needs a non-empty id")
    if len(ids) != len(set(ids)):
        raise ValueError("Ambience catalog ids must be unique")
    return data, source


def public_catalog(path=None, tags=None):
    catalog, _ = load_catalog(path)
    entries = catalog.get("entries", [])
    requested = set(tags or [])
    if requested:
        entries = [
            entry for entry in entries
            if requested.issubset(set(entry.get("tags", [])))
        ]
    return {
        "version": catalog.get("version"),
        "description": catalog.get("description"),
        "policy": catalog.get("policy", {}),
        "count": len(entries),
        "entries": entries,
    }


def ambience_info(ambience_id, path=None):
    catalog, _ = load_catalog(path)
    for entry in catalog.get("entries", []):
        if entry.get("id") == ambience_id:
            return {
                "version": catalog.get("version"),
                "policy": catalog.get("policy", {}),
                "entry": entry,
            }
    raise ValueError(f"Unknown ambience: {ambience_id}")
