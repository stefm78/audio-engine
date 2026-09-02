#!/usr/bin/env python3
"""Confucius4 R0 resource gate for Odyssée P6.

Exactly one neutral French render. This is not an artistic P6 candidate.
All model dependencies are local, predownloaded at pinned revisions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import yaml

BASELINE_AUDIO_SHA256 = "474c2e41a5d702b2a84524aa3be9a0559ed7378af18d507ac082b666029d64ae"
BASELINE_REPORT_SHA256 = "366091a73e7597626384535e900a5b30e7943c485d0197ec25f015c384b6d891"
ANCHOR_SEGMENTS = (6, 7, 8)
CALIBRATION_TEXT = "Je suis revenu à Ithaque."
LANG = "fr"
SEED = 2026090101

SOURCE_REV = "45f83890b72ba26d1954dab5001600301ebe8dd3"
CONFUCIUS_HF_REV = "696981f"
W2V_HF_REV = "da985ba"
CAMPPLUS_HF_REV = "e4b6ede"
BIGVGAN_HF_REV = "633ff70"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_baseline(audio: Path, report: Path) -> dict:
    if sha256(audio) != BASELINE_AUDIO_SHA256:
        raise SystemExit("R0_BASELINE_AUDIO_SHA_REJECT")
    if sha256(report) != BASELINE_REPORT_SHA256:
        raise SystemExit("R0_BASELINE_REPORT_SHA_REJECT")
    data = json.loads(report.read_text(encoding="utf-8"))
    if data.get("variant") != "p6-b":
        raise SystemExit("R0_BASELINE_VARIANT_REJECT")
    by_i = {int(x["i"]): x for x in data["segments"]}
    for i in ANCHOR_SEGMENTS:
        if i not in by_i or by_i[i].get("speaker") != "Ulysse":
            raise SystemExit(f"R0_ANCHOR_BINDING_REJECT:{i}")
    return data


def derive_anchor(audio: Path, report: dict, out: Path) -> tuple[Path, list[dict]]:
    decoded = out / "baseline-16k.wav"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(audio),
         "-ar", "16000", "-ac", "1", str(decoded)],
        check=True,
    )
    y, sr = sf.read(decoded, dtype="float32", always_2d=False)
    if sr != 16000:
        raise SystemExit("R0_DECODE_SR_REJECT")

    cursor_ms = 0
    bounds = {}
    for s in report["segments"]:
        i = int(s["i"])
        audio_ms = int(s["audio_ms"])
        pause_ms = int(s.get("pause_ms", 0))
        bounds[i] = (cursor_ms, cursor_ms + audio_ms)
        cursor_ms += audio_ms + pause_ms

    chunks = []
    parts = []
    silence = np.zeros(int(sr * 0.16), dtype=np.float32)
    for n, i in enumerate(ANCHOR_SEGMENTS):
        start_ms, end_ms = bounds[i]
        a = int(round(start_ms * sr / 1000))
        b = int(round(end_ms * sr / 1000))
        clip = np.asarray(y[a:b], dtype=np.float32)
        chunks.append(clip)
        parts.append({
            "i": i,
            "audio_ms": int(round(len(clip) * 1000 / sr)),
            "pcm_sha256": hashlib.sha256(clip.tobytes()).hexdigest(),
        })
        if n < len(ANCHOR_SEGMENTS) - 1:
            chunks.append(silence)

    anchor = np.concatenate(chunks)
    anchor_path = out / "ulysse-henri-anchor.wav"
    sf.write(anchor_path, anchor, sr, subtype="PCM_16")
    return anchor_path, parts


def tech_gate(path: Path) -> dict:
    y, sr = sf.read(path, dtype="float32", always_2d=False)
    y = np.asarray(y, dtype=np.float32)
    if y.ndim == 2:
        y = y.mean(axis=1)
    finite = bool(np.isfinite(y).all())
    duration = float(len(y) / sr) if sr else 0.0
    rms = float(np.sqrt(np.mean(np.square(y)))) if len(y) else 0.0
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    passed = finite and 0.15 <= duration <= 12.0 and 0.0015 <= rms <= 0.7 and peak <= 1.0
    return {
        "status": "PASS" if passed else "REJECT",
        "sample_rate": int(sr),
        "duration_seconds": duration,
        "rms": rms,
        "peak": peak,
        "finite": finite,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--confucius-model-dir", required=True)
    ap.add_argument("--w2v-dir", required=True)
    ap.add_argument("--campplus-dir", required=True)
    ap.add_argument("--bigvgan-dir", required=True)
    ap.add_argument("--baseline-audio", required=True)
    ap.add_argument("--baseline-report", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    source_dir = Path(args.source_dir).resolve()
    confucius_dir = Path(args.confucius_model_dir).resolve()
    w2v_dir = Path(args.w2v_dir).resolve()
    campplus_dir = Path(args.campplus_dir).resolve()
    bigvgan_dir = Path(args.bigvgan_dir).resolve()

    report = validate_baseline(Path(args.baseline_audio), Path(args.baseline_report))
    anchor, anchor_parts = derive_anchor(Path(args.baseline_audio), report, out)

    cfg = yaml.safe_load((source_dir / "config/inference_config.yaml").read_text(encoding="utf-8"))
    cfg["paths"]["tokenizer_path"] = str(confucius_dir)
    cfg["paths"]["w2v_bert_path"] = str(w2v_dir)
    cfg["paths"]["w2v_stat"] = str(confucius_dir / "wav2vec2bert_stats.pt")
    cfg["paths"]["vocoder_path"] = str(bigvgan_dir)
    cfg["paths"]["style_encoder"]["checkpoint"] = "campplus_cn_common.bin"
    cfg["paths"]["t2s_checkpoint"] = "t2s_model.safetensors"
    cfg["paths"]["s2a_checkpoint"] = "s2a_model.pt"
    local_cfg = out / "inference-pinned.yaml"
    local_cfg.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    sys.path.insert(0, str(source_dir))
    import confuciustts.cli.inference as inf  # noqa: E402

    def pinned_hf_hub_download(repo_id: str, filename: str, *a, **kw):
        if repo_id == "netease-youdao/Confucius4-TTS":
            p = confucius_dir / filename
        elif repo_id == "funasr/campplus":
            p = campplus_dir / filename
        else:
            raise RuntimeError(f"R0_UNPINNED_HF_DOWNLOAD_REJECT:{repo_id}:{filename}")
        if not p.is_file():
            raise FileNotFoundError(p)
        return str(p)

    inf.hf_hub_download = pinned_hf_hub_download

    random.seed(SEED)
    np.random.seed(SEED % (2**32 - 1))
    torch.manual_seed(SEED)

    model = inf.ConfuciusTTS(config_path=str(local_cfg), device="cpu")

    random.seed(SEED)
    np.random.seed(SEED % (2**32 - 1))
    torch.manual_seed(SEED)
    audio = model.generate(
        text=CALIBRATION_TEXT,
        lang=LANG,
        prompt_wav=str(anchor),
        temperature=0.8,
        top_p=0.8,
        top_k=30,
        num_beams=3,
        repetition_penalty=10.0,
        max_length=512,
        n_timesteps=25,
        inference_cfg_rate=0.7,
        max_text_tokens_per_segment=80,
        verbose=True,
    )
    output = out / "confucius4-r0.wav"
    sf.write(output, audio.detach().cpu().numpy().squeeze(), model.sample_rate, subtype="PCM_16")
    gate = tech_gate(output)
    if gate["status"] != "PASS":
        raise SystemExit("R0_TECHNICAL_REJECT:" + json.dumps(gate))

    manifest = {
        "schema": "audio-engine.confucius4.r0.v1",
        "status": "RESOURCE_GATE_PASS",
        "artistic_candidate": False,
        "human_review": False,
        "cloud_tts": False,
        "nuc_required": False,
        "source": {
            "repo": "netease-youdao/Confucius4-TTS",
            "revision": SOURCE_REV,
        },
        "models": {
            "confucius4": {"repo": "netease-youdao/Confucius4-TTS", "revision": CONFUCIUS_HF_REV},
            "w2v_bert": {"repo": "facebook/w2v-bert-2.0", "revision": W2V_HF_REV},
            "campplus": {"repo": "funasr/campplus", "revision": CAMPPLUS_HF_REV},
            "bigvgan": {"repo": "nvidia/bigvgan_v2_22khz_80band_256x", "revision": BIGVGAN_HF_REV},
        },
        "baseline": {
            "audio_sha256": BASELINE_AUDIO_SHA256,
            "report_sha256": BASELINE_REPORT_SHA256,
            "anchor_segments": list(ANCHOR_SEGMENTS),
            "anchor_sha256": sha256(anchor),
            "anchor_parts": anchor_parts,
        },
        "render": {
            "text": CALIBRATION_TEXT,
            "language": LANG,
            "seed": SEED,
            "output_sha256": sha256(output),
            "technical_gate": gate,
        },
        "decision": "AUTHORIZE_ONE_P6_SCIENTIFIC_CELL_IF_RUNNER_RESOURCE_PASS",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
