"""Optional Chatterbox provider for Voice Casting Lab experiments only.

This module intentionally imports Chatterbox/Torch lazily so the production
Audio Engine runtime keeps its small dependency surface. It is not wired into
public render contracts or production provider selection.
"""

from __future__ import annotations

from pathlib import Path


class ChatterboxLabProvider:
    name = "chatterbox-v3-lab"
    processing = "local-optional"
    expressive_controls = ("exaggeration", "cfg_weight", "temperature", "seed")

    def __init__(self, *, device: str = "cpu", t3_model: str = "v3"):
        try:
            import torch
            import torchaudio
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        except ImportError as exc:
            raise RuntimeError(
                "Chatterbox lab provider requires the optional 'chatterbox-tts' "
                "environment; it is intentionally not an audio-engine dependency."
            ) from exc

        self._torch = torch
        self._torchaudio = torchaudio
        self.device = device
        self.t3_model = t3_model
        if device == "cpu":
            try:
                torch.set_num_threads(2)
            except Exception:
                pass
        self.model = ChatterboxMultilingualTTS.from_pretrained(
            device=device,
            t3_model=t3_model,
        )

    def synthesize(self, segment: dict, path) -> None:
        audio_prompt_path = segment.get("audio_prompt_path")
        if not audio_prompt_path:
            raise ValueError("Chatterbox lab synthesis requires audio_prompt_path")
        prompt = Path(audio_prompt_path)
        if not prompt.exists():
            raise FileNotFoundError(prompt)

        seed = int(segment.get("seed", 20260824))
        self._torch.manual_seed(seed)

        wav = self.model.generate(
            str(segment["text"]),
            language_id=str(segment.get("language_id", "fr")),
            audio_prompt_path=str(prompt),
            exaggeration=float(segment.get("exaggeration", 0.5)),
            cfg_weight=float(segment.get("cfg_weight", 0.5)),
            temperature=float(segment.get("temperature", 0.8)),
        )
        self._torchaudio.save(str(path), wav, self.model.sr)
