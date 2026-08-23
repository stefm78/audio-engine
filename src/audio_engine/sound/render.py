import hashlib
import json
import math
from pathlib import Path

from ..audio import run_ffmpeg
from ..contract import sha256_file
from .catalog import load_catalog, sound_info

PLACEMENT_PAN = {
    "left": -0.45,
    "center": 0.0,
    "right": 0.45,
}


def _asset_root(reference_path):
    reference_path = Path(reference_path).resolve()
    cwd = Path.cwd().resolve()
    try:
        reference_path.relative_to(cwd)
        return cwd
    except ValueError:
        return reference_path.parent


def _resolve_relative_source(reference_path, value, label):
    if "://" in value:
        raise ValueError(f"{label} must be a local relative path, not a URL")
    if Path(value).is_absolute():
        raise ValueError(f"{label} must be relative")
    root = _asset_root(reference_path)
    source = (Path(reference_path).parent / value).resolve()
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes allowed asset root: {value}") from exc
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"Sound input not found: {source}")
    return source


def _constant_power_pan_filter(pan):
    pan = max(-1.0, min(1.0, float(pan)))
    angle = (pan + 1.0) * math.pi / 4.0
    left = math.cos(angle)
    right = math.sin(angle)
    return f"pan=stereo|c0={left:.8f}*c0|c1={right:.8f}*c0"


def _resolve_item(item, role, program_path, sounds_path=None):
    sound_id = item.get("sound")
    file_value = item.get("file")
    entry = None
    catalog_source = None
    if sound_id:
        entry, catalog_source = sound_info(sound_id, sounds_path)
        expected_type = "event" if role == "event" else "ambience"
        if entry.get("type") != expected_type:
            raise ValueError(
                f"Sound {sound_id} has type {entry.get('type')}; {role} requires {expected_type}"
            )
        asset_file = entry.get("asset", {}).get("file")
        if not asset_file:
            location = entry.get("asset", {}).get("location")
            raise ValueError(
                f"Sound {sound_id} is validated but not materialized locally"
                + (f" ({location})" if location else "")
            )
        source = _resolve_relative_source(catalog_source, asset_file, f"sound {sound_id} asset.file")
        defaults = entry.get("defaults", {}) if isinstance(entry.get("defaults"), dict) else {}
    else:
        source = _resolve_relative_source(program_path, file_value, f"soundscape.{role}.file")
        defaults = {}

    merged = {**defaults, **item}
    default_gain = -18 if role == "event" else (-22 if role == "bed" else -28)
    metadata = {
        "role": role,
        "sound": sound_id,
        "file": file_value,
        "source_sha256": sha256_file(source),
        "gain_db": merged.get("gain_db", default_gain),
    }
    if entry:
        metadata.update({
            "catalog_type": entry.get("type"),
            "catalog_content_sha256": entry.get("content_sha256"),
            "source": entry.get("source"),
            "license": entry.get("license"),
            "asset": entry.get("asset"),
        })
        if metadata["source_sha256"] != entry.get("content_sha256"):
            raise ValueError(f"Sound {sound_id} content hash does not match catalog")
    return source, merged, metadata


def soundscape_source_sha256(soundscape, program_path, sounds_path=None):
    catalog_sha = None
    if any(item.get("sound") for item in _all_items(soundscape)):
        _, catalog_source = load_catalog(sounds_path)
        catalog_sha = sha256_file(catalog_source)
    payload = {"catalog_sha256": catalog_sha, "components": []}
    for role, item in _role_items(soundscape):
        source, merged, metadata = _resolve_item(item, role, program_path, sounds_path)
        payload["components"].append({
            "role": role,
            "sound": item.get("sound"),
            "source_sha256": metadata["source_sha256"],
            "config": merged,
        })
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _all_items(soundscape):
    items = []
    if soundscape.get("bed"):
        items.append(soundscape["bed"])
    items.extend(soundscape.get("layers", []))
    items.extend(soundscape.get("events", []))
    return items


def _role_items(soundscape):
    if soundscape.get("bed"):
        yield "bed", soundscape["bed"]
    for item in soundscape.get("layers", []):
        yield "layer", item
    for item in soundscape.get("events", []):
        yield "event", item


def _engine_sha256():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def render_soundscape(
    soundscape,
    program_path,
    cache_root,
    duration_seconds,
    sample_rate_hz,
    sounds_path=None,
    channels=2,
):
    if channels != 2:
        raise ValueError("Soundscape rendering currently requires stereo output")
    duration = max(0.001, float(duration_seconds))
    resolved = []
    fingerprint_components = []
    for role, item in _role_items(soundscape):
        source, merged, metadata = _resolve_item(item, role, program_path, sounds_path)
        if role == "event" and float(merged.get("at_ms", 0)) / 1000.0 >= duration:
            raise ValueError(f"Sound event at {merged.get('at_ms')} ms starts after program audio ends")
        resolved.append((role, source, merged, metadata))
        fingerprint_components.append({
            "role": role,
            "source_sha256": metadata["source_sha256"],
            "config": merged,
        })

    fingerprint_payload = {
        "components": fingerprint_components,
        "duration_seconds": round(duration, 3),
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
        "sound_engine_sha256": _engine_sha256(),
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    output = cache_root / f"{fingerprint}.wav"

    components = []
    for role, _, merged, metadata in resolved:
        component = {**metadata}
        if role != "event":
            component.update({
                "loop": merged.get("loop", True),
                "fade_in_ms": merged.get("fade_in_ms", 1000),
                "fade_out_ms": merged.get("fade_out_ms", 1500),
            })
        else:
            component.update({
                "at_ms": merged.get("at_ms"),
                "placement": merged.get("placement", "center"),
            })
        components.append(component)

    metadata = {
        "fingerprint": fingerprint,
        "ducking": soundscape.get("ducking", "speech"),
        "component_count": len(components),
        "components": components,
    }
    if output.exists() and output.stat().st_size > 0:
        return output, True, metadata

    args = [
        "-f", "lavfi",
        "-t", f"{duration:.3f}",
        "-i", f"anullsrc=r={sample_rate_hz}:cl=stereo",
    ]
    for role, source, merged, _ in resolved:
        if role != "event" and merged.get("loop", True):
            args.extend(["-stream_loop", "-1"])
        args.extend(["-i", str(source)])

    filters = []
    mix_labels = ["[0:a]"]
    for index, (role, _, merged, _) in enumerate(resolved, start=1):
        gain = float(merged.get("gain_db", -18 if role == "event" else (-22 if role == "bed" else -28)))
        chain = [f"volume={gain}dB", f"aresample={sample_rate_hz}"]
        if role == "event":
            placement = merged.get("placement", "center")
            if placement != "center":
                chain.extend([
                    "aformat=channel_layouts=mono",
                    _constant_power_pan_filter(PLACEMENT_PAN[placement]),
                ])
            else:
                chain.append("aformat=channel_layouts=stereo")
            at_ms = int(round(float(merged.get("at_ms", 0))))
            chain.extend([f"adelay={at_ms}|{at_ms}", f"atrim=0:{duration:.3f}"])
        else:
            chain.append("aformat=channel_layouts=stereo")
            fade_in = max(0.0, min(float(merged.get("fade_in_ms", 1000)) / 1000.0, duration))
            fade_out = max(0.0, min(float(merged.get("fade_out_ms", 1500)) / 1000.0, duration))
            if fade_in > 0:
                chain.append(f"afade=t=in:st=0:d={fade_in:.3f}")
            if fade_out > 0:
                start = max(0.0, duration - fade_out)
                chain.append(f"afade=t=out:st={start:.3f}:d={fade_out:.3f}")
            chain.append(f"atrim=0:{duration:.3f}")
        label = f"s{index}"
        filters.append(f"[{index}:a]{','.join(chain)}[{label}]")
        mix_labels.append(f"[{label}]")

    filters.append(
        "".join(mix_labels)
        + f"amix=inputs={len(mix_labels)}:duration=first:dropout_transition=0:normalize=0[out]"
    )
    args.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[out]",
        "-t", f"{duration:.3f}",
        "-ar", str(sample_rate_hz),
        "-ac", "2",
        "-c:a", "pcm_s16le",
        str(output),
    ])
    run_ffmpeg(args)
    return output, False, metadata
