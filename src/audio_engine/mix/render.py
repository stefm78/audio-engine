import math
from pathlib import Path

from ..audio import probe_duration_seconds, run_ffmpeg
from ..effects import acoustic_space_filter

PLACEMENT_PAN = {
    "left": -0.45,
    "slight-left": -0.16,
    "center": 0.0,
    "slight-right": 0.16,
    "right": 0.45,
}


def _declared_position(segment, actors):
    if "placement" in segment:
        placement = segment["placement"]
        return placement, PLACEMENT_PAN[placement]
    character_id = segment.get("character_id")
    actor = actors.get(character_id, {}) if character_id else {}
    placement = actor.get("placement", "center")
    return placement, PLACEMENT_PAN[placement]


def _declared_space(program, segment, actors):
    if "acoustic_space" in segment:
        return segment["acoustic_space"]
    character_id = segment.get("character_id")
    actor = actors.get(character_id, {}) if character_id else {}
    if "acoustic_space" in actor:
        return actor["acoustic_space"]
    return program.get("acoustic_space", "dry")


def stereo_required(program):
    if program.get("ambience") or program.get("soundscape"):
        return True
    actors = program.get("actors", {})
    for segment in program.get("segments", []):
        _, pan = _declared_position(segment, actors)
        if abs(pan) > 1e-9:
            return True
    return False


def _constant_power_pan_filter(pan):
    pan = max(-1.0, min(1.0, float(pan)))
    angle = (pan + 1.0) * math.pi / 4.0
    left = math.cos(angle)
    right = math.sin(angle)
    return f"pan=stereo|c0={left:.8f}*c0|c1={right:.8f}*c0"


def _silence_file(directory, duration_ms, sample_rate_hz, channels, cache):
    duration_ms = int(round(duration_ms))
    if duration_ms <= 0:
        return None
    key = (duration_ms, sample_rate_hz, channels)
    if key in cache:
        return cache[key]
    layout = "mono" if channels == 1 else "stereo"
    path = Path(directory) / f"silence-{duration_ms}ms-{channels}ch.wav"
    run_ffmpeg([
        "-f", "lavfi",
        "-i", f"anullsrc=r={sample_rate_hz}:cl={layout}",
        "-t", f"{duration_ms / 1000:.3f}",
        "-c:a", "pcm_s16le",
        str(path),
    ])
    cache[key] = path
    return path


def _prepare_voice_clip(source, destination, sample_rate_hz, channels, pan, acoustic_space):
    args = ["-i", str(source)]
    filters = []
    space_filter = acoustic_space_filter(acoustic_space)
    if space_filter:
        filters.append(space_filter)
    if channels == 2:
        filters.append(_constant_power_pan_filter(pan))
    if filters:
        args.extend(["-af", ",".join(filters)])
    args.extend([
        "-ar", str(sample_rate_hz),
        "-ac", str(channels),
        "-c:a", "pcm_s16le",
        str(destination),
    ])
    run_ffmpeg(args)


def _concat_pcm(parts, output_path):
    concat_file = Path(output_path).with_suffix(".concat.txt")
    concat_file.write_text(
        "".join(f"file '{Path(part).resolve()}'\n" for part in parts),
        encoding="utf-8",
    )
    try:
        run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c:a", "pcm_s16le",
            str(output_path),
        ])
    finally:
        concat_file.unlink(missing_ok=True)


def render_speech_track(
    program,
    resolved_segments,
    voice_clips,
    temp_dir,
    profile,
    scene_spaces=None,
):
    temp_dir = Path(temp_dir)
    channels = profile["channels"]
    sample_rate_hz = profile["sample_rate_hz"]
    actors = program.get("actors", {})
    scene_spaces = scene_spaces or {}
    parts = []
    silence_cache = {}
    timeline = {}

    lead_ms = program.get("lead_in_ms", 250)
    lead = _silence_file(
        temp_dir,
        lead_ms,
        sample_rate_hz,
        channels,
        silence_cache,
    )
    if lead:
        parts.append(lead)
    cursor_ms = float(lead_ms)

    for segment, source in zip(resolved_segments, voice_clips):
        placement, pan = _declared_position(segment, actors)
        acoustic_space = _declared_space(program, segment, actors)
        segment["resolved_placement"] = placement
        segment["resolved_pan"] = round(pan, 4)
        segment["resolved_acoustic_space"] = acoustic_space
        destination = temp_dir / f"voice-{segment['sequence']:03d}.wav"
        _prepare_voice_clip(
            source,
            destination,
            sample_rate_hz,
            channels,
            pan,
            acoustic_space,
        )
        parts.append(destination)
        clip_duration = probe_duration_seconds(destination)
        if clip_duration is None:
            raise RuntimeError(f"Could not determine voice duration for segment {segment['sequence']}")
        start_ms = cursor_ms
        end_ms = start_ms + (clip_duration * 1000.0)
        declared_pause = float(segment.get("pause_after_ms", 350))
        effective_pause = max(declared_pause, float(scene_spaces.get(segment["sequence"], 0)))
        timeline[segment["sequence"]] = {
            "start_ms": round(start_ms, 3),
            "end_ms": round(end_ms, 3),
            "pause_after_ms": round(effective_pause, 3),
            "acoustic_space": acoustic_space,
        }
        segment["resolved_pause_after_ms"] = round(effective_pause, 3)
        cursor_ms = end_ms + effective_pause
        pause = _silence_file(
            temp_dir,
            effective_pause,
            sample_rate_hz,
            channels,
            silence_cache,
        )
        if pause:
            parts.append(pause)

    output = temp_dir / "speech.wav"
    _concat_pcm(parts, output)
    return output, timeline


def render_master(speech_path, output_path, profile, ambience_path=None, ducking="speech"):
    loudnorm = (
        f"loudnorm=I={profile['loudness_lufs']}:"
        f"TP={profile['true_peak_db']}:LRA={profile['lra']}"
    )
    if ambience_path is None:
        run_ffmpeg([
            "-i", str(speech_path),
            "-af", loudnorm,
            "-c:a", profile["codec"],
            "-b:a", f"{profile['bitrate_kbps']}k",
            "-ar", str(profile["sample_rate_hz"]),
            "-ac", str(profile["channels"]),
            str(output_path),
        ])
        return

    if ducking == "speech":
        filter_complex = (
            "[1:a][0:a]sidechaincompress="
            "threshold=0.02:ratio=6:attack=20:release=350[bg];"
            f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,{loudnorm}[out]"
        )
    else:
        filter_complex = (
            f"[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,{loudnorm}[out]"
        )
    run_ffmpeg([
        "-i", str(speech_path),
        "-i", str(ambience_path),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", profile["codec"],
        "-b:a", f"{profile['bitrate_kbps']}k",
        "-ar", str(profile["sample_rate_hz"]),
        "-ac", str(profile["channels"]),
        str(output_path),
    ])
