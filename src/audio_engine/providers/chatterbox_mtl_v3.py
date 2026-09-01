import hashlib
import json
import math
import os
import random
import tempfile
from pathlib import Path

from ..audio import run_ffmpeg
from ..contract import ContractError, load_json, sha256_file
from ..provider_package import validate_provider_package

_PROVIDER_ID = "chatterbox-multilingual-v3"
_ALLOWED_PARAMETERS = {
    "language_id",
    "reference",
    "exaggeration",
    "cfg_weight",
    "temperature",
    "repetition_penalty",
    "min_p",
    "top_p",
}


class ChatterboxMultilingualV3Provider:
    """Fail-closed local Chatterbox Multilingual V3 Production adapter.

    Model and conditioning assets must already exist locally and match the
    provider package. The adapter never resolves floating model/provider state
    during synthesis.
    """

    name = _PROVIDER_ID
    processing = "local"
    edge_silence_normalization = False
    expressive_controls = (
        "provider_parameters.exaggeration",
        "provider_parameters.cfg_weight",
        "provider_parameters.temperature",
    )

    def __init__(self, package_path, workspace_root=".", model_dir=None, model_factory=None):
        self.package_path = Path(package_path)
        self.workspace_root = Path(workspace_root).resolve()
        self.package = validate_provider_package(
            load_json(self.package_path),
            package_path=self.package_path,
            workspace_root=self.workspace_root,
            verify_files=False,
        )
        provider = self.package["provider"]
        if provider["id"] != self.name:
            raise ContractError(
                f"Provider package id {provider['id']!r} does not match adapter {self.name!r}"
            )
        runtime = self.package["runtime"]
        self.device = runtime.get("device", "cpu")
        if self.device != "cpu":
            raise ContractError(
                "chatterbox-multilingual-v3 Production v1 is qualified for device='cpu' only"
            )

        raw_model_dir = model_dir or os.getenv("AUDIO_ENGINE_CHATTERBOX_MODEL_DIR")
        if not raw_model_dir:
            raise ContractError(
                "Chatterbox model_dir is required; implicit model download is forbidden"
            )
        self.model_dir = Path(raw_model_dir).resolve()
        self._verify_model_assets()
        self.references = self._verify_references()
        self.package_sha256 = sha256_file(self.package_path)
        self._model_factory = model_factory
        self._model = None

    def cache_identity(self):
        payload = {
            "provider": self.name,
            "adapter_code_sha256": sha256_file(Path(__file__)),
            "implementation_version": self.package["provider"]["implementation_version"],
            "package_sha256": self.package_sha256,
            "model_revision": self.package["model"]["revision"],
            "model_integrity": self.package["model"]["integrity"],
            "references": [
                {"id": item["id"], "sha256": item["sha256"]}
                for item in self.package.get("references", [])
            ],
            "device": self.device,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def _verify_model_assets(self):
        if not self.model_dir.is_dir():
            raise ContractError(f"Chatterbox model directory not found: {self.model_dir}")
        for item in self.package["model"]["integrity"]:
            filename = item["name"]
            if Path(filename).name != filename:
                raise ContractError(
                    f"Chatterbox model integrity name must be a filename: {filename!r}"
                )
            target = self.model_dir / filename
            if not target.is_file():
                raise ContractError(f"Chatterbox model asset missing: {filename}")
            actual = sha256_file(target)
            if actual != item["sha256"]:
                raise ContractError(
                    f"Chatterbox model asset SHA-256 mismatch for {filename}: "
                    f"{actual} != {item['sha256']}"
                )

    def _verify_references(self):
        references = {}
        for item in self.package.get("references", []):
            target = (self.workspace_root / item["path"]).resolve()
            try:
                target.relative_to(self.workspace_root)
            except ValueError as exc:
                raise ContractError(
                    f"Chatterbox reference escapes workspace: {item['path']}"
                ) from exc
            if not target.is_file():
                raise ContractError(f"Chatterbox reference missing: {item['path']}")
            actual = sha256_file(target)
            if actual != item["sha256"]:
                raise ContractError(
                    f"Chatterbox reference SHA-256 mismatch for {item['id']}: "
                    f"{actual} != {item['sha256']}"
                )
            references[item["id"]] = target
        return references

    def _load_model(self):
        if self._model is not None:
            return self._model
        if self._model_factory is not None:
            self._model = self._model_factory(self.model_dir, self.device)
            return self._model

        previous_offline = os.environ.get("HF_HUB_OFFLINE")
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            self._model = ChatterboxMultilingualTTS.from_local(
                self.model_dir,
                device=self.device,
                t3_model="v3",
            )
        except ImportError as exc:
            raise RuntimeError(
                "Chatterbox runtime is unavailable. Install the promoted runtime package; "
                "the engine will not fall back to Edge."
            ) from exc
        finally:
            if previous_offline is None:
                os.environ.pop("HF_HUB_OFFLINE", None)
            else:
                os.environ["HF_HUB_OFFLINE"] = previous_offline
        return self._model

    def _resolved_controls(self, segment):
        defaults = dict(self.package["synthesis"]["parameters"])
        overrides = segment.get("provider_parameters") or {}
        unknown = sorted((set(defaults) | set(overrides)) - _ALLOWED_PARAMETERS)
        if unknown:
            raise ContractError(
                f"Unsupported Chatterbox synthesis parameters: {', '.join(unknown)}"
            )
        controls = {**defaults, **overrides}
        reference_id = controls.pop("reference", None)
        if not reference_id:
            raise ContractError("Chatterbox provider parameter 'reference' is required")
        try:
            reference_path = self.references[reference_id]
        except KeyError as exc:
            raise ContractError(
                f"Unknown Chatterbox conditioning reference: {reference_id!r}"
            ) from exc

        language_id = controls.pop("language_id", None)
        if not isinstance(language_id, str) or not language_id:
            raise ContractError("Chatterbox provider parameter 'language_id' is required")

        seed = segment.get("provider_seed")
        if seed is None:
            sequence = int(segment.get("sequence") or 0)
            seed = int(self.package["synthesis"]["seed"]) + sequence
        return seed, language_id, reference_path, controls

    def synthesize(self, segment, path):
        seed, language_id, reference_path, controls = self._resolved_controls(segment)
        model = self._load_model()

        try:
            import numpy as np
            import torch
            import torchaudio as ta
        except ImportError as exc:
            raise RuntimeError(
                "Promoted Chatterbox runtime dependencies are incomplete"
            ) from exc

        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        wav = model.generate(
            segment["text"],
            language_id=language_id,
            audio_prompt_path=str(reference_path),
            **controls,
        )

        if wav.ndim == 1:
            wav = wav.unsqueeze(0)
        elif wav.ndim != 2:
            raise RuntimeError(f"Unexpected Chatterbox waveform rank: {wav.ndim}")
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)

        target_rate = 24000
        source_rate = int(model.sr)
        if source_rate != target_rate:
            wav = ta.functional.resample(wav, source_rate, target_rate)

        wav = wav.float()
        rms = torch.sqrt(torch.mean(wav.pow(2))).item()
        if rms > 0:
            current_dbfs = 20.0 * math.log10(rms)
            target_dbfs = float(
                (self.package["synthesis"].get("normalization") or {}).get(
                    "target_dbfs",
                    -20.0,
                )
            )
            gain_db = max(-8.0, min(8.0, target_dbfs - current_dbfs))
            wav = wav * (10.0 ** (gain_db / 20.0))
        wav = torch.clamp(wav, -1.0, 1.0)

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temp_value:
            normalized_wav = Path(temp_value) / "normalized.wav"
            ta.save(str(normalized_wav), wav.cpu(), target_rate)
            run_ffmpeg([
                "-i", str(normalized_wav),
                "-map_metadata", "-1",
                "-ac", "1",
                "-c:a", "libmp3lame",
                "-b:a", "96k",
                str(path),
            ])
