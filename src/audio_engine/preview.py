from pathlib import Path

from .audio import probe_duration_seconds, run_ffmpeg
from .render import render_program


def _event_components(manifest):
    soundscape = manifest.get("mix", {}).get("soundscape") or {}
    return [
        item for item in soundscape.get("components", [])
        if item.get("role") == "event" and item.get("at_ms") is not None
    ]


def preview_program(
    program_path,
    output_root="output",
    voices_path=None,
    sounds_path=None,
    event=None,
    before_ms=2500,
    after_ms=2500,
    provider=None,
):
    if before_ms < 0 or after_ms < 0:
        raise ValueError("preview before/after durations must be >= 0")
    manifest = render_program(
        program_path,
        output_root,
        voices_path=voices_path,
        sounds_path=sounds_path,
        provider=provider,
    )
    output_root = Path(output_root)
    program_dir = output_root / manifest["id"]
    audio_path = program_dir / manifest["audio"]["file"]
    audio_duration = probe_duration_seconds(audio_path)
    if audio_duration is None:
        raise RuntimeError("Could not determine rendered program duration for preview")

    components = _event_components(manifest)
    if not components:
        raise ValueError("Program has no sound event to preview")
    if event is not None:
        if not 1 <= event <= len(components):
            raise ValueError(f"event must be between 1 and {len(components)}")
        selected = [(event, components[event - 1])]
    else:
        selected = list(enumerate(components, start=1))

    preview_dir = program_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    previews = []
    for index, component in selected:
        event_start_ms = float(component["at_ms"])
        event_duration_ms = float(component.get("play_duration_ms") or 0)
        start_ms = max(0.0, event_start_ms - float(before_ms))
        end_ms = min(
            audio_duration * 1000.0,
            event_start_ms + event_duration_ms + float(after_ms),
        )
        duration_ms = max(1.0, end_ms - start_ms)
        destination = preview_dir / f"event-{index:02d}.mp3"
        run_ffmpeg([
            "-ss", f"{start_ms / 1000.0:.3f}",
            "-i", str(audio_path),
            "-t", f"{duration_ms / 1000.0:.3f}",
            "-c:a", "libmp3lame",
            "-b:a", "128k",
            str(destination),
        ])
        previews.append({
            "event": index,
            "intent_role": component.get("intent_role"),
            "sound": component.get("sound"),
            "file": str(destination),
            "window_start_ms": round(start_ms, 1),
            "window_end_ms": round(end_ms, 1),
            "duration_ms": round(duration_ms, 1),
            "event_start_ms": round(event_start_ms, 1),
            "event_play_duration_ms": round(event_duration_ms, 1),
        })

    return {
        "program_id": manifest["id"],
        "render_cache_hit": manifest.get("cache_hit", False),
        "previews": previews,
    }
