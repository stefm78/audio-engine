import hashlib
import json
import os
import random
import tempfile
from pathlib import Path

from ..audio import run_ffmpeg
from ..contract import ContractError, load_json, sha256_file
from ..provider_package import validate_provider_package
from .local_runtime import (
    verify_model_assets,
    verify_references,
    verify_system_runtime,
)

_PROVIDER_ID = "voxcpm2"
_ALLOWED_PARAMETERS = {
    "reference",
    "control",
    "cfg_value",
    "inference_timesteps",
    "normalize_model_output",
    "denoise",
    "retry_badcase",
}


class VoxCPM2Provider:
    """Fail-closed local VoxCPM2 Production adapter.

    The adapter consumes only an already-hydrated immutable model snapshot and
    immutable conditioning references. It never downloads model/reference data
    during synthesis and never falls back to another provider.
    """

    name = _PROVIDER_ID
    processing = "local"
    edge_silence_normalization = False
    expressive_controls = (
        "provider_parameters.control",
        "provider_parameters.cfg_value",
        "provider_parameters.inference_timesteps",
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
            raise ContractError("voxcpm2 Production v1 is qualified for device='cpu' only")
        self.system_runtime = verify_system_runtime(runtime, "VoxCPM2")

        raw_model_dir = model_dir or os.getenv("AUDIO_ENGINE_VOXCPM2_MODEL_DIR")
        if not raw_model_dir:
            raise ContractError(
                "VoxCPM2 model_dir is required; implicit model download is forbidden"
            )
        self.model_dir = Path(raw_model_dir).resolve()
        verify_model_assets(self.package, self.model_dir, "VoxCPM2")
        self.references = verify_references(
            self.package,
            self.workspace_root,
            "VoxCPM2",
        )
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
            "system_runtime": self.system_runtime,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def _load_model(self):
        if self._model is not None:
            return self._model
        if self._model_factory is not None:
            self._model = self._model_factory(self.model_dir, self.device)
            return self._model

        previous_offline = os.environ.get("HF_HUB_OFFLINE")
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            from voxcpm import VoxCPM
            self._model = VoxCPM.from_pretrained(
                str(self.model_dir),
                load_denoiser=False,
                optimize=False,
                device=self.device,
            )
        except ImportError as exc:
            raise RuntimeError(
                "VoxCPM2 runtime is unavailable. Install the promoted runtime package; "
                "the engine will not fall back."
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
                f"Unsupported VoxCPM2 synthesis parameters: {', '.join(unknown)}"
            )
        controls = {**defaults, **overrides}

        reference_id = controls.pop("reference", None)
        if not reference_id:
            raise ContractError("VoxCPM2 provider parameter 'reference' is required")
        try:
            reference_path = self.references[reference_id]
        except KeyError as exc:
            raise ContractError(
                f"Unknown VoxCPM2 conditioning reference: {reference_id!r}"
            ) from exc

        control = controls.pop("control", None)
        if not isinstance(control, str) or not control.strip():
            raise ContractError("VoxCPM2 provider parameter 'control' is required")

        cfg_value = controls.pop("cfg_value", None)
        inference_timesteps = controls.pop("inference_timesteps", None)
        if not isinstance(cfg_value, (int, float)) or isinstance(cfg_value, bool):
            raise ContractError("VoxCPM2 cfg_value must be numeric")
        if (
            not isinstance(inference_timesteps, int)
            or isinstance(inference_timesteps, bool)
            or inference_timesteps <= 0
        ):
            raise ContractError("VoxCPM2 inference_timesteps must be a positive integer")

        for key in ("normalize_model_output", "denoise", "retry_badcase"):
            if not isinstance(controls.get(key), bool):
                raise ContractError(f"VoxCPM2 {key} must be boolean")

        seed = segment.get("provider_seed")
        if seed is None:
            sequence = int(segment.get("sequence") or 0)
            seed = int(self.package["synthesis"]["seed"]) + sequence

        return seed, reference_path, control, cfg_value, inference_timesteps, controls

    def synthesize(self, segment, path):
        (
            seed,
            reference_path,
            control,
            cfg_value,
            inference_timesteps,
            controls,
        ) = self._resolved_controls(segment)
        model = self._load_model()

        try:
            import numpy as np
            import soundfile as sf
            import torch
            from pydub import AudioSegment
        except ImportError as exc:
            raise RuntimeError("Promoted VoxCPM2 runtime dependencies are incomplete") from exc

        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        final_text = f"({control}){segment['text']}"
        wav = model.generate(
            text=final_text,
            reference_wav_path=str(reference_path),
            cfg_value=float(cfg_value),
            inference_timesteps=int(inference_timesteps),
            normalize=controls["normalize_model_output"],
            denoise=controls["denoise"],
            retry_badcase=controls["retry_badcase"],
            seed=int(seed),
        )

        sample_rate = int(model.tts_model.sample_rate)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temp_value:
            temp = Path(temp_value)
            raw_wav = temp / "raw.wav"
            normalized_wav = temp / "normalized.wav"
            sf.write(raw_wav, wav, sample_rate)

            audio = (
                AudioSegment.from_file(raw_wav, format="wav")
                .set_frame_rate(24000)
                .set_channels(1)
            )
            if audio.rms > 0:
                target_dbfs = float(
                    (self.package["synthesis"].get("normalization") or {}).get(
                        "target_dbfs",
                        -20.0,
                    )
                )
                gain = max(-8.0, min(8.0, target_dbfs - audio.dBFS))
                audio = audio.apply_gain(gain)
            audio.export(normalized_wav, format="wav")

            run_ffmpeg([
                "-i", str(normalized_wav),
                "-map_metadata", "-1",
                "-ac", "1",
                "-c:a", "libmp3lame",
                "-b:a", "96k",
                str(path),
            ])
