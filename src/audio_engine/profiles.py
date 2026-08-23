LOSSY_TRUE_PEAK_DB = -2.5


PROFILES = {
    "speech": {
        "codec": "libmp3lame",
        "container": "mp3",
        "bitrate_kbps": 80,
        "sample_rate_hz": 24000,
        "channels": 1,
        "loudness_lufs": -16,
        "true_peak_db": LOSSY_TRUE_PEAK_DB,
        "lra": 11,
    },
    "speech-high": {
        "codec": "libmp3lame",
        "container": "mp3",
        "bitrate_kbps": 96,
        "sample_rate_hz": 24000,
        "channels": 1,
        "loudness_lufs": -16,
        "true_peak_db": LOSSY_TRUE_PEAK_DB,
        "lra": 11,
    },
}


def get_profile(name: str, stereo: bool = False):
    try:
        profile = dict(PROFILES[name])
    except KeyError as exc:
        raise ValueError(f"Unknown profile: {name}. Available: {', '.join(PROFILES)}") from exc
    if stereo:
        profile["channels"] = 2
        profile["bitrate_kbps"] = max(profile["bitrate_kbps"], 96)
    return profile
