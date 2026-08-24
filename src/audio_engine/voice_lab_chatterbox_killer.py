"""Minimal blind killer test for Chatterbox Multilingual V3.

The purpose is to decide whether the fully open/local model deserves a larger
benchmark before we spend more compute or add semantic-instruction models.
"""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from .providers.chatterbox_lab import ChatterboxLabProvider
from .providers.edge import EdgeProvider


REFERENCE_VOICE = "fr-FR-VivienneMultilingualNeural"
REFERENCE_TEXT = (
    "À l'aube, personne dans la ville ne savait encore ce qui allait se produire. "
    "Approchez. Ce que je vais vous dire ne doit sortir d'ici sous aucun prétexte."
)

CASES = (
    {
        "id": "panic",
        "intention": "panique",
        "text": "Vite ! Ils arrivent ! Fermez la porte !",
    },
    {
        "id": "mystery",
        "intention": "mystère",
        "text": "Depuis trois nuits, la même lumière apparaît derrière cette fenêtre condamnée.",
    },
)

TREATMENTS = (
    {
        "id": "edge-baseline",
        "provider": "edge",
    },
    {
        "id": "chatterbox-neutral",
        "provider": "chatterbox",
        "exaggeration": 0.5,
        "cfg_weight": 0.5,
    },
    {
        "id": "chatterbox-dramatic",
        "provider": "chatterbox",
        "exaggeration": 0.8,
        "cfg_weight": 0.3,
    },
    {
        "id": "chatterbox-strong",
        "provider": "chatterbox",
        "exaggeration": 1.2,
        "cfg_weight": 0.3,
    },
)


def experiment_spec():
    return {
        "version": 1,
        "kind": "chatterbox-v3-killer-test",
        "production_promotion": False,
        "reference": {
            "voice": REFERENCE_VOICE,
            "text": REFERENCE_TEXT,
            "source": "synthetic-edge-reference",
        },
        "model": {
            "family": "Chatterbox Multilingual",
            "t3_model": "v3",
            "language_id": "fr",
            "optional_dependency": True,
        },
        "cases": [
            {**case, "treatments": [dict(item) for item in TREATMENTS]}
            for case in CASES
        ],
        "decision": {
            "promising_if": (
                "Chatterbox produces at least one artistically acceptable winner "
                "over Edge while preserving French pronunciation and recognizable identity."
            ),
            "next_if_promising": "expand to two voices and four hard intentions",
            "next_if_not_promising": "skip directly to semantic-instruction challenger",
        },
    }


def _convert_reference(mp3_path: Path, wav_path: Path) -> None:
    subprocess.run(
        [
            get_ffmpeg_exe(),
            "-y",
            "-i",
            str(mp3_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def render_experiment(output_dir, *, edge=None, chatterbox=None):
    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    edge = edge or EdgeProvider()
    reference_mp3 = output_dir / "reference-edge.mp3"
    reference_wav = output_dir / "reference-edge-16k.wav"
    edge.synthesize(
        {
            "text": REFERENCE_TEXT,
            "voice": REFERENCE_VOICE,
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
            "language_locale": "fr-FR",
        },
        reference_mp3,
    )
    _convert_reference(reference_mp3, reference_wav)

    chatterbox = chatterbox or ChatterboxLabProvider(device="cpu", t3_model="v3")
    spec = experiment_spec()
    rendered = []
    failures = []

    for case in spec["cases"]:
        for treatment in case["treatments"]:
            filename = f"{case['id']}--{treatment['id']}.wav"
            path = clips_dir / filename
            try:
                if treatment["provider"] == "edge":
                    mp3_path = clips_dir / f"{case['id']}--edge-baseline.mp3"
                    edge.synthesize(
                        {
                            "text": case["text"],
                            "voice": REFERENCE_VOICE,
                            "rate": "+0%",
                            "pitch": "+0Hz",
                            "volume": "+0%",
                            "language_locale": "fr-FR",
                        },
                        mp3_path,
                    )
                    _convert_reference(mp3_path, path)
                    mp3_path.unlink(missing_ok=True)
                else:
                    chatterbox.synthesize(
                        {
                            "text": case["text"],
                            "audio_prompt_path": str(reference_wav),
                            "language_id": "fr",
                            "exaggeration": treatment["exaggeration"],
                            "cfg_weight": treatment["cfg_weight"],
                            "temperature": 0.8,
                            "seed": 20260824,
                        },
                        path,
                    )
                rendered.append(
                    {
                        "case_id": case["id"],
                        "treatment_id": treatment["id"],
                        "file": f"clips/{filename}",
                    }
                )
            except Exception as exc:
                failures.append(
                    {
                        "case_id": case["id"],
                        "treatment_id": treatment["id"],
                        "error": str(exc),
                    }
                )

    result = {
        **spec,
        "status": "success" if not failures else ("partial" if rendered else "failed"),
        "rendered_count": len(rendered),
        "failure_count": len(failures),
        "rendered": rendered,
        "failures": failures,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_blind_player(result, output_dir)
    return result


def write_blind_player(manifest, output_dir, *, seed=20260824):
    output_dir = Path(output_dir)
    rendered = {
        (item["case_id"], item["treatment_id"]): item["file"]
        for item in manifest.get("rendered", [])
    }
    randomizer = random.Random(seed)
    trials = []
    for case in manifest["cases"]:
        options = []
        for treatment in case["treatments"]:
            file = rendered.get((case["id"], treatment["id"]))
            if file:
                options.append({**treatment, "file": file})
        if len(options) != len(case["treatments"]):
            continue
        randomizer.shuffle(options)
        trials.append(
            {
                "id": case["id"],
                "intention": case["intention"],
                "text": case["text"],
                "options": [
                    {"letter": letter, **option}
                    for letter, option in zip("ABCD", options)
                ],
            }
        )

    payload = json.dumps({"version": 1, "trials": trials}, ensure_ascii=False).replace("</", "<\\/")
    html = f"""<!doctype html><html lang='fr'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Chatterbox V3 — killer test</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.45}}.card{{border:1px solid #888;border-radius:12px;padding:1rem;margin:1rem 0}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}audio{{width:100%}}button{{padding:.7rem 1rem;margin:.25rem}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style>
<h1>Chatterbox V3 — killer test</h1><p>Deux décisions seulement. Choisis la variante qui joue le mieux l'intention tout en restant naturelle et correctement française.</p>
<p id='progress'></p><div id='app'></div><button id='export'>Exporter les résultats JSON</button>
<script>const data={payload};let i=0;const answers={{}};const app=document.getElementById('app');const progress=document.getElementById('progress');
function render(){{const t=data.trials[i];progress.textContent=t?`Cas ${{i+1}} / ${{data.trials.length}} · ${{t.intention}}`:'Test terminé';if(!t){{app.innerHTML='<p>Exportez les résultats.</p>';return;}}const players=t.options.map(o=>`<div><h3>${{o.letter}}</h3><audio controls preload='none' src='${{o.file}}'></audio></div>`).join('');const buttons=t.options.map(o=>`<button data-v='${{o.letter}}'>${{o.letter}} est meilleure</button>`).join('');app.innerHTML=`<div class='card'><h2>${{t.intention}}</h2><p><em>${{t.text}}</em></p><div class='grid'>${{players}}</div><p>${{buttons}}<button data-v='none'>Aucune acceptable</button><button data-v='invalid-pronunciation'>Prononciation invalide</button></p></div>`;app.querySelectorAll('button[data-v]').forEach(b=>b.onclick=()=>{{answers[t.id]=b.dataset.v;i++;render();}});}}
document.getElementById('export').onclick=()=>{{const result={{schema:'voice-casting-chatterbox-killer-v1',exported_at:new Date().toISOString(),responses:answers,mapping:data.trials}};const blob=new Blob([JSON.stringify(result,null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='voice-casting-chatterbox-killer-results.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}};render();</script></html>"""
    (output_dir / "index.html").write_text(html, encoding="utf-8")
    return {"trial_count": len(trials)}
