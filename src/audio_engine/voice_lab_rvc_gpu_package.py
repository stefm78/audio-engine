"""Frozen GPU handover contract for learned Lucie identity in the Voice Lab.

This module does not train anything. It defines the exact RVC source/config/model
provenance and creates deterministic single-speaker v2/32k/F0 file lists.
Production Edge is intentionally outside this module.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

RVC_REPO = "RVC-Project/Retrieval-based-Voice-Conversion-WebUI"
RVC_REVISION = "81eed5e8f68b6bed1789f682fe78cdd324495afc"
RVC_LICENSE = "MIT"
RVC_CONFIG = "configs/v2/32k.json"
RVC_CONFIG_BLOB = "09788b030b575bbc812319d18af15ec2815187be"
RVC_SOURCE_BLOBS = {
    "train/preprocess.py": "917fb928a12aa45f8d21f6f7f77522df3ff417e7",
    "train/dataset/extract_f0.py": "22c7c3f56249acc61f46b77b10e3c2b3e81691b7",
    "train/dataset/extract_hubert_feature.py": "9fd24375668d92f5bbcc1f2a934095c54d7cab1b",
    "train/train.py": "3a5c51b01a3006bc7ce714a2a939dce817cf80b9",
    "train/train_index.py": "b3a73e513ae8fbcd791a9959c4ea5e3c63837c22",
    "train/data_utils.py": "682538a84056d118962925155fb319d0caf7750d",
    "infer/module/models.py": "d0e612452671f7188e8a13431ac6a9eab29b4ee0",
    "train/losses.py": "aa7bd81cf596884a8b33e802ae49254d7810a860",
}

MODEL_REPO = "lj1995/VoiceConversionWebUI"
MODEL_REPO_LICENSE = "MIT"
MODEL_ASSETS = {
    "assets/hubert_base/pytorch_model.bin": "cc8c20f4b90a520757260197a3ff2505705a7adbd20ad9eeaa4e1a9b38442ef5",
    "assets/rmvpe/rmvpe.pt": "6d62215f4306e3ca278246188607209f09af3dc77ed4232efdd069798c4ec193",
    "assets/pretrained_v2/f0G32k.pth": "2332611297b8d88c7436de8f17ef5f07a2119353e962cd93cda5806d59a1133d",
    "assets/pretrained_v2/f0D32k.pth": "bd7134e7793674c85474d5145d2d982e3c5d8124fc7bb6c20f710ed65808fa8a",
    "mute.zip": "ee948e85213e4ed2f2ba2f8dfcee810bfd0b63131d91450e920bbe1cbd0321d0",
}

EXPERIMENT = "lucie_rvc_v2_32k"
SAMPLE_RATE = 32000
VERSION = "v2"
IF_F0 = 1
F0_METHOD = "rmvpe"
GPU_ID = 0
BATCH_SIZE = 4
TOTAL_EPOCHS = 200
SAVE_EVERY_EPOCHS = 25
TRAIN_SEED = 1234  # native configs/v2/32k.json value
PREPROCESS_SLICE_SECONDS = 3.7
SPEAKER_ID = 0
MIN_DATASET_SECONDS = 300.0
MAX_AGGREGATE_WER = 0.05
MIN_EXPANSION_ACCEPTANCE_RATE = 0.85


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def package_spec() -> dict:
    return {
        "schema": "voice-lab-rvc-gpu-package-v1",
        "role": "lucie",
        "rvc": {
            "repo": RVC_REPO,
            "revision": RVC_REVISION,
            "license": RVC_LICENSE,
            "config": RVC_CONFIG,
            "config_git_blob": RVC_CONFIG_BLOB,
            "source_git_blobs": dict(RVC_SOURCE_BLOBS),
        },
        "bootstrap_models": {
            "repo": MODEL_REPO,
            "license": MODEL_REPO_LICENSE,
            "sha256": dict(MODEL_ASSETS),
            "mutable_revision_allowed_only_with_hash_verification": True,
        },
        "training": {
            "sample_rate": SAMPLE_RATE,
            "version": VERSION,
            "if_f0": IF_F0,
            "f0_method": F0_METHOD,
            "gpu_id": GPU_ID,
            "batch_size": BATCH_SIZE,
            "total_epochs": TOTAL_EPOCHS,
            "save_every_epochs": SAVE_EVERY_EPOCHS,
            "seed": TRAIN_SEED,
            "preprocess_slice_seconds": PREPROCESS_SLICE_SECONDS,
            "cache_dataset_in_gpu": False,
            "single_speaker_id": SPEAKER_ID,
            "parameter_tuning": False,
        },
        "dataset_contract": {
            "status": "dataset-pass",
            "accepted_duration_seconds_min": MIN_DATASET_SECONDS,
            "aggregate_wer_max": MAX_AGGREGATE_WER,
            "expansion_acceptance_rate_min": MIN_EXPANSION_ACCEPTANCE_RATE,
            "retries": 0,
            "substitutions": 0,
        },
        "human_gate": False,
        "production_qualified": False,
    }


def validate_dataset_manifest(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("status") != "dataset-pass":
        raise ValueError("RVC GPU handover requires a machine-qualified dataset-pass manifest")
    if float(data.get("accepted_duration_seconds", 0.0)) < MIN_DATASET_SECONDS:
        raise ValueError("qualified dataset is shorter than 300 seconds")
    if float(data.get("aggregate_wer", 1.0)) > MAX_AGGREGATE_WER + 1e-12:
        raise ValueError("qualified dataset aggregate WER exceeds 0.05")
    if float(data.get("expansion_acceptance_rate", 0.0)) < MIN_EXPANSION_ACCEPTANCE_RATE - 1e-12:
        raise ValueError("qualified dataset expansion acceptance rate is below 0.85")
    if int(data.get("retries", 0)) != 0 or int(data.get("substitutions", 0)) != 0:
        raise ValueError("dataset contract forbids retries/substitutions")
    return data


def build_filelist(exp_dir: Path, *, speaker_id: int = SPEAKER_ID) -> list[str]:
    """Build the single-speaker F0 filelist expected by the pinned RVC CLI."""
    exp_dir = Path(exp_dir).resolve()
    gt = exp_dir / "0_gt_wavs"
    feature = exp_dir / "3_feature768"
    f0 = exp_dir / "2a_f0"
    f0nsf = exp_dir / "2b-f0nsf"
    names = sorted(p.name for p in gt.glob("*.wav"))
    if not names:
        raise ValueError("no preprocessed training WAVs")
    rows = []
    for name in names:
        stem = Path(name).stem
        paths = [
            gt / name,
            feature / f"{stem}.npy",
            f0 / f"{name}.npy",
            f0nsf / f"{name}.npy",
        ]
        missing = [str(p) for p in paths if not p.is_file()]
        if missing:
            raise ValueError(f"incomplete RVC feature tuple for {name}: {missing}")
        rows.append("|".join([*(str(p) for p in paths), str(speaker_id)]))
    return rows


def mute_rows(rvc_root: Path, *, speaker_id: int = SPEAKER_ID) -> list[str]:
    root = Path(rvc_root).resolve()
    line = "|".join(
        [
            str(root / "logs/mute/0_gt_wavs/mute32k.wav"),
            str(root / "logs/mute/3_feature768/mute.npy"),
            str(root / "logs/mute/2a_f0/mute.wav.npy"),
            str(root / "logs/mute/2b-f0nsf/mute.wav.npy"),
            str(speaker_id),
        ]
    )
    return [line, line]


def write_filelist(exp_dir: Path, rvc_root: Path) -> Path:
    rows = build_filelist(exp_dir) + mute_rows(rvc_root)
    # Upstream WebUI shuffles; the Lab deliberately sorts real rows and appends two
    # identical mute rows so the handover input is deterministic. Training itself
    # shuffles samples per epoch from seed 1234.
    out = Path(exp_dir) / "filelist.txt"
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return out


def expected_training_argv() -> list[str]:
    return [
        "train/train.py",
        "-e", EXPERIMENT,
        "-sr", "32k",
        "-f0", "1",
        "-bs", str(BATCH_SIZE),
        "-g", str(GPU_ID),
        "-te", str(TOTAL_EPOCHS),
        "-se", str(SAVE_EVERY_EPOCHS),
        "-pg", "assets/pretrained_v2/f0G32k.pth",
        "-pd", "assets/pretrained_v2/f0D32k.pth",
        "-l", "1",
        "-c", "0",
        "-sw", "1",
        "-v", VERSION,
    ]
