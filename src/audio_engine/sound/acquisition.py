import html
import json
import re
import shutil
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import Request, urlopen

from ..ambience.qualification import qualify_candidate
from .catalog import load_catalog
from .selection import select_candidates

USER_AGENT = "recit-audio-engine/0.5 (+https://github.com/stefm78/audio-engine)"
DEFAULT_PROVIDERS = ("wikimedia-commons", "openverse")
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
AUDIO_EXTENSIONS = {".ogg", ".oga", ".wav", ".flac", ".mp3", ".m4a", ".aac", ".opus", ".webm"}


def _slug(value, fallback="sound"):
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return normalized or fallback


def _strip_html(value):
    text = re.sub(r"<[^>]+>", " ", html.unescape(str(value or "")))
    return re.sub(r"\s+", " ", text).strip()


def _tokens(*values):
    text = " ".join(_strip_html(value) for value in values)
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    words = re.findall(r"[a-z0-9][a-z0-9-]{2,}", normalized)
    stop = {"the", "and", "this", "that", "with", "from", "file", "audio", "sound", "recording"}
    result = []
    for word in words:
        if word not in stop and word not in result:
            result.append(word)
    return result[:64]


def _http_json(url, timeout=20):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _commons_license_id(short_name, license_url=None):
    label = _strip_html(short_name).lower()
    url = str(license_url or "").lower()
    if "cc0" in label or "/publicdomain/zero/1.0" in url:
        return "CC0-1.0"
    if "public domain" in label or "/publicdomain/mark/1.0" in url:
        return "Public-Domain"
    if "cc by 4.0" in label or "/licenses/by/4.0" in url:
        return "CC-BY-4.0"
    if "cc by 3.0" in label or "/licenses/by/3.0" in url:
        return "CC-BY-3.0"
    return None


def _metadata_value(metadata, key):
    value = metadata.get(key, {}) if isinstance(metadata, dict) else {}
    return value.get("value") if isinstance(value, dict) else None


def _commons_record(page, discovery_provider="wikimedia-commons", rank=1, query=None):
    imageinfo = page.get("imageinfo") or []
    if not imageinfo:
        return None
    info = imageinfo[0]
    mime = str(info.get("mime") or "")
    mediatype = str(info.get("mediatype") or "").upper()
    source_url = info.get("url")
    if not source_url or (not mime.startswith("audio/") and mediatype != "AUDIO"):
        return None

    metadata = info.get("extmetadata") or {}
    license_short = _metadata_value(metadata, "LicenseShortName")
    license_url = _metadata_value(metadata, "LicenseUrl")
    license_id = _commons_license_id(license_short, license_url)
    description = _metadata_value(metadata, "ImageDescription")
    artist = _strip_html(_metadata_value(metadata, "Artist"))
    credit = _strip_html(_metadata_value(metadata, "Credit"))
    title = page.get("title") or Path(urlparse(source_url).path).name
    description_url = info.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{title.replace(' ', '_')}"
    identifier = title
    page_id = page.get("pageid")
    stable_id = f"commons-{page_id}" if page_id is not None else f"commons-{_slug(title)}"

    return {
        "id": stable_id,
        "provider": "wikimedia-commons",
        "discovery_provider": discovery_provider,
        "rank": int(rank),
        "query": query,
        "title": title,
        "description": _strip_html(description),
        "download_url": source_url,
        "source_page": description_url,
        "source_identifier": identifier,
        "license_id": license_id,
        "license_url": license_url,
        "attribution": artist or credit or None,
        "tags": _tokens(title, description),
        "source_metadata_verified": True,
        "size_bytes": info.get("size"),
        "mime": mime,
    }


def discover_wikimedia(query, limit=8):
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(min(max(int(limit) * 4, 8), 50)),
        "prop": "imageinfo",
        "iiprop": "url|mime|mediatype|size|extmetadata",
        "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|Credit|AttributionRequired|ImageDescription",
        "iiextmetadatalanguage": "en",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
    data = _http_json(url)
    pages = (data.get("query") or {}).get("pages") or []
    results = []
    for page in pages:
        record = _commons_record(page, rank=len(results) + 1, query=query)
        if record:
            results.append(record)
        if len(results) >= int(limit):
            break
    return results


def _commons_lookup(source_page, discovery_provider, rank, query):
    parsed = urlparse(source_page)
    if parsed.hostname not in {"commons.wikimedia.org", "www.commons.wikimedia.org"}:
        return None
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "imageinfo",
        "iiprop": "url|mime|mediatype|size|extmetadata",
        "iiextmetadatafilter": "LicenseShortName|LicenseUrl|Artist|Credit|AttributionRequired|ImageDescription",
        "iiextmetadatalanguage": "en",
    }
    query_values = parse_qs(parsed.query)
    if query_values.get("curid"):
        params["pageids"] = query_values["curid"][0]
    elif "/wiki/" in parsed.path:
        params["titles"] = unquote(parsed.path.split("/wiki/", 1)[1]).replace("_", " ")
    elif query_values.get("title"):
        params["titles"] = query_values["title"][0]
    else:
        return None
    data = _http_json("https://commons.wikimedia.org/w/api.php?" + urlencode(params))
    pages = (data.get("query") or {}).get("pages") or []
    if not pages:
        return None
    return _commons_record(pages[0], discovery_provider=discovery_provider, rank=rank, query=query)


def discover_openverse(query, limit=8):
    params = {"q": query, "page_size": str(min(max(int(limit) * 3, 8), 20))}
    data = _http_json("https://api.openverse.org/v1/audio/?" + urlencode(params))
    results = []
    for index, item in enumerate(data.get("results") or [], start=1):
        landing = item.get("foreign_landing_url")
        if not landing:
            continue
        # Openverse is discovery-only. Final licence/provenance proof must come
        # from a supported upstream verifier. Commons is the first one.
        record = _commons_lookup(landing, "openverse", index, query)
        if record:
            record["openverse_id"] = item.get("id")
            results.append(record)
        if len(results) >= int(limit):
            break
    return results


def discover_candidates(query, providers=None, limit=8):
    requested = list(providers or DEFAULT_PROVIDERS)
    unknown = sorted(set(requested) - set(DEFAULT_PROVIDERS))
    if unknown:
        raise ValueError("Unsupported autonomous acquisition provider(s): " + ", ".join(unknown))
    results = []
    diagnostics = []
    for provider in requested:
        try:
            found = discover_wikimedia(query, limit) if provider == "wikimedia-commons" else discover_openverse(query, limit)
            diagnostics.append({"provider": provider, "status": "success", "count": len(found)})
            results.extend(found)
        except Exception as exc:  # provider failure must not abort multi-source discovery
            diagnostics.append({"provider": provider, "status": "error", "error": str(exc)})
    deduped = []
    seen = set()
    for record in results:
        key = record.get("download_url") or record.get("source_identifier")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped, diagnostics


def _extension_for(record):
    suffix = Path(urlparse(record.get("download_url") or "").path).suffix.lower()
    if suffix in AUDIO_EXTENSIONS:
        return suffix
    mime = str(record.get("mime") or "").lower()
    return {
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/flac": ".flac",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/opus": ".opus",
    }.get(mime, ".audio")


def _download(record, directory, max_bytes=MAX_DOWNLOAD_BYTES):
    url = record.get("download_url")
    parsed = urlparse(url or "")
    if parsed.scheme != "https":
        raise ValueError("Autonomous acquisition accepts HTTPS assets only")
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{_slug(record.get('id'))}{_extension_for(record)}"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response, target.open("wb") as stream:
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > int(max_bytes):
            raise ValueError(f"Candidate exceeds download limit: {declared} bytes")
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > int(max_bytes):
                raise ValueError(f"Candidate exceeds download limit: >{max_bytes} bytes")
            stream.write(chunk)
    if not target.exists() or target.stat().st_size == 0:
        raise ValueError("Downloaded candidate is empty")
    return target


def _catalog_hit(sound_id, sound_type, required_tags, preferred_tags, catalog_path=None):
    catalog, _ = load_catalog(catalog_path)
    entries = catalog.get("entries", [])
    required = set(required_tags or [])
    preferred = set(preferred_tags or [])
    if sound_id:
        for entry in entries:
            if entry.get("id") == sound_id:
                if entry.get("type") != sound_type:
                    raise ValueError(f"Existing sound {sound_id} has type {entry.get('type')}, expected {sound_type}")
                return entry
        # A caller-supplied semantic id is an identity contract. Never silently
        # substitute a different catalog entry merely because its tags match.
        return None
    matches = [
        entry for entry in entries
        if entry.get("type") == sound_type and required.issubset(set(entry.get("tags", [])))
    ]
    matches.sort(key=lambda entry: (-len(preferred & set(entry.get("tags", []))), entry.get("id", "")))
    return matches[0] if matches else None


def ensure_sound(
    query,
    *,
    sound_type,
    sound_id=None,
    required_tags=None,
    preferred_tags=None,
    providers=None,
    output_dir=".sound-acquisition",
    catalog_path=None,
    limit=8,
    min_score=70.0,
):
    requested_id = sound_id or _slug(query, "auto-sound")[:60]
    hit = _catalog_hit(requested_id if sound_id else None, sound_type, required_tags, preferred_tags, catalog_path)
    if hit:
        return {
            "schema_version": 1,
            "status": "catalog-hit",
            "decision": "automatic",
            "selected_id": hit["id"],
            "selected": hit,
            "network_requests_required": False,
        }

    root = Path(output_dir)
    candidates_dir = root / "candidates"
    previews_dir = root / "audit-previews"
    assets_dir = root / "assets"
    root.mkdir(parents=True, exist_ok=True)
    records, diagnostics = discover_candidates(query, providers=providers, limit=limit)
    qualified = []
    failures = []

    for record in records:
        try:
            source = _download(record, candidates_dir)
            candidate = qualify_candidate(
                source,
                candidate_id=record["id"],
                candidate_type=sound_type,
                source_provider=record["provider"],
                source_page=record["source_page"],
                source_identifier=record.get("source_identifier"),
                license_id=record.get("license_id"),
                attribution=record.get("attribution"),
                raw_redistribution="unknown",
                tags=record.get("tags", []),
                preview_dir=previews_dir,
                source_metadata_verified=bool(record.get("source_metadata_verified")),
            )
            candidate["discovery"] = {
                "query": query,
                "provider": record.get("discovery_provider"),
                "rank": record.get("rank"),
                "title": record.get("title"),
            }
            candidate_path = candidates_dir / f"{_slug(record['id'])}.candidate.json"
            candidate_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            qualified.append(candidate)
        except Exception as exc:
            failures.append({"id": record.get("id"), "title": record.get("title"), "error": str(exc)})

    selection = select_candidates(
        qualified,
        sound_type=sound_type,
        required_tags=required_tags,
        preferred_tags=preferred_tags,
        min_score=min_score,
    )
    if selection.get("status") != "selected":
        result = {
            **selection,
            "query": query,
            "requested_id": requested_id,
            "discovery": diagnostics,
            "qualified_count": len(qualified),
            "failures": failures,
            "network_requests_required": True,
        }
        (root / f"{requested_id}.selection.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return result

    winner = selection["selected"]
    source = Path(winner["file"]["path"])
    assets_dir.mkdir(parents=True, exist_ok=True)
    asset = assets_dir / f"{requested_id}{source.suffix.lower()}"
    shutil.copyfile(source, asset)
    entry = {
        "id": requested_id,
        "type": sound_type,
        "status": "validated",
        "tags": winner.get("tags", []),
        "content_sha256": winner["file"]["content_sha256"],
        "source": winner.get("source", {}),
        "license": {
            "id": winner.get("license", {}).get("id"),
            "verified": True,
            "verification_method": winner.get("license", {}).get("verification_method"),
            "attribution": winner.get("license", {}).get("attribution"),
            "raw_redistribution": winner.get("license", {}).get("raw_redistribution"),
        },
        "asset": {"file": f"assets/{asset.name}", "status": "locked"},
        "provenance": {
            "selection": "automatic",
            "query": query,
            "score": selection.get("selected_score"),
            "discovery": winner.get("discovery"),
        },
    }
    catalog = {
        "version": 1,
        "description": "Runtime validated sound overlay generated autonomously by Audio Engine.",
        "policy": {"publication": "validated-only", "render_network_access": False},
        "entries": [entry],
    }
    catalog_file = root / f"{requested_id}.catalog.json"
    catalog_file.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / "sounds.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        **selection,
        "status": "selected",
        "selected_id": requested_id,
        "selected": entry,
        "query": query,
        "discovery": diagnostics,
        "qualified_count": len(qualified),
        "failures": failures,
        "network_requests_required": True,
        "materialized": {
            "asset": str(asset),
            "catalog": str(catalog_file),
            "render_catalog": str(root / "sounds.json"),
        },
    }
    (root / f"{requested_id}.selection.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result
