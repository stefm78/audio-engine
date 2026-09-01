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

def measure_encoded_true_peak_dbtp(path):
    completed = subprocess.run(
        [
            ffmpeg_exe(),
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "loudnorm=I=-16:TP=-2.5:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "true-peak analysis failed")
    values = re.findall(r'"input_tp"\s*:\s*"([^"]+)"', completed.stderr)
    if not values:
        raise RuntimeError("Could not parse encoded true peak")
    return float(values[-1])


def encode_concat(parts, output_path, profile):
    concat_file = Path(output_path).with_suffix(".concat.txt")
    concat_file.write_text(
        "".join(f"file '{Path(part).resolve()}'\n" for part in parts),
        encoding="utf-8",
    )
    requested_peak = float(profile["true_peak_db"])
    filter_peak = requested_peak
    measured_peak = None
    attempts = 0
    try:
        for attempts in range(1, 4):
            filter_value = (
                f"loudnorm=I={profile['loudness_lufs']}:"
                f"TP={filter_peak:.3f}:LRA={profile['lra']}"
            )
            run_ffmpeg([
                "-f", "concat", "-safe", "0", "-i", str(concat_file),
                "-af", filter_value,
                "-c:a", profile["codec"],
                "-b:a", f"{profile['bitrate_kbps']}k",
                "-ar", str(profile["sample_rate_hz"]),
                "-ac", str(profile["channels"]),
                str(output_path),
            ])
            measured_peak = measure_encoded_true_peak_dbtp(output_path)
            if measured_peak <= requested_peak + 0.5:
                break
            excess = measured_peak - requested_peak
            filter_peak -= excess + 0.5
        else:
            raise RuntimeError(
                "Encoded true peak remains above bounded assembly target after "
                f"3 attempts: {measured_peak:.3f} dBTP > {requested_peak + 0.5:.3f} dBTP"
            )
    finally:
        concat_file.unlink(missing_ok=True)

    return {
        "requested_true_peak_dbtp": requested_peak,
        "effective_loudnorm_true_peak_dbtp": round(filter_peak, 3),
        "measured_encoded_true_peak_dbtp": round(float(measured_peak), 3),
        "attempts": attempts,
        "acceptance_ceiling_dbtp": round(requested_peak + 0.5, 3),
    }

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
