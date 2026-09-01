"""Experimental Qwen3 Base style-transplant provider for Voice Casting Lab only.

This is preserved from the historical PR #70 implementation so the P6 cell can
reuse exactly the same architecture for the previously PASSed contained-sadness
subcase. Lab only. No Production promotion.
"""
from __future__ import annotations

import random
from pathlib import Path


class Qwen3StyleTransplantLabProvider:
    name = "qwen3-style-transplant-lab"
    processing = "local-optional"
    identity_mode = "frozen-xvector-plus-foreign-icl-style"

    def __init__(self, *, model_dir, device: str = "cpu"):
        try:
            import numpy as np
            import soundfile as sf
            import torch
            from qwen_tts import Qwen3TTSModel
            from transformers.utils import logging as transformers_logging
        except ImportError as exc:
            raise RuntimeError(
                "Qwen3 style-transplant lab provider requires the isolated qwen-tts environment"
            ) from exc
        model_path = Path(model_dir)
        if not model_path.exists():
            raise FileNotFoundError(model_path)
        self._np, self._sf, self._torch = np, sf, torch
        self._transformers_logging = transformers_logging
        self.device = device
        self.model = Qwen3TTSModel.from_pretrained(
            str(model_path),
            device_map=device,
            dtype=torch.bfloat16,
            attn_implementation="eager",
        )

    def build_identity_embedding(self, reference_wav_path):
        reference = Path(reference_wav_path)
        if not reference.is_file():
            raise FileNotFoundError(reference)
        item = self.model.create_voice_clone_prompt(
            ref_audio=str(reference),
            ref_text=None,
            x_vector_only_mode=True,
        )[0]
        return item.ref_spk_embedding

    def build_xvector_prompt(self, reference_wav_path):
        reference = Path(reference_wav_path)
        if not reference.is_file():
            raise FileNotFoundError(reference)
        return self.model.create_voice_clone_prompt(
            ref_audio=str(reference),
            ref_text=None,
            x_vector_only_mode=True,
        )[0]

    def build_style_prompt(self, identity_embedding, style_wav_path, style_text: str):
        style_wav = Path(style_wav_path)
        if not style_wav.is_file():
            raise FileNotFoundError(style_wav)
        style_text = str(style_text or "").strip()
        if not style_text:
            raise ValueError("style donor transcript is required")
        item = self.model.create_voice_clone_prompt(
            ref_audio=str(style_wav),
            ref_text=style_text,
            x_vector_only_mode=False,
        )[0]
        item.ref_spk_embedding = identity_embedding
        item.x_vector_only_mode = False
        item.icl_mode = True
        return item

    def synthesize(self, segment: dict, path, *, voice_clone_prompt) -> None:
        text = str(segment.get("text") or "").strip()
        if not text:
            raise ValueError("Qwen3 style transplant requires text")
        seed = int(segment.get("seed", 20260825))
        random.seed(seed)
        self._np.random.seed(seed % (2**32 - 1))
        self._torch.manual_seed(seed)

        log = self._transformers_logging
        was_enabled = True
        checker = getattr(log, "is_progress_bar_enabled", None)
        if callable(checker):
            was_enabled = bool(checker())
        disable = getattr(log, "disable_progress_bar", None)
        enable = getattr(log, "enable_progress_bar", None)
        if callable(disable):
            disable()
        try:
            wavs, sr = self.model.generate_voice_clone(
                text=text,
                language=segment.get("language", "French"),
                voice_clone_prompt=[voice_clone_prompt],
                non_streaming_mode=True,
                do_sample=True,
                max_new_tokens=int(segment.get("max_new_tokens", 768)),
            )
        finally:
            if was_enabled and callable(enable):
                enable()

        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._sf.write(str(output), wavs[0], sr)
