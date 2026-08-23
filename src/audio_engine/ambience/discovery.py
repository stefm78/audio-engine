import json
from pathlib import Path
from urllib.parse import quote, quote_plus


def default_sources_path():
    return Path(__file__).parent.parent / "ambience_sources.json"


def load_sources(path=None):
    source = Path(path) if path else default_sources_path()
    data = json.loads(source.read_text(encoding="utf-8"))
    entries = data.get("sources")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Ambience discovery sources must be a non-empty array")
    ids = [entry.get("id") for entry in entries]
    if any(not isinstance(value, str) or not value.strip() for value in ids):
        raise ValueError("Every ambience discovery source needs a non-empty id")
    if len(ids) != len(set(ids)):
        raise ValueError("Ambience discovery source ids must be unique")
    return data, source


def discovery_plan(query, source_ids=None, path=None):
    query = str(query or "").strip()
    if not query:
        raise ValueError("Discovery query must not be empty")

    data, _ = load_sources(path)
    sources = data["sources"]
    requested = list(source_ids or [])
    if requested:
        known = {entry["id"] for entry in sources}
        unknown = [source_id for source_id in requested if source_id not in known]
        if unknown:
            raise ValueError(f"Unknown ambience discovery source(s): {', '.join(unknown)}")
        requested_set = set(requested)
        sources = [entry for entry in sources if entry["id"] in requested_set]

    encoded_query = quote_plus(query)
    encoded_path = quote(query.strip(), safe="")
    planned = []
    for source in sources:
        item = dict(source)
        template = item.pop("search_url_template", None)
        item["query"] = query
        item["search_url"] = (
            template.replace("{query}", encoded_query).replace("{query_path}", encoded_path)
            if template else None
        )
        item["network_action"] = "none"
        planned.append(item)

    return {
        "schema_version": 1,
        "query": query,
        "mode": "discovery-plan",
        "network_requests_performed": 0,
        "count": len(planned),
        "sources": planned,
        "next_step": "Search externally, download a chosen candidate under its applicable terms, then run `audio-engine ambience qualify FILE ...`.",
    }
