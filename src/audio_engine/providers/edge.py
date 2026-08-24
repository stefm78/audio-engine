import asyncio
import re
import edge_tts

_PATCHED = False


def _locale_from_voice(voice):
    match = re.match(r"^([a-z]{2,3}-[A-Z]{2})-", voice or "")
    return match.group(1) if match else None


def patch_ssml_locale():
    global _PATCHED
    if _PATCHED:
        return
    try:
        import edge_tts.communicate as edge_communicate
        original = getattr(edge_communicate, "mkssml", None)
        if original:
            def localized(communicate, escaped_text):
                ssml = original(communicate, escaped_text)
                locale = _locale_from_voice(getattr(communicate, "voice", None))
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
                await communicator.save(str(path))
                return
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    await asyncio.sleep(1.5)
        raise last_error

    def synthesize(self, segment, path):
        asyncio.run(self.synthesize_async(segment, path))
