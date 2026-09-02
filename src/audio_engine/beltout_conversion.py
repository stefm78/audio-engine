import hashlib
import json
import math
import sys
from pathlib import Path

from .contract import ContractError


CHECKPOINTS = {
    "decoder": "cfm_step_117580.safetensors",
    "pitch": "pitchmvmt_step_117580.safetensors",
    "encoder": "encoder_step_0.safetensors",
    "flow": "flow_step_0.safetensors",
    "mel2wav": "mel2wav_step_0.safetensors",
    "speaker": "speaker_encoder_step_0.safetensors",
    "tokenizer": "tokenizer_step_0.safetensors",
}


class BeltOutConversionError(ContractError):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def constant_gain_db(source_rms, converted_rms, clamp_db):
    if source_rms <= 0 or converted_rms <= 0:
        raise BeltOutConversionError("source and converted RMS must be positive")
    if clamp_db < 0:
        raise BeltOutConversionError("gain clamp must be non-negative")
    wanted = 20.0 * math.log10(source_rms / converted_rms)
    return max(-float(clamp_db), min(float(clamp_db), wanted))


def _rms(values):
    import numpy as np
    values = np.asarray(values, dtype=np.float32)
    return float(np.sqrt(np.mean(np.square(values)))) if len(values) else 0.0


def _tech_gate(values, sample_rate):
    import numpy as np
    values = np.asarray(values, dtype=np.float32)
    finite = bool(np.isfinite(values).all())
    duration = float(len(values) / sample_rate) if sample_rate else 0.0
    rms = _rms(values)
    peak = float(np.max(np.abs(values))) if len(values) else 0.0
    passed = finite and 0.25 <= duration <= 20.0 and 0.0015 <= rms <= 0.8 and peak <= 1.0
    return {
        "status": "PASS" if passed else "REJECT",
        "sample_rate": int(sample_rate),
        "duration_seconds": duration,
        "rms": rms,
        "peak": peak,
        "finite": finite,
    }


def _convert_waveform(model, source_wav, device, n_timesteps):
    import numpy as np
    import torch
    import torch.nn.functional as F
    import torchaudio

    wav = torch.from_numpy(np.asarray(source_wav, dtype=np.float32)).float().to(device).unsqueeze(0)
    wav16 = torchaudio.functional.resample(wav, model.sr, 16000)

    with torch.inference_mode():
        tokens, _ = model.tokenizer(wav16)
        target_x = model._production_target_x_vector
        speaker_embedding = model.flow.spk_embed_affine_layer(target_x)
        token_embeddings = model.flow.input_embedding(tokens)
        token_len = torch.tensor([token_embeddings.shape[1]], device=device)
        h, _ = model.encoder(token_embeddings, token_len)
        encoded_tokens = model.flow.encoder_proj(h)
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

        import torchcrepe

        crepe_embedding = torchcrepe.embed(
            padded,
            crepe_sr,
            hop_length=hop,
            model="tiny",
            device=device,
        )
        crepe_embedding = crepe_embedding[:, : mel_len * 2, :, :]
        projector_input = crepe_embedding.reshape(-1, frames_per_mel, 256)
        pitch_flat = model.pitchmvmt(projector_input)
        pitch = pitch_flat.reshape(1, -1, 80).transpose(1, 2)
        mask = torch.ones(1, 1, mu.shape[2], device=device, dtype=torch.bool)
        output_mels, _ = model.decoder(
            mu=mu,
            mask=mask,
            spks=speaker_embedding,
            cond=pitch,
            n_timesteps=int(n_timesteps),
        )
        output_wav, _ = model.mel2wav.inference(speech_feat=output_mels)

    return output_wav.squeeze().detach().cpu().numpy().astype(np.float32)


def convert_once(
    source_path,
    target_anchor_path,
    beltout_source,
    checkpoint_dir,
    output_path,
    *,
    seed,
    n_timesteps=10,
    gain_clamp_db=8.0,
    device="cpu",
):
    """Perform one immutable BeltOut conversion. Existing output is a hard stop."""
    source_path = Path(source_path).resolve()
    target_anchor_path = Path(target_anchor_path).resolve()
    beltout_source = Path(beltout_source).resolve()
    checkpoint_dir = Path(checkpoint_dir).resolve()
    output_path = Path(output_path).resolve()

    if output_path.exists():
        raise BeltOutConversionError(
            f"single-pass output already exists; overwrite/retry forbidden: {output_path}"
        )
    for label, path in (("source", source_path), ("target anchor", target_anchor_path)):
        if not path.is_file():
            raise BeltOutConversionError(f"{label} file not found: {path}")
    for filename in CHECKPOINTS.values():
        if not (checkpoint_dir / filename).is_file():
            raise BeltOutConversionError(f"missing BeltOut checkpoint: {filename}")

    import numpy as np
    import soundfile as sf
    import torch
    import librosa

    torch.manual_seed(int(seed))
    np.random.seed(int(seed) % (2**32 - 1))
    torch.set_num_threads(2)

    sys.path.insert(0, str(beltout_source / "src"))
    try:
        from beltout import BeltOutTTM
    except Exception as exc:
        raise BeltOutConversionError(f"cannot import BeltOut from exact source: {exc}") from exc

    model = BeltOutTTM.from_local(
        str(checkpoint_dir / CHECKPOINTS["decoder"]),
        str(checkpoint_dir / CHECKPOINTS["pitch"]),
        str(checkpoint_dir / CHECKPOINTS["encoder"]),
        str(checkpoint_dir / CHECKPOINTS["flow"]),
        str(checkpoint_dir / CHECKPOINTS["mel2wav"]),
        str(checkpoint_dir / CHECKPOINTS["speaker"]),
        str(checkpoint_dir / CHECKPOINTS["tokenizer"]),
        device=device,
    )

    source_wav, _ = librosa.load(source_path, sr=model.sr, mono=True)
    anchor_wav, _ = librosa.load(target_anchor_path, sr=model.sr, mono=True)
    if _tech_gate(source_wav, model.sr)["status"] != "PASS":
        raise BeltOutConversionError("source performance failed technical gate")
    if _tech_gate(anchor_wav, model.sr)["status"] != "PASS":
        raise BeltOutConversionError("target anchor failed technical gate")

    with torch.inference_mode():
        anchor_t = torch.from_numpy(anchor_wav).float().unsqueeze(0)
        target_x = model.embed_ref_x_vector(anchor_t, model.sr, device=device)
    model._production_target_x_vector = target_x.to(device)

    converted = _convert_waveform(model, source_wav, device, int(n_timesteps))
    source_rms = _rms(source_wav)
    converted_rms = _rms(converted)
    gain_db = constant_gain_db(source_rms, converted_rms, float(gain_clamp_db))
    peak = float(np.max(np.abs(converted))) if len(converted) else 0.0
    if peak > 0:
        peak_safe_db = 20.0 * math.log10(0.99 / peak)
        gain_db = min(gain_db, peak_safe_db)
    gain = math.pow(10.0, gain_db / 20.0)
    aligned = np.asarray(converted, dtype=np.float32) * gain

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, aligned, model.sr, subtype="PCM_16")

    source_duration = len(source_wav) / model.sr
    output_duration = len(aligned) / model.sr
    duration_ratio = output_duration / source_duration if source_duration else math.inf
    gate = _tech_gate(aligned, model.sr)
    duration_pass = 0.75 <= duration_ratio <= 1.25
    status = "PASS" if gate["status"] == "PASS" and duration_pass else "REJECT"

    report = {
        "schema": "audio-engine.beltout.production-conversion.v1",
        "status": status,
        "single_pass": True,
        "source_sha256": sha256_file(source_path),
        "target_anchor_sha256": sha256_file(target_anchor_path),
        "output_sha256": sha256_file(output_path),
        "seed": int(seed),
        "n_timesteps": int(n_timesteps),
        "device": device,
        "post_conversion": {
            "kind": "constant_level_alignment_only",
            "source_rms": source_rms,
            "converted_rms_before_gain": converted_rms,
            "applied_gain_db": gain_db,
            "gain_clamp_db": float(gain_clamp_db),
        },
        "timing": {
            "source_duration_seconds": source_duration,
            "output_duration_seconds": output_duration,
            "duration_ratio": duration_ratio,
            "pass": duration_pass,
        },
        "technical_gate": gate,
    }
    report_path = output_path.with_suffix(output_path.suffix + ".json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if status != "PASS":
        raise BeltOutConversionError(
            "BeltOut conversion output failed technical/timing gate; no retry is authorized"
        )
    return report
