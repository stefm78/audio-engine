import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

def ffmpeg_exe():
    return imageio_ffmpeg.get_ffmpeg_exe()

def run_ffmpeg(args, capture=False):
    command = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args]
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )

def silence_file(directory, duration_ms, cache):
    duration_ms = int(duration_ms)
    if duration_ms <= 0:
        return None
    if duration_ms in cache:
        return cache[duration_ms]
    path = Path(directory) / f"silence-{duration_ms}ms.mp3"
    run_ffmpeg([
        "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
        "-t", f"{duration_ms / 1000:.3f}",
        "-c:a", "libmp3lame",
        "-b:a", "64k",
        str(path),
    ])
    cache[duration_ms] = path
    return path

def encode_concat(parts, output_path, profile):
    concat_file = Path(output_path).with_suffix(".concat.txt")
    concat_file.write_text(
        "".join(f"file '{Path(part).resolve()}'\n" for part in parts),
        encoding="utf-8",
    )
    filter_value = (
        f"loudnorm=I={profile['loudness_lufs']}:"
        f"TP={profile['true_peak_db']}:LRA={profile['lra']}"
    )
    try:
        run_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-af", filter_value,
            "-c:a", profile["codec"],
            "-b:a", f"{profile['bitrate_kbps']}k",
            "-ar", str(profile["sample_rate_hz"]),
            "-ac", str(profile["channels"]),
            str(output_path),
        ])
    finally:
        concat_file.unlink(missing_ok=True)

def probe_duration_seconds(path):
    result = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3)
