"""Azure Speech provider used only by the Voice Casting Lab.

This module deliberately stays outside the production render path until blind
listening evidence justifies promotion.  It uses the Azure Speech REST endpoint
directly to keep dependencies minimal.
"""

from __future__ import annotations

import html
import os
import urllib.error
import urllib.request


class AzureSpeechLabProvider:
    name = "azure-speech-lab"
    processing = "remote"
    expressive_controls = ("style", "styledegree")

    def __init__(self, *, key: str | None = None, region: str | None = None):
        self.key = key or os.environ.get("AZURE_SPEECH_KEY")
        self.region = region or os.environ.get("AZURE_SPEECH_REGION")
        if not self.key or not self.region:
            raise RuntimeError(
                "Azure Speech lab provider requires AZURE_SPEECH_KEY and "
                "AZURE_SPEECH_REGION."
            )

    def _ssml(self, segment: dict) -> str:
        text = html.escape(str(segment["text"]), quote=False)
        voice = html.escape(str(segment["voice"]), quote=True)
        locale = html.escape(str(segment.get("language_locale", "fr-FR")), quote=True)
        style = segment.get("style")
        styledegree = segment.get("styledegree")

        body = text
        if style:
            style_attr = html.escape(str(style), quote=True)
            degree_attr = ""
            if styledegree is not None:
                degree = float(styledegree)
                if not 0.01 <= degree <= 2.0:
                    raise ValueError("styledegree must be between 0.01 and 2.0")
                degree_attr = f" styledegree='{degree:g}'"
            body = f"<mstts:express-as style='{style_attr}'{degree_attr}>{text}</mstts:express-as>"

        return (
            "<speak version='1.0' "
            "xmlns='http://www.w3.org/2001/10/synthesis' "
            "xmlns:mstts='http://www.w3.org/2001/mstts' "
            f"xml:lang='{locale}'>"
            f"<voice name='{voice}'>{body}</voice>"
            "</speak>"
        )

    def synthesize(self, segment: dict, path) -> None:
        endpoint = (
            f"https://{self.region}.tts.speech.microsoft.com/"
            "cognitiveservices/v1"
        )
        request = urllib.request.Request(
            endpoint,
            data=self._ssml(segment).encode("utf-8"),
            method="POST",
            headers={
                "Ocp-Apim-Subscription-Key": self.key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                "User-Agent": "recit-audio-engine-voice-lab",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Azure Speech synthesis failed with HTTP {exc.code}: {detail}"
            ) from exc
        path.write_bytes(payload)
