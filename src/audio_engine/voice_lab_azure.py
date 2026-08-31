"""Azure Speech expressive synthesis helper for Voice Casting Lab only.

This module is intentionally not wired into Production rendering.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

_REGION_RE = re.compile(r"^[a-z0-9-]+$")
DEFAULT_OUTPUT_FORMAT = "audio-24khz-96kbitrate-mono-mp3"


class AzureSpeechLabError(RuntimeError):
    pass


def _attr(value: str) -> str:
    return html.escape(str(value), quote=True)


def build_ssml(
    text: str,
    voice: str,
    *,
    locale: str = "fr-FR",
    style: str | None = None,
    styledegree: float | None = None,
    rate: str | None = None,
    pitch: str | None = None,
    volume: str | None = None,
) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text is required")
    if not isinstance(voice, str) or not voice.strip():
        raise ValueError("voice is required")
    if styledegree is not None:
        if style is None:
            raise ValueError("styledegree requires style")
        styledegree = float(styledegree)
        if not 0.01 <= styledegree <= 2.0:
            raise ValueError("styledegree must be between 0.01 and 2.0")

    body = html.escape(text)
    prosody_attrs = []
    if rate is not None:
        prosody_attrs.append(f'rate="{_attr(rate)}"')
    if pitch is not None:
        prosody_attrs.append(f'pitch="{_attr(pitch)}"')
    if volume is not None:
        prosody_attrs.append(f'volume="{_attr(volume)}"')
    if prosody_attrs:
        body = f"<prosody {' '.join(prosody_attrs)}>{body}</prosody>"

    if style is not None:
        attrs = [f'style="{_attr(style)}"']
        if styledegree is not None:
            attrs.append(f'styledegree="{styledegree:g}"')
        body = f"<mstts:express-as {' '.join(attrs)}>{body}</mstts:express-as>"

    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{_attr(locale)}">'
        f'<voice name="{_attr(voice)}">{body}</voice></speak>'
    )


def request_manifest(
    text: str,
    voice: str,
    region: str,
    *,
    locale: str = "fr-FR",
    style: str | None = None,
    styledegree: float | None = None,
    rate: str | None = None,
    pitch: str | None = None,
    volume: str | None = None,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
) -> dict:
    ssml = build_ssml(
        text,
        voice,
        locale=locale,
        style=style,
        styledegree=styledegree,
        rate=rate,
        pitch=pitch,
        volume=volume,
    )
    return {
        "provider": "azure-speech-lab",
        "processing": "remote",
        "region": region,
        "voice": voice,
        "locale": locale,
        "style": style,
        "styledegree": styledegree,
        "rate": rate,
        "pitch": pitch,
        "volume": volume,
        "output_format": output_format,
        "text_chars": len(text),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "ssml_sha256": hashlib.sha256(ssml.encode("utf-8")).hexdigest(),
    }


class AzureSpeechLabClient:
    def __init__(self, key: str, region: str, *, opener=urlopen):
        if not key:
            raise AzureSpeechLabError("AZURE_SPEECH_KEY is required")
        if not region:
            raise AzureSpeechLabError("AZURE_SPEECH_REGION is required")
        region = region.strip().lower()
        if not _REGION_RE.fullmatch(region):
            raise AzureSpeechLabError("AZURE_SPEECH_REGION is invalid")
        self._key = key
        self.region = region
        self._opener = opener

    @classmethod
    def from_env(cls, *, opener=urlopen):
        return cls(
            os.environ.get("AZURE_SPEECH_KEY", ""),
            os.environ.get("AZURE_SPEECH_REGION", ""),
            opener=opener,
        )

    @property
    def endpoint(self) -> str:
        return f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"

    def synthesize(
        self,
        text: str,
        voice: str,
        path,
        *,
        locale: str = "fr-FR",
        style: str | None = None,
        styledegree: float | None = None,
        rate: str | None = None,
        pitch: str | None = None,
        volume: str | None = None,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ) -> dict:
        ssml = build_ssml(
            text,
            voice,
            locale=locale,
            style=style,
            styledegree=styledegree,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        request = Request(
            self.endpoint,
            data=ssml.encode("utf-8"),
            method="POST",
            headers={
                "Ocp-Apim-Subscription-Key": self._key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": output_format,
                "User-Agent": "recit-audio-engine-voice-lab",
            },
        )
        try:
            with self._opener(request, timeout=90) as response:
                payload = response.read()
        except Exception as exc:
            raise AzureSpeechLabError(f"Azure Speech synthesis failed: {exc}") from exc
        if not payload:
            raise AzureSpeechLabError("Azure Speech returned empty audio")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        manifest = request_manifest(
            text,
            voice,
            self.region,
            locale=locale,
            style=style,
            styledegree=styledegree,
            rate=rate,
            pitch=pitch,
            volume=volume,
            output_format=output_format,
        )
        manifest["audio_bytes"] = len(payload)
        manifest["audio_sha256"] = hashlib.sha256(payload).hexdigest()
        return manifest


def write_manifest(path, manifest: dict) -> None:
    Path(path).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
