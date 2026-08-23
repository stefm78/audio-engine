PROFILES = {
    "speech": {
        "codec": "libmp3lame",
        "container": "mp3",
        "bitrate_kbps": 80,
        "sample_rate_hz": 24000,
        "channels": 1,
        "loudness_lufs": -16,
        "true_peak_db": -1.5,
        "lra": 11,
    },
    "speech-high": {
        "codec": "libmp3lame",
        "container": "mp3",
        "bitrate_kbps": 96,
        "sample_rate_hz": 24000,
        "channels": 1,
        "loudness_lufs": -16,
        "true_peak_db": -1.5,
        "lra": 11,
    },
}

def get_profile(name: str):
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown profile: {name}. Available: {', '.join(PROFILES)}") from exc
