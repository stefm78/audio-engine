from __future__ import annotations

import hashlib
import importlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from .contract import ContractError

_REQUIRED_CHECKPOINT_ROLES = (
    "decoder",
    "pitch",
    "encoder",
    "flow",
    "mel2wav",
    "speaker",
    "tokenizer",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_beltout_checkpoint_manifest(path):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"BeltOut checkpoint manifest is invalid: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError("BeltOut checkpoint manifest must be an object")
    if set(data) != set(_REQUIRED_CHECKPOINT_ROLES):
        raise ContractError(
            "BeltOut checkpoint manifest must contain exactly: "
            + ", ".join(_REQUIRED_CHECKPOINT_ROLES)
        )
    for role in _REQUIRED_CHECKPOINT_ROLES:
        item = data[role]
        if not isinstance(item, dict):
            raise ContractError(f"BeltOut checkpoint role {role!r} must be an object")
        filename = item.get("file")
        digest = item.get("sha256")
        if (
            not isinstance(filename, str)
            or not filename
            or Path(filename).is_absolute()
            or ".." in Path(filename).parts
        ):
            raise ContractError(f"BeltOut checkpoint role {role!r} has unsafe file")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ContractError(
                f"BeltOut checkpoint role {role!r} needs lowercase SHA-256"
            )
    return data


def _verify_git_revision(source_root: Path, expected_revision: str):
    if not _GIT_SHA_RE.fullmatch(str(expected_revision or "")):
        raise ContractError("BeltOut expected revision must be an exact 40-char Git SHA")
    if not source_root.is_dir():
        raise ContractError(f"BeltOut source directory not found: {source_root}")
    try:
        probe = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ContractError(f"Unable to inspect BeltOut Git revision: {exc}") from exc
    actual = (probe.stdout or "").strip()
    if probe.returncode != 0 or actual != expected_revision:
        raise ContractError(
            f"BeltOut source revision mismatch: {actual or 'unavailable'} != {expected_revision}"
        )
    return actual


def verify_beltout_conversion_inputs(
    *,
    source,
    source_sha256,
    target_reference,
    target_reference_sha256,
    beltout_source,
    expected_revision,
    checkpoint_dir,
    checkpoint_manifest,
    output,
    report,
    seed,
    n_timesteps,
):
    source = Path(source).resolve()
    target_reference = Path(target_reference).resolve()
    beltout_source = Path(beltout_source).resolve()
    checkpoint_dir = Path(checkpoint_dir).resolve()
    output = Path(output).resolve()
    report = Path(report).resolve()

    if output.exists() or report.exists():
        raise ContractError(
            "BeltOut one-shot output/report already exists; retry or best-of-N is forbidden"
        )
    if output == report:
        raise ContractError("BeltOut output and report paths must differ")
    if not source.is_file():
        raise ContractError(f"BeltOut source performance not found: {source}")
    if not target_reference.is_file():
        raise ContractError(f"BeltOut target reference not found: {target_reference}")
    if not checkpoint_dir.is_dir():
        raise ContractError(f"BeltOut checkpoint directory not found: {checkpoint_dir}")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ContractError("BeltOut seed must be a non-negative integer")
    if not isinstance(n_timesteps, int) or isinstance(n_timesteps, bool) or n_timesteps <= 0:
        raise ContractError("BeltOut n_timesteps must be a positive integer")
    if not _SHA256_RE.fullmatch(str(source_sha256 or "")):
        raise ContractError("BeltOut source SHA-256 must be exact lowercase hex")
    if not _SHA256_RE.fullmatch(str(target_reference_sha256 or "")):
        raise ContractError("BeltOut target reference SHA-256 must be exact lowercase hex")
    actual_source_sha = _sha256(source)
    if actual_source_sha != source_sha256:
        raise ContractError(
            f"BeltOut source SHA-256 mismatch: {actual_source_sha} != {source_sha256}"
        )
    actual_target_sha = _sha256(target_reference)
    if actual_target_sha != target_reference_sha256:
        raise ContractError(
            f"BeltOut target reference SHA-256 mismatch: {actual_target_sha} != {target_reference_sha256}"
        )

    revision = _verify_git_revision(beltout_source, expected_revision)
    manifest = load_beltout_checkpoint_manifest(checkpoint_manifest)
    verified_checkpoints = {}
    for role in _REQUIRED_CHECKPOINT_ROLES:
        item = manifest[role]
        target = (checkpoint_dir / item["file"]).resolve()
        try:
            target.relative_to(checkpoint_dir)
        except ValueError as exc:
            raise ContractError(
                f"BeltOut checkpoint escapes checkpoint directory: {item['file']}"
            ) from exc
        if not target.is_file():
            raise ContractError(f"BeltOut checkpoint missing: {item['file']}")
        actual = _sha256(target)
        if actual != item["sha256"]:
            raise ContractError(
                f"BeltOut checkpoint SHA-256 mismatch for {role}: "
                f"{actual} != {item['sha256']}"
            )
        verified_checkpoints[role] = {
            "path": str(target),
            "file": item["file"],
            "sha256": actual,
        }

    return {
        "source": source,
        "source_sha256": actual_source_sha,
        "target_reference": target_reference,
        "target_reference_sha256": actual_target_sha,
        "beltout_source": beltout_source,
        "expected_revision": revision,
        "checkpoint_dir": checkpoint_dir,
        "checkpoints": verified_checkpoints,
        "output": output,
        "report": report,
        "seed": seed,
        "n_timesteps": n_timesteps,
    }


def _load_audio_for_conversion(librosa, np, path, sample_rate):
    """Decode one immutable input without materializing a normalized raw file."""
    try:
        audio, _ = librosa.load(path, sr=sample_rate, mono=True)
        return np.asarray(audio, dtype=np.float32), "librosa"
    except Exception as primary_exc:
        try:
            import imageio_ffmpeg
        except ImportError as exc:
            raise ContractError(
                "Audio container is unsupported by the local decoder and "
                "imageio-ffmpeg is unavailable"
            ) from exc

        command = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel", "error",
            "-nostdin",
            "-i", str(path),
            "-vn",
            "-ac", "1",
            "-ar", str(sample_rate),
            "-f", "f32le",
            "-acodec", "pcm_f32le",
            "pipe:1",
        ]
        try:
            decoded = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError as exc:
            raise ContractError(f"Unable to invoke deterministic audio decoder: {exc}") from exc
        if decoded.returncode != 0:
            detail = (decoded.stderr or b"").decode("utf-8", errors="replace").strip()
            raise ContractError(
                "Unable to decode immutable source audio in memory"
                + (f": {detail}" if detail else "")
            ) from primary_exc
        audio = np.frombuffer(decoded.stdout or b"", dtype="<f4").copy()
        if audio.size == 0:
            raise ContractError("Deterministic in-memory audio decode produced no samples")
        return audio, "ffmpeg-memory"


def _cosine(torch, functional, a, b):
    a = a.detach().float().reshape(1, -1).cpu()
    b = b.detach().float().reshape(1, -1).cpu()
    return float(functional.cosine_similarity(a, b, dim=1).item())


def _convert_with_beltout(validated):
    try:
        import librosa
        import numpy as np
        import soundfile as sf
        import torch
        import torch.nn.functional as F
        import torchaudio
        import torchcrepe
    except ImportError as exc:
        raise ContractError(
            "BeltOut Production runtime dependencies are incomplete"
        ) from exc

    source_root = validated["beltout_source"]
    source_module_root = str(source_root / "src")
    inserted = False
    if source_module_root not in sys.path:
        sys.path.insert(0, source_module_root)
        inserted = True
    try:
        try:
            beltout_module = importlib.import_module("beltout")
            BeltOutTTM = beltout_module.BeltOutTTM
        except (ImportError, AttributeError) as exc:
            raise ContractError("Pinned BeltOut source cannot be imported") from exc

        checkpoints = validated["checkpoints"]
        model = BeltOutTTM.from_local(
            checkpoints["decoder"]["path"],
            checkpoints["pitch"]["path"],
            checkpoints["encoder"]["path"],
            checkpoints["flow"]["path"],
            checkpoints["mel2wav"]["path"],
            checkpoints["speaker"]["path"],
            checkpoints["tokenizer"]["path"],
            device="cpu",
        )

        source_wav, source_decoder = _load_audio_for_conversion(
            librosa, np, validated["source"], model.sr
        )
        target_wav, target_decoder = _load_audio_for_conversion(
            librosa, np, validated["target_reference"], model.sr
        )
        if len(source_wav) == 0 or len(target_wav) == 0:
            raise ContractError("BeltOut source and target reference must contain audio")

        source_t = torch.from_numpy(source_wav).float().unsqueeze(0)
        target_t = torch.from_numpy(target_wav).float().unsqueeze(0)
        with torch.inference_mode():
            source_x = model.embed_ref_x_vector(source_t, model.sr, device="cpu")
            target_x = model.embed_ref_x_vector(target_t, model.sr, device="cpu")

        torch.manual_seed(validated["seed"])
        np.random.seed(validated["seed"] % (2**32 - 1))
        torch.set_num_threads(2)

        wav24 = source_t.to("cpu")
        wav16 = torchaudio.functional.resample(wav24, model.sr, 16000)
        with torch.inference_mode():
            s3_tokens, _ = model.tokenizer(wav16)
            speaker_embedding = model.flow.spk_embed_affine_layer(target_x.to("cpu"))
            token_embeddings = model.flow.input_embedding(s3_tokens)
            token_len = torch.tensor([token_embeddings.shape[1]], device="cpu")
            hidden, _ = model.encoder(token_embeddings, token_len)
            encoded_tokens = model.flow.encoder_proj(hidden)
            mu = encoded_tokens.transpose(1, 2)
            mel_len = mu.shape[2]

            crepe_sr = 16000
            hop = int(crepe_sr / 100.0)
            frames_per_mel = 2
            samples_needed = mel_len * frames_per_mel * hop
            padded = wav16
            pad = samples_needed - padded.shape[1]
            if pad > 0:
                padded = F.pad(padded, (0, pad))

            crepe_embedding = torchcrepe.embed(
                padded,
                crepe_sr,
                hop_length=hop,
                model="tiny",
                device="cpu",
            )
            crepe_embedding = crepe_embedding[:, : mel_len * 2, :, :]
            projector_input = crepe_embedding.reshape(-1, frames_per_mel, 256)
            pitch_flat = model.pitchmvmt(projector_input)
            pitch = pitch_flat.reshape(1, -1, 80).transpose(1, 2)

            mask = torch.ones(1, 1, mu.shape[2], device="cpu", dtype=torch.bool)
            output_mels, _ = model.decoder(
                mu=mu,
                mask=mask,
                spks=speaker_embedding,
                cond=pitch,
                n_timesteps=validated["n_timesteps"],
            )
            output_wav, _ = model.mel2wav.inference(speech_feat=output_mels)

        converted = output_wav.squeeze().detach().cpu().numpy().astype(np.float32)
        source_duration = float(len(source_wav) / model.sr)
        converted_duration = float(len(converted) / model.sr)

        temp_output = validated["output"].with_suffix(
            validated["output"].suffix + ".tmp"
        )
        temp_output.parent.mkdir(parents=True, exist_ok=True)
        temp_output.unlink(missing_ok=True)
        sf.write(temp_output, converted, model.sr, subtype="PCM_16", format="WAV")
        temp_output.replace(validated["output"])

        output_read, output_sr = sf.read(
            validated["output"],
            dtype="float32",
            always_2d=False,
        )
        output_np = np.asarray(output_read, dtype=np.float32)
        if output_np.ndim == 2:
            output_np = output_np.mean(axis=1)
        finite = bool(np.isfinite(output_np).all())
        rms = float(np.sqrt(np.mean(np.square(output_np)))) if len(output_np) else 0.0
        peak = float(np.max(np.abs(output_np))) if len(output_np) else 0.0
        technical_pass = (
            finite
            and output_sr > 0
            and 0.20 <= converted_duration <= 30.0
            and 0.0015 <= rms <= 0.8
            and peak <= 1.0
        )

        output_t = torch.from_numpy(output_np).float().unsqueeze(0)
        with torch.inference_mode():
            output_x = model.embed_ref_x_vector(output_t, output_sr, device="cpu")
        source_to_target = _cosine(torch, F, source_x, target_x)
        output_to_target = _cosine(torch, F, output_x, target_x)
        output_to_source = _cosine(torch, F, output_x, source_x)
        identity_direction_pass = (
            output_to_target > source_to_target
            and output_to_target > output_to_source
        )
        duration_ratio = (
            converted_duration / source_duration if source_duration else math.inf
        )
        duration_pass = 0.75 <= duration_ratio <= 1.25

        return {
            "audio_decode": {
                "source": source_decoder,
                "target_reference": target_decoder,
                "persistent_normalized_raw_file": False,
                "filters": [],
            },
            "technical": {
                "status": "PASS" if technical_pass else "REJECT",
                "sample_rate": int(output_sr),
                "duration_seconds": converted_duration,
                "rms": rms,
                "peak": peak,
                "finite": finite,
            },
            "source_duration_seconds": source_duration,
            "output_duration_seconds": converted_duration,
            "duration_ratio": duration_ratio,
            "duration_pass": duration_pass,
            "speaker_embedding": {
                "cosine_source_to_target": source_to_target,
                "cosine_output_to_target": output_to_target,
                "cosine_output_to_source": output_to_source,
                "direction_pass": identity_direction_pass,
            },
            "pass": bool(
                technical_pass and duration_pass and identity_direction_pass
            ),
        }
    finally:
        if inserted:
            try:
                sys.path.remove(source_module_root)
            except ValueError:
                pass


def convert_beltout_once(
    *,
    source,
    source_sha256,
    target_reference,
    target_reference_sha256,
    beltout_source,
    expected_revision,
    checkpoint_dir,
    checkpoint_manifest,
    output,
    report,
    seed,
    n_timesteps,
):
    validated = verify_beltout_conversion_inputs(
        source=source,
        source_sha256=source_sha256,
        target_reference=target_reference,
        target_reference_sha256=target_reference_sha256,
        beltout_source=beltout_source,
        expected_revision=expected_revision,
        checkpoint_dir=checkpoint_dir,
        checkpoint_manifest=checkpoint_manifest,
        output=output,
        report=report,
        seed=seed,
        n_timesteps=n_timesteps,
    )
    evidence = _convert_with_beltout(validated)
    result = {
        "schema_version": 1,
        "status": "PASS" if evidence["pass"] else "REJECT",
        "operation": "beltout-once",
        "retry_allowed_after_output": False,
        "network_used": False,
        "fallback": "fail",
        "inputs": {
            "source_sha256": validated["source_sha256"],
            "target_reference_sha256": validated["target_reference_sha256"],
            "beltout_revision": validated["expected_revision"],
            "checkpoints": {
                role: {
                    "file": item["file"],
                    "sha256": item["sha256"],
                }
                for role, item in validated["checkpoints"].items()
            },
        },
        "conversion": {
            "seed": validated["seed"],
            "n_timesteps": validated["n_timesteps"],
            "best_of_n": False,
            "second_pass": False,
            "time_stretch": False,
            "pitch_shift": False,
            "emotion_dsp": False,
        },
        "output": {
            "path": str(validated["output"]),
            "sha256": _sha256(validated["output"]),
        },
        "evidence": evidence,
    }
    report_path = validated["report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temp_report = report_path.with_suffix(report_path.suffix + ".tmp")
    temp_report.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp_report.replace(report_path)
    return result
