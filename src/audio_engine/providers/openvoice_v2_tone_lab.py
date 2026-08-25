"""Lab-only OpenVoice V2 tone-color converter.

This provider deliberately separates expressive source audio from target speaker
identity. It never performs TTS itself: a pre-rendered expressive French donor is
converted toward a frozen target speaker embedding.
"""
from __future__ import annotations

from pathlib import Path


class OpenVoiceV2ToneLabProvider:
    """Thin adapter around the pinned OpenVoice V2 tone-color converter."""

    identity_mode = "openvoice-v2-tone-color"

    def __init__(self, *, config_path: Path, checkpoint_path: Path, device: str = "cpu", tau: float = 0.3):
        config_path = Path(config_path)
        checkpoint_path = Path(checkpoint_path)
        if not config_path.is_file():
            raise FileNotFoundError(config_path)
        if not checkpoint_path.is_file():
            raise FileNotFoundError(checkpoint_path)
        if not (0.0 <= float(tau) <= 1.0):
            raise ValueError("tau must be between 0 and 1")

        # OpenVoice's current ToneColorConverter constructor forwards all kwargs
        # to its base class before inspecting enable_watermark. A tiny subclass
        # avoids loading wavmark while leaving conversion logic untouched.
        from openvoice.api import OpenVoiceBaseClass, ToneColorConverter

        class _NoWatermarkToneColorConverter(ToneColorConverter):
            def __init__(self, config, *, device):
                OpenVoiceBaseClass.__init__(self, str(config), device=device)
                self.watermark_model = None
                self.version = getattr(self.hps, "_version_", "v1")

        self.converter = _NoWatermarkToneColorConverter(config_path, device=device)
        self.converter.load_ckpt(str(checkpoint_path))
        self.device = device
        self.tau = float(tau)

    def extract_embedding(self, audio_path: Path):
        audio_path = Path(audio_path)
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        return self.converter.extract_se(str(audio_path))

    def convert(self, source_audio: Path, target_embedding, output_path: Path):
        source_audio = Path(source_audio)
        output_path = Path(output_path)
        if not source_audio.is_file():
            raise FileNotFoundError(source_audio)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        source_embedding = self.extract_embedding(source_audio)
        self.converter.convert(
            audio_src_path=str(source_audio),
            src_se=source_embedding,
            tgt_se=target_embedding,
            output_path=str(output_path),
            tau=self.tau,
            message="",
        )
        if not output_path.is_file() or output_path.stat().st_size <= 44:
            raise RuntimeError(f"OpenVoice did not create a valid WAV payload: {output_path}")
        return output_path
