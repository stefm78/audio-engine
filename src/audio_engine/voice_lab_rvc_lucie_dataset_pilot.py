"""Bounded neutral Lucie dataset pilot for learned-character RVC research.

The candidate texts and seeds are frozen before synthesis. The pilot is not a
production voice pack and does not authorize RVC training by itself.
"""
from __future__ import annotations

import hashlib

SELECTED_PAIR_RUN_ID = 32818950167
SELECTED_PAIR_ARTIFACT = "qwen3-contrast-selected-pair"
LUCIE_ANCHOR_SHA256 = "9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822"
CLAIRE_ANCHOR_SHA256 = "3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe"
QWEN_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
BASE_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
BASE_MODEL_REVISION = "74a6279626edc2d5a787d5b6467668eba0b86ef6"

# Deliberately neutral content: declarative sentences, varied consonants/vowels,
# numbers, liaison contexts and proper rhythm, with no acting instruction.
CANDIDATES = (
    ("n01", "Le matin, Lucie ouvre les volets et regarde la place encore tranquille."),
    ("n02", "Dans le carnet bleu, trois dates sont notées au crayon près de la marge."),
    ("n03", "Nous prendrons le train de neuf heures puis nous marcherons jusqu'au vieux pont."),
    ("n04", "Sur la table, une tasse, deux clés et quelques feuilles attendent depuis hier."),
    ("n05", "Je connais ce quartier depuis longtemps, même si certaines rues ont beaucoup changé."),
    ("n06", "Après le déjeuner, nous vérifierons les fenêtres avant de ranger les dossiers."),
    ("n07", "Le jardin descend doucement vers la rivière, entre les pierres claires et les arbres."),
    ("n08", "Vous trouverez la petite boîte en bois derrière les livres de la deuxième étagère."),
    ("n09", "Cette année, les travaux commencent en septembre et devraient finir avant décembre."),
    ("n10", "Quand la lumière baisse, les façades deviennent dorées puis la rue retrouve son calme."),
)


def seed_for(candidate_id: str) -> int:
    payload = f"rvc-lucie-neutral-pilot\0{candidate_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


def pilot_spec() -> dict:
    return {
        "schema": "rvc-lucie-neutral-dataset-pilot-v1",
        "role": "lucie",
        "source": "Qwen3 Base x-vector-only from human-qualified contrasted Lucie anchor",
        "selected_pair_run_id": SELECTED_PAIR_RUN_ID,
        "selected_pair_artifact": SELECTED_PAIR_ARTIFACT,
        "lucie_anchor_sha256": LUCIE_ANCHOR_SHA256,
        "claire_anchor_sha256": CLAIRE_ANCHOR_SHA256,
        "qwen_revision": QWEN_REVISION,
        "base_model": {"id": BASE_MODEL_ID, "revision": BASE_MODEL_REVISION},
        "candidates": [
            {"id": cid, "text": text, "seed": seed_for(cid)} for cid, text in CANDIDATES
        ],
        "candidate_count": len(CANDIDATES),
        "retries": 0,
        "emotion_instruction": False,
        "gates": {
            "technical": "finite mono/stereo speech, non-silent, unclipped, 1.5-10.0 s",
            "identity_per_accepted_clip": "independent WeSpeaker sim(Lucie) > sim(Claire)",
            "french_per_accepted_clip": "Whisper Small WER <= 0.20",
            "aggregate_french": "word-count-weighted WER <= 0.10",
            "accepted_duration_seconds": "30 <= total <= 60",
        },
        "training_authorized": False,
        "human_gate": False,
        "production_qualified": False,
    }
