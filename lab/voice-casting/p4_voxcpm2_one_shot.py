#!/usr/bin/env python3
"""P4 Sirens one-shot VoxCPM2 experiment.

This is deliberately scene-local. It preserves the immutable H1b-B P4 scene
and replaces only the five left/lead Siren utterances. No cloud TTS, no NUC,
no best-of-N, no post-verdict tuning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf
from pydub import AudioSegment
from voxcpm import VoxCPM

UPSTREAM_REVISION = "ee8161e9e1b7b082cb5721a3a9980da4204401e6"
MODEL_ID = "openbmb/VoxCPM2"
MODEL_REVISION = "32279effe8c19989596f05d353d1447f51d9e915"
MODEL_LICENSE = "Apache-2.0"

BASELINE_AUDIO_SHA256 = "14f325e3a1404c260c9a5139b85bcb5267cdd91a60c2458ea80bd66f3d75365d"
BASELINE_REPORT_SHA256 = "8f3d2e0a63752d09974c2553c25f28fe9e0b5c6ec800fb734d16ae859f65aa06"
CLAIRE_SHA256 = "3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe"

CFG_VALUE = 2.0
INFERENCE_TIMESTEPS = 10
SEED_BASE = 2026090100
PAN = -0.16

TARGETS = {
    2: ("Sirène gauche", "Ulysse d’Ithaque."),
    4: ("Sirène gauche", "Troie."),
    6: ("Sirène gauche", "Pourquoi tu as crié ton nom."),
    8: ("Sirène gauche", "…ou être connu ?"),
    12: ("Sirène gauche", "Nous savons déjà."),
}

VARIANTS = {
    "p4-voxcpm2-a": {
        "title": "Invitation intime et intelligente",
        "control": (
            "An intimate, intelligent invitation addressed personally to Ulysses. "
            "Warm recognition, quiet curiosity and genuine pleasure in understanding him. "
            "Compelling and close, but never sexualised, never mystical, never theatrical, "
            "never whispered and never sung. Natural adult French diction."
        ),
    },
    "p4-voxcpm2-b": {
        "title": "Certitude calme et magnétique",
        "control": (
            "Quietly delighted certainty addressed personally to Ulysses, as if you already know "
            "the choices he cannot admit. Magnetic through understanding and calm confidence, "
            "not seduction. No mysticism, no chant, no singing, no breathy whisper, no caricature. "
            "Natural adult French diction."
        ),
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(seg: AudioSegment, target_dbfs: float = -20.0) -> AudioSegment:
    seg = seg.set_frame_rate(24000).set_channels(2)
    if math.isfinite(seg.dBFS):
        seg = seg.apply_gain(max(-8.0, min(8.0, target_dbfs - seg.dBFS)))
    return seg


def technical_gate(path: Path) -> dict:
    y, sr = sf.read(path, dtype="float32", always_2d=False)
    y = np.asarray(y, dtype=np.float32)
    if y.ndim == 2:
        y = y.mean(axis=1)
    finite = bool(np.isfinite(y).all())
    duration = float(len(y) / sr) if sr else 0.0
    rms = float(np.sqrt(np.mean(np.square(y)))) if len(y) else 0.0
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    passed = finite and 0.12 <= duration <= 12.0 and 0.002 <= rms <= 0.5 and peak <= 1.0
    return {
        "status": "PASS" if passed else "REJECT",
        "sample_rate": int(sr),
        "duration_seconds": duration,
        "rms": rms,
        "peak": peak,
        "finite": finite,
    }


def validate_baseline(audio_path: Path, report_path: Path, claire_path: Path):
    if sha256(audio_path) != BASELINE_AUDIO_SHA256:
        raise SystemExit("P4_BASELINE_AUDIO_SHA_REJECT")
    if sha256(report_path) != BASELINE_REPORT_SHA256:
        raise SystemExit("P4_BASELINE_REPORT_SHA_REJECT")
    if sha256(claire_path) != CLAIRE_SHA256:
        raise SystemExit("CLAIRE_REFERENCE_SHA_REJECT")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("variant") != "p4-b":
        raise SystemExit("P4_BASELINE_VARIANT_REJECT")
    by_i = {int(s["i"]): s for s in report["segments"]}
    for i, (speaker, text) in TARGETS.items():
        s = by_i.get(i)
        if not s or s["speaker"] != speaker or s["text"] != text:
            raise SystemExit(f"P4_BASELINE_BINDING_REJECT:{i}")
    return report


def render_variant(model, baseline, report, claire_path: Path, out: Path, variant_id: str, spec: dict):
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    slots_dir = out / "slots"
    slots_dir.mkdir(parents=True, exist_ok=True)

    replacement_audio = {}
    slot_reports = []

    for i, (speaker, text) in TARGETS.items():
        seed = SEED_BASE + i
        raw_path = raw_dir / f"{variant_id}-{i:02d}.wav"
        final_text = f"({spec['control']}){text}"
        wav = model.generate(
            text=final_text,
            reference_wav_path=str(claire_path),
            cfg_value=CFG_VALUE,
            inference_timesteps=INFERENCE_TIMESTEPS,
            normalize=False,
            denoise=False,
            retry_badcase=False,
            seed=seed,
        )
        sf.write(raw_path, wav, int(model.tts_model.sample_rate))
        gate = technical_gate(raw_path)
        if gate["status"] != "PASS":
            raise SystemExit(f"P4_SLOT_TECHNICAL_REJECT:{variant_id}:{i}:{json.dumps(gate)}")

        rendered = normalize(AudioSegment.from_file(raw_path)).pan(PAN)
        slot_path = slots_dir / f"{variant_id}-{i:02d}.wav"
        rendered.export(slot_path, format="wav")
        replacement_audio[i] = rendered
        slot_reports.append(
            {
                "i": i,
                "speaker": speaker,
                "text": text,
                "seed": seed,
                "control": spec["control"],
                "raw_sha256": sha256(raw_path),
                "slot_sha256": sha256(slot_path),
                "technical_gate": gate,
                "candidate_audio_ms": len(rendered),
            }
        )

    final = AudioSegment.empty()
    cursor = 0
    preserved = []
    for seg in report["segments"]:
        i = int(seg["i"])
        audio_ms = int(seg["audio_ms"])
        pause_ms = int(seg.get("pause_ms", 0))
        speech_end = cursor + audio_ms
        slot_end = speech_end + pause_ms
        if i in replacement_audio:
            final += replacement_audio[i]
            if pause_ms:
                final += baseline[speech_end:slot_end]
        else:
            frozen = baseline[cursor:slot_end]
            final += frozen
            preserved.append(
                {
                    "i": i,
                    "speaker": seg["speaker"],
                    "text": seg["text"],
                    "audio_ms": audio_ms,
                    "pause_ms": pause_ms,
                    "preserved_pcm_sha256": hashlib.sha256(frozen.raw_data).hexdigest(),
                }
            )
        cursor = slot_end

    if cursor < len(baseline):
        final += baseline[cursor:]

    candidate = out / f"{variant_id}.mp3"
    final.export(candidate, format="mp3", bitrate="128k")
    return {
        "variant": variant_id,
        "title": spec["title"],
        "candidate_sha256": sha256(candidate),
        "duration_seconds": len(final) / 1000.0,
        "replacement_indices": sorted(TARGETS),
        "preserved_indices": [p["i"] for p in preserved],
        "slots": slot_reports,
        "preserved": preserved,
    }


def write_review(out: Path, results: list[dict]):
    cards = []
    for r in results:
        cards.append(
            f"""<section class="card"><h2>{r['title']}</h2>
<audio controls preload="metadata" src="{r['variant']}.mp3"></audio>
<fieldset><legend>Attraction</legend>
<label><input type="radio" name="{r['variant']}-attraction" value="PASS"> PASS — j'ai envie qu'Ulysse continue d'écouter</label>
<label><input type="radio" name="{r['variant']}-attraction" value="BORDERLINE"> BORDERLINE</label>
<label><input type="radio" name="{r['variant']}-attraction" value="FAIL"> FAIL</label></fieldset>
<fieldset><legend>Français</legend>
<label><input type="radio" name="{r['variant']}-french" value="PASS"> PASS</label>
<label><input type="radio" name="{r['variant']}-french" value="FAIL"> FAIL</label></fieldset>
<fieldset><legend>Cliché</legend>
<label><input type="radio" name="{r['variant']}-cliche" value="NONE"> AUCUN</label>
<label><input type="radio" name="{r['variant']}-cliche" value="LIGHT"> LÉGER</label>
<label><input type="radio" name="{r['variant']}-cliche" value="HEAVY"> FORT</label></fieldset>
<fieldset><legend>Polyphonie / adresse</legend>
<label><input type="radio" name="{r['variant']}-polyphony" value="PASS"> polyphonie utile PASS</label>
<label><input type="radio" name="{r['variant']}-polyphony" value="FAIL"> polyphonie FAIL</label>
<label><input type="radio" name="{r['variant']}-addressed" value="PASS"> dialogue adressé à Ulysse PASS</label>
<label><input type="radio" name="{r['variant']}-addressed" value="FAIL"> adresse à Ulysse FAIL</label></fieldset></section>"""
        )
    html = f"""<!doctype html><html lang="fr"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Odyssée P4 — VoxCPM2 one-shot</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.45}}.card{{border:1px solid #999;border-radius:14px;padding:1rem;margin:1rem 0}}audio{{width:100%}}label{{display:block;margin:.5rem 0}}fieldset{{margin:1rem 0}}button{{padding:.7rem 1rem}}</style>
<h1>P4 — Sirènes VoxCPM2</h1>
<p>Deux directions préenregistrées, même modèle, mêmes seeds, même scène H1b-B. Seule la Sirène gauche est remplacée.</p>
{''.join(cards)}
<label>Préférence globale <select id="pref"><option value="">—</option><option>A</option><option>B</option><option>aucune</option></select></label>
<p><button id="export">Copier le verdict</button></p>
<textarea id="out" rows="12" style="width:100%"></textarea>
<script>
document.getElementById('export').onclick=()=>{{
 const data={{schema:'odyssee-p4-voxcpm2-human-v1',preference:document.getElementById('pref').value,variants:{{}}}};
 for(const id of ['p4-voxcpm2-a','p4-voxcpm2-b']){{
  data.variants[id]={{}};
  for(const k of ['attraction','french','cliche','polyphony','addressed']){{
   const n=document.querySelector('input[name="'+id+'-'+k+'"]:checked');
   data.variants[id][k]=n?n.value:null;
  }}
 }}
 const text=JSON.stringify(data,null,2);document.getElementById('out').value=text;navigator.clipboard?.writeText(text);
}};
</script></html>"""
    (out / "index.html").write_text(html, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--baseline-audio", required=True)
    ap.add_argument("--baseline-report", required=True)
    ap.add_argument("--claire", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    baseline_audio = Path(args.baseline_audio)
    baseline_report = Path(args.baseline_report)
    claire = Path(args.claire)
    report = validate_baseline(baseline_audio, baseline_report, claire)

    baseline = AudioSegment.from_file(baseline_audio).set_frame_rate(24000).set_channels(2)
    model = VoxCPM.from_pretrained(
        args.model_dir,
        load_denoiser=False,
        optimize=False,
        device="cpu",
    )

    results = [
        render_variant(model, baseline, report, claire, out, variant_id, spec)
        for variant_id, spec in VARIANTS.items()
    ]
    manifest = {
        "schema": "odyssee-p4-voxcpm2-one-shot-v1",
        "status": "MACHINE_PASS",
        "cloud_tts": False,
        "nuc_required": False,
        "baseline": {
            "repo": "stefm78/recit-audioguide",
            "release": "odyssee-h1b-corrective-review-v1",
            "variant": "p4-b",
            "audio_sha256": BASELINE_AUDIO_SHA256,
            "report_sha256": BASELINE_REPORT_SHA256,
        },
        "reference": {
            "source": "voice-lab-reference-pack-v1/reference-claire.wav",
            "sha256": CLAIRE_SHA256,
        },
        "provider": {
            "runtime": "OpenBMB/VoxCPM",
            "upstream_revision": UPSTREAM_REVISION,
            "model": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "license": MODEL_LICENSE,
        },
        "parameters": {
            "cfg_value": CFG_VALUE,
            "inference_timesteps": INFERENCE_TIMESTEPS,
            "seed_base": SEED_BASE,
            "seed_rule": "seed_base + H1b segment index",
            "retry_badcase": False,
            "normalize_model_output": False,
            "denoise": False,
        },
        "results": results,
        "human_gate": "PENDING",
        "p4_pass_requires": [
            "attraction_PASS",
            "french_PASS",
            "polyphony_PASS",
            "cliche_NONE_OR_LIGHT",
            "addressed_PASS",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_review(out, results)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
