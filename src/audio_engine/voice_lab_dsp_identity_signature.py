"""Deterministic post-TTS identity signature experiment.

This Lab-only experiment does not synthesize any speech. It reuses the exact human-
evaluated Qwen3 contrasted-emotion bundle and applies one mild, fixed spectral EQ
signature per character to both the neutral reference and every emotional line.
The goal is to add a stable perceptual landmark that survives emotional prosody.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg

from .voice_casting_distance import compare_anchors

SCHEMA = "dsp-identity-signature-v1"
SOURCE_RUN_ID = 32823632721
SOURCE_ARTIFACT = "voice-casting-qwen3-contrast-emotion-killer-recovery"
BLIND_SEED = 2026082512

SOURCE_SHA256 = {
    "reference-claire.wav": "3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe",
    "reference-lucie.wav": "9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822",
    "clips/claire--panic.wav": "ac92fd1f8346b981ac7518e1e698cf8b1c31a96dff069ad60a2d017a17ff9d7f",
    "clips/lucie--panic.wav": "8168d32c7a1ee81485396ff426f1fa6ad306a54765d60351e10dbe7231da3a09",
    "clips/claire--wonder.wav": "da173789bff0c42bbf0f306a581c2d5a9559de0bb98114381397b71526360c8e",
    "clips/lucie--wonder.wav": "f18ee8d13204d1a1c0ccc6e8621edf107fff8236946a174aaa6d95e7b7ef1788",
    "clips/claire--sadness-contained.wav": "d2091868592c3c8691c2c0c6a39adaa3613d4941d087c36e4be69e5395a19c84",
    "clips/lucie--sadness-contained.wav": "6190b6c45aa4efeea24d55e8f048d0af1dc2199d73b95a974c5b94cbee71b131",
}

# Bounded, deliberately mild spectral signatures. No pitch, formant, tempo or
# duration manipulation is allowed in this experiment.
PROFILES = {
    "claire": (
        (300, 3.0),
        (700, 1.5),
        (2500, -2.5),
        (3500, -1.5),
    ),
    "lucie": (
        (300, -1.5),
        (700, -1.0),
        (2500, 3.0),
        (3500, 2.0),
    ),
}

CASES = (
    {
        "id": "panic",
        "label": "Panique urgente",
        "text": "Vite ! Ils arrivent ! Fermez la porte !",
    },
    {
        "id": "wonder",
        "label": "Émerveillement",
        "text": "Regardez... La brume se lève. On voit toute la vallée, jusqu'aux montagnes.",
    },
    {
        "id": "sadness-contained",
        "label": "Tristesse contenue",
        "text": "Il est parti avant l'aube. Je savais que ce moment viendrait, mais pas si tôt.",
    },
)

# Diagnostics are a cheap prefilter only. Human ABX remains the identity gate.
SOURCE_DISTANCE = {
    "neutral": 84.226,
    "panic": 46.644,
    "wonder": 63.420,
    "sadness-contained": 33.090,
}
MIN_PANIC_GAIN = 2.0
MAX_OTHER_DROP = 5.0


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate_profiles() -> None:
    if set(PROFILES) != {"claire", "lucie"}:
        raise ValueError("DSP profiles must define Claire and Lucie")
    for role, bands in PROFILES.items():
        if len(bands) != 4:
            raise ValueError(f"{role} profile must contain exactly four EQ bands")
        for frequency, gain_db in bands:
            if not 150 <= float(frequency) <= 5000:
                raise ValueError(f"{role} EQ frequency outside bounded range")
            if abs(float(gain_db)) > 3.0:
                raise ValueError(f"{role} EQ gain exceeds +/-3 dB")


def filter_chain(role: str) -> str:
    validate_profiles()
    if role not in PROFILES:
        raise ValueError(f"unknown DSP role: {role}")
    # Common -3 dB headroom prevents boosted EQ bands from clipping. It is
    # deliberately identical for both characters and therefore not an identity cue.
    parts = ["volume=-3dB"]
    parts.extend(
        f"equalizer=f={int(frequency)}:t=q:w=1:g={gain_db:g}"
        for frequency, gain_db in PROFILES[role]
    )
    chain = ",".join(parts)
    forbidden = ("rubberband", "atempo", "asetrate", "aresample=", "pitch", "formant")
    if any(token in chain.lower() for token in forbidden):
        raise AssertionError("identity signature must not manipulate pitch/formant/tempo")
    return chain


def _wav_shape(path: Path) -> tuple[int, int, int]:
    with wave.open(str(path), "rb") as stream:
        return stream.getframerate(), stream.getnchannels(), stream.getnframes()


def apply_signature(input_path, output_path, role: str, *, ffmpeg_exe: str | None = None) -> dict:
    input_path, output_path = Path(input_path), Path(output_path)
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    ffmpeg_exe = ffmpeg_exe or imageio_ffmpeg.get_ffmpeg_exe()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    before = _wav_shape(input_path)
    command = [
        ffmpeg_exe,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-fflags",
        "+bitexact",
        "-i",
        str(input_path),
        "-af",
        filter_chain(role),
        "-ac",
        "1",
        "-ar",
        str(before[0]),
        "-c:a",
        "pcm_s16le",
        "-flags:a",
        "+bitexact",
        "-map_metadata",
        "-1",
        str(output_path),
    ]
    subprocess.run(command, check=True)
    after = _wav_shape(output_path)
    if before[0] != after[0] or after[1] != 1:
        raise ValueError("DSP signature changed sample rate or channel contract")
    if abs(before[2] - after[2]) > 1:
        raise ValueError("DSP signature changed duration")
    return {
        "role": role,
        "filter": filter_chain(role),
        "input_sha256": _sha256(input_path),
        "output_sha256": _sha256(output_path),
        "sample_rate": after[0],
        "frames": after[2],
    }


def validate_source_bundle(source_dir) -> dict:
    source_dir = Path(source_dir)
    manifest_path = source_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "success" or manifest.get("trial_count") != 3:
        raise ValueError("source bundle is not the qualified technical emotion bundle")
    for relative, expected in SOURCE_SHA256.items():
        path = source_dir / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"source hash mismatch for {relative}: {actual}")
    return manifest


def _distance_set(root: Path) -> dict:
    return {
        "neutral": compare_anchors(root / "reference-claire.wav", root / "reference-lucie.wav"),
        **{
            case["id"]: compare_anchors(
                root / "clips" / f"claire--{case['id']}.wav",
                root / "clips" / f"lucie--{case['id']}.wav",
            )
            for case in CASES
        },
    }


def diagnostic_gate(distances: dict) -> dict:
    scores = {key: float(value["score"]) for key, value in distances.items()}
    panic_gain = scores["panic"] - SOURCE_DISTANCE["panic"]
    other_drops = {
        key: SOURCE_DISTANCE[key] - scores[key]
        for key in ("neutral", "wonder", "sadness-contained")
    }
    eligible = panic_gain >= MIN_PANIC_GAIN and all(drop <= MAX_OTHER_DROP for drop in other_drops.values())
    return {
        "eligible": eligible,
        "panic_gain": round(panic_gain, 3),
        "minimum_panic_gain": MIN_PANIC_GAIN,
        "other_drops": {key: round(value, 3) for key, value in other_drops.items()},
        "maximum_other_drop": MAX_OTHER_DROP,
        "claim": "prefilter-only-not-speaker-identity-qualification",
    }


def build_bundle(source_dir, output_dir, *, seed: int = BLIND_SEED) -> dict:
    validate_profiles()
    source_dir, output_dir = Path(source_dir), Path(output_dir)
    source_manifest = validate_source_bundle(source_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "clips").mkdir(exist_ok=True)

    transformations = {}
    for role in ("claire", "lucie"):
        ref_name = f"reference-{role}.wav"
        transformations[ref_name] = apply_signature(source_dir / ref_name, output_dir / ref_name, role)
        for case in CASES:
            relative = f"clips/{role}--{case['id']}.wav"
            transformations[relative] = apply_signature(source_dir / relative, output_dir / relative, role)

    distances = _distance_set(output_dir)
    prefilter = diagnostic_gate(distances)
    if not prefilter["eligible"]:
        status = "rejected"
        trials = []
    else:
        status = "success"
        rnd = random.Random(seed)
        trials = []
        for case in CASES:
            options = [
                {"role": role, "file": f"clips/{role}--{case['id']}.wav"}
                for role in ("claire", "lucie")
            ]
            rnd.shuffle(options)
            trials.append(
                {
                    "id": case["id"],
                    "label": case["label"],
                    "text": case["text"],
                    "references": [
                        {"role": "claire", "label": "Référence 1", "file": "reference-claire.wav"},
                        {"role": "lucie", "label": "Référence 2", "file": "reference-lucie.wav"},
                    ],
                    "options": [
                        {"letter": letter, **option} for letter, option in zip("AB", options)
                    ],
                    "correct_reference_for_A": "Référence 1" if options[0]["role"] == "claire" else "Référence 2",
                }
            )

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_version = subprocess.run(
        [ffmpeg_exe, "-version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]
    manifest = {
        "schema": SCHEMA,
        "status": status,
        "architecture": "direct-voicedesign-plus-deterministic-spectral-signature",
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact": SOURCE_ARTIFACT,
        "source_manifest_schema": source_manifest.get("schema"),
        "source_sha256": dict(SOURCE_SHA256),
        "profiles": {
            role: [{"frequency_hz": f, "gain_db": g} for f, g in bands]
            for role, bands in PROFILES.items()
        },
        "common_headroom_db": -3.0,
        "ffmpeg": ffmpeg_version,
        "transformations": transformations,
        "distance_diagnostics_not_a_gate": distances,
        "prefilter": prefilter,
        "trial_count": len(trials),
        "gates": {
            "identity": "3/3 blind A-to-reference mappings correct",
            "french": "both-good on all 3 screens",
            "acting": "6/6 yes; DSP must not degrade the already human-qualified acting",
        },
        "claims": {
            "dsp_identity_qualified": False,
            "long_form_qualified": False,
            "age_lineage": False,
            "production_promoted": False,
        },
        "trials": trials,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if status == "success":
        _write_player(output_dir, trials)
    return manifest


def _write_player(output_dir: Path, trials) -> None:
    public = [
        {
            "id": t["id"],
            "label": t["label"],
            "text": t["text"],
            "references": t["references"],
            "options": [{"letter": o["letter"], "file": o["file"]} for o in t["options"]],
        }
        for t in trials
    ]
    public_json = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    mapping_json = json.dumps({"trials": trials}, ensure_ascii=False).replace("</", "<\\/")
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Signature vocale stable</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}.card{{border:1px solid #999;border-radius:12px;padding:1rem}}audio{{width:100%}}label{{display:block;margin:.55rem 0}}fieldset{{border:0;padding:0;margin:1rem 0}}legend{{font-weight:700;margin-bottom:.35rem}}button{{padding:.7rem 1rem;margin:.4rem}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><h1>Signature vocale stable</h1><p>3 écrans. Écoutez les deux références, puis A et B. Tous les choix sont visibles.</p><main id="app"></main><script>const trials={public_json};const mapping={mapping_json};let i=0;const responses={{}};function audio(src){{return `<audio controls preload="none" src="${{src}}"></audio>`}}function radio(name,value,label){{return `<label><input type="radio" name="${{name}}" value="${{value}}"> ${{label}}</label>`}}function checked(name){{const el=document.querySelector(`input[name="${{name}}"]:checked`);return el?el.value:''}}function render(){{const t=trials[i];document.getElementById('app').innerHTML=`<h2>${{i+1}}/3 — ${{t.label}}</h2><p>${{t.text}}</p><div class="grid"><div class="card"><h3>Référence 1</h3>${{audio(t.references[0].file)}}<h3>Référence 2</h3>${{audio(t.references[1].file)}}</div><div class="card"><h3>A</h3>${{audio(t.options[0].file)}}<h3>B</h3>${{audio(t.options[1].file)}}</div></div><fieldset><legend>À quelle référence correspond A ?</legend>${{radio('identity','Référence 1','Référence 1')}}${{radio('identity','Référence 2','Référence 2')}}${{radio('identity','uncertain','Impossible à distinguer')}}</fieldset><fieldset><legend>Le jeu de A correspond-il à l'intention ?</legend>${{radio('actingA','yes','Oui')}}${{radio('actingA','no','Non')}}</fieldset><fieldset><legend>Le jeu de B correspond-il à l'intention ?</legend>${{radio('actingB','yes','Oui')}}${{radio('actingB','no','Non')}}</fieldset><fieldset><legend>Français</legend>${{radio('french','both-good','Les deux sont bons')}}${{radio('french','a-defect','Défaut éliminatoire sur A')}}${{radio('french','b-defect','Défaut éliminatoire sur B')}}${{radio('french','both-defect','Défaut éliminatoire sur les deux')}}</fieldset><p><button onclick="save()">${{i===trials.length-1?'Terminer':'Suivant'}}</button></p>`}}function save(){{const identity=checked('identity'),actingA=checked('actingA'),actingB=checked('actingB'),french=checked('french');if(!identity||!actingA||!actingB||!french){{alert('Répondez aux quatre questions.');return}}responses[trials[i].id]={{identity,actingA,actingB,french}};i++;if(i<trials.length)render();else finish()}}function finish(){{document.getElementById('app').innerHTML=`<h2>Terminé</h2><p>Exportez le JSON et envoyez-le dans la conversation.</p><button onclick="download()">Exporter le JSON</button>`}}function download(){{const blob=new Blob([JSON.stringify({{schema:'dsp-identity-signature-results-v1',exported_at:new Date().toISOString(),responses,mapping}},null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='dsp-identity-signature-results.json';a.click();URL.revokeObjectURL(a.href)}}render();</script></body></html>'''
    if "<select" in html.lower():
        raise AssertionError("Voice Lab questionnaires must be radio-only")
    (output_dir / "index.html").write_text(html, encoding="utf-8")
