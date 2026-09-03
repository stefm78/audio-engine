import asyncio
import re
import edge_tts

_PATCHED = False


def _locale_from_voice(voice):
    match = re.match(r"^([a-z]{2,3}-[A-Z]{2})-", voice or "")
    return match.group(1) if match else None


def _speech_locale(config):
    """Resolve the root SSML locale from explicit transport or voice identity."""
    explicit = getattr(config, "_audio_engine_language_locale", None)
    return explicit or _locale_from_voice(getattr(config, "voice", None))


def patch_ssml_locale():
    global _PATCHED
    if _PATCHED:
        return
    try:
        import edge_tts.communicate as edge_communicate
        original = getattr(edge_communicate, "mkssml", None)
        if original:
            def localized(config, escaped_text):
                ssml = original(config, escaped_text)
                locale = _speech_locale(config)
                if locale:
                    ssml = re.sub(
                        r"xml:lang=(['\"])en-US\1",
                        f"xml:lang='{locale}'",
                        ssml,
                        count=1,
                    )
                return ssml
            edge_communicate.mkssml = localized
    finally:
        _PATCHED = True


class EdgeProvider:
    name = "edge"
    processing = "remote"
    expressive_controls = ("rate", "pitch", "volume")

    # Cache identity is a synthesis contract, not a hash of incidental adapter code.
    # Bump this value only when successful Edge audio semantics change.
    cache_identity = (
        "edge-tts-7.2.8|ssml-locale-v1|"
        "voice-synthesis-v2-edge-silence-normalized"
    )

    # Historical identities whose successful synthesis path and normalized clip
    # bytes are semantically compatible with cache_identity above. These are
    # opt-in migration aliases only; the current identity remains authoritative.
    cache_compatible_identities = (
        "dfc727bb784bcb630165714b90a01266d524a1c4aa3485b6c6d106e7a1f8e6a6",
        "7c58d0ba7ff7c0bd2b8a14f28a342274407e893f92d1eccdbb0daca90be2b380",
    )

    def __init__(self):
        patch_ssml_locale()

    async def list_voices_async(self, locale_prefix=None):
        voices = await edge_tts.list_voices()
        normalized = []
        for item in voices:
            short_name = item.get("ShortName") or item.get("Name")
            locale = item.get("Locale") or _locale_from_voice(short_name)
            if locale_prefix and not str(locale or "").startswith(locale_prefix):
                continue
            normalized.append({
                "voice": short_name,
                "locale": locale,
                "gender": str(item.get("Gender") or "").lower() or None,
                "friendly_name": item.get("FriendlyName"),
            })
        return sorted(normalized, key=lambda item: (item.get("locale") or "", item.get("voice") or ""))

    def list_voices(self, locale_prefix=None):
        return asyncio.run(self.list_voices_async(locale_prefix=locale_prefix))

    async def synthesize_async(self, segment, path):
        last_error = None
        for attempt in range(2):
            try:
                communicator = edge_tts.Communicate(
                    segment["text"],
                    segment["voice"],
                    rate=segment.get("rate", "+0%"),
                    pitch=segment.get("pitch", "+0Hz"),
                    volume=segment.get("volume", "+0%"),
                )
                language_locale = segment.get("language_locale")
                if language_locale:
                    communicator._audio_engine_language_locale = language_locale
                    tts_config = getattr(communicator, "tts_config", None)
                    if tts_config is not None:
                        tts_config._audio_engine_language_locale = language_locale
                await communicator.save(str(path))
                return
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(1.5)
        if isinstance(last_error, edge_tts.exceptions.NoAudioReceived):
            try:
                voices = await edge_tts.list_voices()
                available = {
                    item.get("ShortName") or item.get("Name")
                    for item in voices
                }
            except Exception:
                available = None
            if available is not None and segment["voice"] not in available:
                raise RuntimeError(
                    f"Edge voice is unavailable in the current provider catalog: "
                    f"{segment['voice']!r}. No fallback is allowed."
                ) from last_error
        raise last_error

    def synthesize(self, segment, path):
        asyncio.run(self.synthesize_async(segment, path))
