#!/usr/bin/env python3
"""BeltOut R0 for Odyssée P6.

One immutable expressive source clip -> one immutable Henri/Ulysse target x-vector.
Resource/capability gate only. No P6 target text and no human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F
import torchaudio

BELTOUT_SOURCE_REV = "f71295e33cc9c0092083089ed0f9c1a532e77e6b"
BELTOUT_HF_REV = "f71295e33cc9c0092083089ed0f9c1a532e77e6b"

BASELINE_AUDIO_SHA256 = "474c2e41a5d702b2a84524aa3be9a0559ed7378af18d507ac082b666029d64ae"
BASELINE_REPORT_SHA256 = "366091a73e7597626384535e900a5b30e7943c485d0197ec25f015c384b6d891"
DONOR_SHA256 = "4194a72b1705ec1820ea13cfdd3a0ed434e2bf63a445ba9f85ea1aeca33fdd25"
ANCHOR_SEGMENTS = (6, 7, 8)
SEED = 2026090207

CHECKPOINTS = {
    "decoder": "cfm_step_117580.safetensors",
    "pitch": "pitchmvmt_step_117580.safetensors",
    "encoder": "encoder_step_0.safetensors",
    "flow": "flow_step_0.safetensors",
    "mel2wav": "mel2wav_step_0.safetensors",
    "speaker": "speaker_encoder_step_0.safetensors",
    "tokenizer": "tokenizer_step_0.safetensors",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_report(audio: Path, report_path: Path) -> dict:
    if sha256(audio) != BASELINE_AUDIO_SHA256:
        raise SystemExit("BELTOUT_R0_BASELINE_AUDIO_SHA_REJECT")
    if sha256(report_path) != BASELINE_REPORT_SHA256:
        raise SystemExit("BELTOUT_R0_BASELINE_REPORT_SHA_REJECT")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("variant") != "p6-b":
        raise SystemExit("BELTOUT_R0_BASELINE_VARIANT_REJECT")
    by_i = {int(x["i"]): x for x in report["segments"]}
    for i in ANCHOR_SEGMENTS:
        if i not in by_i or by_i[i].get("speaker") != "Ulysse":
            raise SystemExit(f"BELTOUT_R0_ANCHOR_BINDING_REJECT:{i}")
    return report


def derive_anchor(audio: Path, report: dict, out: Path) -> Path:
    y, sr = librosa.load(audio, sr=24000, mono=True)
    cursor_ms = 0
    bounds = {}
    for s in report["segments"]:
        i = int(s["i"])
        audio_ms = int(s["audio_ms"])
        pause_ms = int(s.get("pause_ms", 0))
        bounds[i] = (cursor_ms, cursor_ms + audio_ms)
        cursor_ms += audio_ms + pause_ms

    parts = []
    silence = np.zeros(int(0.16 * sr), dtype=np.float32)
    for n, i in enumerate(ANCHOR_SEGMENTS):
        start_ms, end_ms = bounds[i]
        a = int(round(start_ms * sr / 1000))
        b = int(round(end_ms * sr / 1000))
        parts.append(np.asarray(y[a:b], dtype=np.float32))
        if n < len(ANCHOR_SEGMENTS) - 1:
            parts.append(silence)

    anchor = np.concatenate(parts)
    p = out / "ulysse-henri-anchor.wav"
    sf.write(p, anchor, sr, subtype="PCM_16")
    return p


def tech_gate(path: Path) -> dict:
    y, sr = sf.read(path, dtype="float32", always_2d=False)
    y = np.asarray(y, dtype=np.float32)
    if y.ndim == 2:
        y = y.mean(axis=1)
    finite = bool(np.isfinite(y).all())
    duration = float(len(y) / sr) if sr else 0.0
    rms = float(np.sqrt(np.mean(np.square(y)))) if len(y) else 0.0
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    passed = finite and 0.25 <= duration <= 15.0 and 0.0015 <= rms <= 0.8 and peak <= 1.0
    return {
        "status": "PASS" if passed else "REJECT",
        "sample_rate": int(sr),
        "duration_seconds": duration,
        "rms": rms,
        "peak": peak,
        "finite": finite,
    }


def cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    a = a.detach().float().reshape(1, -1).cpu()
    b = b.detach().float().reshape(1, -1).cpu()
    return float(F.cosine_similarity(a, b, dim=1).item())


def convert_one(model, source_wav: np.ndarray, device: str) -> np.ndarray:
    wav24 = torch.from_numpy(source_wav).float().to(device).unsqueeze(0)
    wav16 = torchaudio.functional.resample(wav24, model.sr, 16000)

    with torch.inference_mode():
        s3_tokens, _ = model.tokenizer(wav16)

        # Target timbre is supplied separately by the caller through model._r0_target_x_vector.
        target_x = model._r0_target_x_vector
        speaker_embedding = model.flow.spk_embed_affine_layer(target_x)

        token_embeddings = model.flow.input_embedding(s3_tokens)
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
            n_timesteps=10,
        )
        output_wav, _ = model.mel2wav.inference(speech_feat=output_mels)

    return output_wav.squeeze().detach().cpu().numpy().astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--beltout-source", required=True)
    ap.add_argument("--checkpoint-dir", required=True)
    ap.add_argument("--baseline-audio", required=True)
    ap.add_argument("--baseline-report", required=True)
    ap.add_argument("--donor", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    torch.manual_seed(SEED)
    np.random.seed(SEED % (2**32 - 1))
    torch.set_num_threads(2)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    source_root = Path(args.beltout_source).resolve()
    ckpt = Path(args.checkpoint_dir).resolve()
    baseline_audio = Path(args.baseline_audio)
    report_path = Path(args.baseline_report)
    donor = Path(args.donor)

    if sha256(donor) != DONOR_SHA256:
        raise SystemExit("BELTOUT_R0_DONOR_SHA_REJECT")

    report = load_report(baseline_audio, report_path)
    anchor = derive_anchor(baseline_audio, report, out)

    for filename in CHECKPOINTS.values():
        if not (ckpt / filename).is_file():
            raise SystemExit(f"BELTOUT_R0_MISSING_CHECKPOINT:{filename}")

    import sys
    sys.path.insert(0, str(source_root / "src"))
    from beltout import BeltOutTTM

    model = BeltOutTTM.from_local(
        str(ckpt / CHECKPOINTS["decoder"]),
        str(ckpt / CHECKPOINTS["pitch"]),
        str(ckpt / CHECKPOINTS["encoder"]),
        str(ckpt / CHECKPOINTS["flow"]),
        str(ckpt / CHECKPOINTS["mel2wav"]),
        str(ckpt / CHECKPOINTS["speaker"]),
        str(ckpt / CHECKPOINTS["tokenizer"]),
        device="cpu",
    )

    donor_wav, _ = librosa.load(donor, sr=model.sr, mono=True)
    anchor_wav, _ = librosa.load(anchor, sr=model.sr, mono=True)

    donor_t = torch.from_numpy(donor_wav).float().unsqueeze(0)
    anchor_t = torch.from_numpy(anchor_wav).float().unsqueeze(0)
    with torch.inference_mode():
        source_x = model.embed_ref_x_vector(donor_t, model.sr, device="cpu")
        target_x = model.embed_ref_x_vector(anchor_t, model.sr, device="cpu")

    model._r0_target_x_vector = target_x.to("cpu")

    torch.manual_seed(SEED)
    np.random.seed(SEED % (2**32 - 1))
    converted = convert_one(model, donor_wav, "cpu")

    output = out / "beltout-r0.wav"
    sf.write(output, converted, model.sr, subtype="PCM_16")

    gate = tech_gate(output)
    if gate["status"] != "PASS":
        raise SystemExit("BELTOUT_R0_TECHNICAL_REJECT:" + json.dumps(gate))

    output_wav, _ = librosa.load(output, sr=model.sr, mono=True)
    output_t = torch.from_numpy(output_wav).float().unsqueeze(0)
    with torch.inference_mode():
        output_x = model.embed_ref_x_vector(output_t, model.sr, device="cpu")

    source_to_target = cosine(source_x, target_x)
    output_to_target = cosine(output_x, target_x)
    output_to_source = cosine(output_x, source_x)

    source_duration = len(donor_wav) / model.sr
    output_duration = len(output_wav) / model.sr
    ratio = output_duration / source_duration if source_duration else math.inf

    identity_direction_pass = (
        output_to_target > source_to_target
        and output_to_target > output_to_source
    )
    duration_pass = 0.75 <= ratio <= 1.25

    manifest = {
        "schema": "audio-engine.beltout.r0.v1",
        "status": "RESOURCE_CAPABILITY_GATE_PASS"
        if identity_direction_pass and duration_pass
        else "CAPABILITY_REJECT",
        "artistic_candidate": False,
        "human_review": False,
        "cloud_tts": False,
        "nuc_required": False,
        "source": {
            "repo": "Bill13579/beltout",
            "revision": BELTOUT_SOURCE_REV,
            "hf_revision": BELTOUT_HF_REV,
            "checkpoints": CHECKPOINTS,
        },
        "inputs": {
            "donor_sha256": DONOR_SHA256,
            "baseline_audio_sha256": BASELINE_AUDIO_SHA256,
            "baseline_report_sha256": BASELINE_REPORT_SHA256,
            "anchor_segments": list(ANCHOR_SEGMENTS),
            "anchor_sha256": sha256(anchor),
        },
        "render": {
            "seed": SEED,
            "output_sha256": sha256(output),
            "technical_gate": gate,
            "source_duration_seconds": source_duration,
            "output_duration_seconds": output_duration,
            "duration_ratio": ratio,
        },
        "speaker_embedding": {
            "cosine_source_to_target": source_to_target,
            "cosine_output_to_target": output_to_target,
            "cosine_output_to_source": output_to_source,
            "direction_pass": identity_direction_pass,
        },
        "duration_pass": duration_pass,
        "decision": "AUTHORIZE_ONE_REAL_P6_BELTOUT_CELL"
        if identity_direction_pass and duration_pass
        else "CLOSE_BELTOUT_NO_TUNING",
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if manifest["status"] != "RESOURCE_CAPABILITY_GATE_PASS":
        raise SystemExit("BELTOUT_R0_CAPABILITY_REJECT")


if __name__ == "__main__":
    main()
