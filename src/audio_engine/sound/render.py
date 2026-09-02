import hashlib
import json
import math
from pathlib import Path

from ..audio import probe_duration_seconds, run_ffmpeg
from ..contract import sha256_file
from ..effects import (
    bridge_transition_defaults,
    punctuation_transition_defaults,
    scene_transition_defaults,
)
from .catalog import load_catalog, sound_info

PLACEMENT_PAN = {
    "left": -0.45,
    "slight-left": -0.16,
    "center": 0.0,
    "slight-right": 0.16,
    "right": 0.45,
}


def narration_space_requirements(soundscape, schema_version):
    if schema_version < 4:
        return {}
    spaces = {}
    for item in soundscape.get("events", []):
        role = item.get("role", "punctuation")
        if role == "scene":
            sequence = int(item["after_segment"])
            spaces[sequence] = max(float(item["space_ms"]), spaces.get(sequence, 0.0))
        elif schema_version >= 5 and role == "bridge":
            sequence = int(item["after_segment"])
            pre_roll_ms = float(bridge_transition_defaults()["pre_roll_ms"])
            pause_ms = pre_roll_ms + float(item["foreground_ms"])
            spaces[sequence] = max(pause_ms, spaces.get(sequence, 0.0))
    return spaces


def scene_space_requirements(soundscape, schema_version):
    """Compatibility alias for callers written against Audio Engine 0.7."""
    return narration_space_requirements(soundscape, schema_version)


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
    digest = hashlib.sha256(Path(__file__).read_bytes())
    from .. import effects
    digest.update(Path(effects.__file__).read_bytes())
    return digest.hexdigest()


def _bounded_fades(play_duration, fade_in_ms, fade_out_ms):
    play_ms = max(1.0, play_duration * 1000.0)
    max_each = play_ms / 2.0
    return min(float(fade_in_ms), max_each), min(float(fade_out_ms), max_each)


def _resolve_event_window(merged, source, schema_version, timeline, master_duration):
    source_duration = probe_duration_seconds(source)
    intent_role = merged.get("role", "punctuation") if schema_version >= 4 else "punctuation"
    requested_play_ms = None
    foreground_ms = None
    carry_under_speech_ms = None

    if intent_role == "scene":
        defaults = scene_transition_defaults()
        sequence = int(merged["after_segment"])
        if not timeline or sequence not in timeline:
            raise ValueError(f"Scene event references unavailable segment {sequence}")
        space_ms = float(merged["space_ms"])
        pre_roll_ms = float(defaults["pre_roll_ms"])
        post_roll_ms = float(defaults["post_roll_ms"])
        at_ms = float(timeline[sequence]["end_ms"]) + pre_roll_ms
        available_ms = max(1.0, space_ms - pre_roll_ms - post_roll_ms)
        requested_play_ms = available_ms
        requested_fade_in = merged.get("fade_in_ms", defaults["default_fade_in_ms"])
        requested_fade_out = merged.get("fade_out_ms", defaults["default_fade_out_ms"])
    elif intent_role == "bridge":
        defaults = bridge_transition_defaults()
        sequence = int(merged["after_segment"])
        if not timeline or sequence not in timeline:
            raise ValueError(f"Bridge event references unavailable segment {sequence}")
        pre_roll_ms = float(defaults["pre_roll_ms"])
        foreground_ms = float(merged["foreground_ms"])
        carry_under_speech_ms = float(merged["carry_under_speech_ms"])
        at_ms = float(timeline[sequence]["end_ms"]) + pre_roll_ms
        requested_play_ms = foreground_ms + carry_under_speech_ms
        available_ms = requested_play_ms
        requested_fade_in = merged.get("fade_in_ms", defaults["default_fade_in_ms"])
        requested_fade_out = merged.get("fade_out_ms", defaults["default_fade_out_ms"])
    else:
        defaults = punctuation_transition_defaults()
        at_ms = float(merged.get("at_ms", 0))
        available_ms = max(1.0, (master_duration * 1000.0) - at_ms)
        requested_play_ms = available_ms
        if schema_version >= 4:
            requested_fade_in = merged.get("fade_in_ms", defaults["default_fade_in_ms"])
            requested_fade_out = merged.get("fade_out_ms", defaults["default_fade_out_ms"])
        else:
            requested_fade_in = 0
            requested_fade_out = 0

    if at_ms / 1000.0 >= master_duration:
        raise ValueError(f"Sound event at {round(at_ms)} ms starts after program audio ends")
    play_duration = available_ms / 1000.0
    clipped_by_source = False
    clipped_by_master = False
    if source_duration is not None and source_duration < play_duration:
        play_duration = source_duration
        clipped_by_source = True
    master_available = master_duration - (at_ms / 1000.0)
    if master_available < play_duration:
        play_duration = master_available
        clipped_by_master = True
    if play_duration <= 0:
        raise ValueError("Sound event has no renderable duration")
    fade_in_ms, fade_out_ms = _bounded_fades(
        play_duration,
        requested_fade_in,
        requested_fade_out,
    )
    return {
        "intent_role": intent_role,
        "at_ms": int(round(at_ms)),
        "play_duration": play_duration,
        "requested_play_duration_ms": round(float(requested_play_ms), 3),
        "duration_clipped": bool(clipped_by_source or clipped_by_master),
        "clipped_by_source": clipped_by_source,
        "clipped_by_master": clipped_by_master,
        "fade_in_ms": fade_in_ms,
        "fade_out_ms": fade_out_ms,
        "after_segment": merged.get("after_segment"),
        "space_ms": merged.get("space_ms"),
        "foreground_ms": foreground_ms,
        "carry_under_speech_ms": carry_under_speech_ms,
    }


def render_soundscape(
    soundscape,
    program_path,
    cache_root,
    duration_seconds,
    sample_rate_hz,
    sounds_path=None,
    channels=2,
    schema_version=3,
    timeline=None,
):
    if channels != 2:
        raise ValueError("Soundscape rendering currently requires stereo output")
    duration = max(0.001, float(duration_seconds))
    resolved = []
    fingerprint_components = []
    for role, item in _role_items(soundscape):
        source, merged, metadata = _resolve_item(item, role, program_path, sounds_path)
        event_window = None
        if role == "event":
            event_window = _resolve_event_window(
                merged,
                source,
                schema_version,
                timeline,
                duration,
            )
        resolved.append((role, source, merged, metadata, event_window))
        fingerprint_components.append({
            "role": role,
            "source_sha256": metadata["source_sha256"],
            "config": merged,
            "resolved_event": event_window,
        })

    fingerprint_payload = {
        "components": fingerprint_components,
        "duration_seconds": round(duration, 3),
        "sample_rate_hz": sample_rate_hz,
        "channels": channels,
        "schema_version": schema_version,
        "sound_engine_sha256": _engine_sha256(),
    }
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    output = cache_root / f"{fingerprint}.wav"

    components = []
    for role, _, merged, metadata, event_window in resolved:
        component = {**metadata}
        if role != "event":
            component.update({
                "intent_role": "texture",
                "loop": merged.get("loop", True),
                "fade_in_ms": merged.get("fade_in_ms", 1000),
                "fade_out_ms": merged.get("fade_out_ms", 1500),
            })
        else:
            component.update({
                "intent_role": event_window["intent_role"],
                "at_ms": event_window["at_ms"],
                "requested_at_ms": merged.get("at_ms"),
                "after_segment": event_window["after_segment"],
                "space_ms": event_window["space_ms"],
                "foreground_ms": event_window["foreground_ms"],
                "carry_under_speech_ms": event_window["carry_under_speech_ms"],
                "requested_play_duration_ms": event_window["requested_play_duration_ms"],
                "play_duration_ms": round(event_window["play_duration"] * 1000.0, 3),
                "duration_clipped": event_window["duration_clipped"],
                "clipped_by_source": event_window["clipped_by_source"],
                "clipped_by_master": event_window["clipped_by_master"],
                "fade_in_ms": round(event_window["fade_in_ms"], 3),
                "fade_out_ms": round(event_window["fade_out_ms"], 3),
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
    for role, source, merged, _, _ in resolved:
        if role != "event" and merged.get("loop", True):
            args.extend(["-stream_loop", "-1"])
        args.extend(["-i", str(source)])

    filters = []
    mix_labels = ["[0:a]"]
    for index, (role, _, merged, _, event_window) in enumerate(resolved, start=1):
        gain = float(merged.get("gain_db", -18 if role == "event" else (-22 if role == "bed" else -28)))
        chain = [f"volume={gain}dB", f"aresample={sample_rate_hz}"]
        if role == "event":
            play_duration = event_window["play_duration"]
            chain.append(f"atrim=0:{play_duration:.3f}")
            fade_in = event_window["fade_in_ms"] / 1000.0
            fade_out = event_window["fade_out_ms"] / 1000.0
            if fade_in > 0:
                chain.append(f"afade=t=in:st=0:d={fade_in:.3f}")
            if fade_out > 0:
                start = max(0.0, play_duration - fade_out)
                chain.append(f"afade=t=out:st={start:.3f}:d={fade_out:.3f}")
            placement = merged.get("placement", "center")
            if placement != "center":
                chain.extend([
                    "aformat=channel_layouts=mono",
                    _constant_power_pan_filter(PLACEMENT_PAN[placement]),
                ])
            else:
                chain.append("aformat=channel_layouts=stereo")
            at_ms = event_window["at_ms"]
            chain.append(f"adelay={at_ms}|{at_ms}")
            chain.append(f"atrim=0:{duration:.3f}")
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
