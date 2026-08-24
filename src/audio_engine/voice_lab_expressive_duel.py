"""Blind expressive-provider experiment for the Voice Casting Lab.

This experiment is deliberately separate from production casting. It answers two
questions before Azure Speech can be promoted anywhere:

1. Does a native Azure speaking style improve the *same* French base voice over
   the current Edge path?
2. Do the French MAI-Voice-2 voices materially raise the acting ceiling on the
   hard intentions that Edge struggled with?
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from .providers.azure_speech_lab import AzureSpeechLabProvider
from .providers.edge import EdgeProvider


CONTROLLED_CASES = (
    {
        "id": "controlled-denise-panic",
        "voice": "fr-FR-DeniseNeural",
        "intention": "panic",
        "text": "Vite ! Ils arrivent ! Fermez la porte !",
        "style": "excited",
    },
    {
        "id": "controlled-denise-mystery",
        "voice": "fr-FR-DeniseNeural",
        "intention": "mystery",
        "text": "Depuis trois nuits, la même lumière apparaît derrière cette fenêtre condamnée.",
        "style": "whispering",
    },
    {
        "id": "controlled-henri-wonder",
        "voice": "fr-FR-HenriNeural",
        "intention": "wonder",
        "text": "Regardez... On distingue toute la vallée, jusqu'aux montagnes derrière la brume.",
        "style": "cheerful",
    },
    {
        "id": "controlled-henri-sadness",
        "voice": "fr-FR-HenriNeural",
        "intention": "sadness-contained",
        "text": "Il était mon frère. Je n'en parlerai pas davantage.",
        "style": "sad",
    },
)


MAI_VOICES = (
    "fr-FR-Soleil:MAI-Voice-2",
    "fr-FR-Marc:MAI-Voice-2",
)


HARD_CASES = (
    {
        "intention": "panic",
        "text": "Vite ! Ils arrivent ! Fermez la porte !",
        "treatments": (
            ("baseline", None, None),
            ("fearful", "fearful", 1.0),
            ("fearful-strong", "fearful", 1.5),
            ("shouting-light", "shouting", 0.8),
        ),
    },
    {
        "intention": "mystery",
        "text": "Depuis trois nuits, la même lumière apparaît derrière cette fenêtre condamnée.",
        "treatments": (
            ("baseline", None, None),
            ("whispering", "whispering", 1.0),
            ("whispering-strong", "whispering", 1.5),
            ("softvoice", "softvoice", 1.0),
        ),
    },
    {
        "intention": "polite-threat",
        "text": "Je vous conseille très sincèrement de reconsidérer votre réponse.",
        "treatments": (
            ("baseline", None, None),
            ("determined", "determined", 1.0),
            ("determined-strong", "determined", 1.5),
            ("angry-light", "angry", 0.6),
        ),
    },
    {
        "intention": "wonder",
        "text": "Regardez... On distingue toute la vallée, jusqu'aux montagnes derrière la brume.",
        "treatments": (
            ("baseline", None, None),
            ("surprised-light", "surprised", 0.8),
            ("surprised", "surprised", 1.2),
            ("excited-light", "excited", 0.8),
        ),
    },
)


def experiment_spec():
    cases = []
    for item in CONTROLLED_CASES:
        cases.append({
            "id": item["id"],
            "kind": "controlled-same-base-voice",
            "voice": item["voice"],
            "intention": item["intention"],
            "text": item["text"],
            "options": [
                {"id": "edge-baseline", "provider": "edge"},
                {"id": "azure-baseline", "provider": "azure"},
                {"id": "azure-style", "provider": "azure", "style": item["style"], "styledegree": 1.0},
                {"id": "azure-style-strong", "provider": "azure", "style": item["style"], "styledegree": 1.5},
            ],
        })

    for voice in MAI_VOICES:
        for hard in HARD_CASES:
            cases.append({
                "id": f"mai-{voice.split(':', 1)[0]}-{hard['intention']}",
                "kind": "mai-ceiling",
                "voice": voice,
                "intention": hard["intention"],
                "text": hard["text"],
                "options": [
                    {
                        "id": treatment_id,
                        "provider": "azure",
                        "style": style,
                        "styledegree": degree,
                    }
                    for treatment_id, style, degree in hard["treatments"]
                ],
            })

    return {
        "version": 1,
        "kind": "expressive-provider-duel",
        "production_promotion": False,
        "questions": {
            "controlled": "Native style improves same base voice?",
            "mai": "MAI-Voice-2 raises acting ceiling?",
        },
        "cases": cases,
    }


def render_experiment(output_dir, *, edge=None, azure=None):
    edge = edge or EdgeProvider()
    azure = azure or AzureSpeechLabProvider()
    output_dir = Path(output_dir)
    clips = output_dir / "clips"
    clips.mkdir(parents=True, exist_ok=True)

    spec = experiment_spec()
    rendered = []
    failures = []
    for case in spec["cases"]:
        for option in case["options"]:
            provider = edge if option["provider"] == "edge" else azure
            filename = f"{case['id']}--{option['id']}.mp3".replace(":", "-")
            path = clips / filename
            segment = {
                "text": case["text"],
                "voice": case["voice"],
                "language_locale": "fr-FR",
            }
            if option.get("style"):
                segment["style"] = option["style"]
            if option.get("styledegree") is not None:
                segment["styledegree"] = option["styledegree"]
            try:
                provider.synthesize(segment, path)
                rendered.append({
                    "case_id": case["id"],
                    "option_id": option["id"],
                    "file": f"clips/{filename}",
                })
            except Exception as exc:
                failures.append({
                    "case_id": case["id"],
                    "option_id": option["id"],
                    "error": str(exc),
                })

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
        (item["case_id"], item["option_id"]): item["file"]
        for item in manifest.get("rendered", [])
    }
    randomizer = random.Random(seed)
    trials = []
    for case in manifest["cases"]:
        options = []
        for option in case["options"]:
            file = rendered.get((case["id"], option["id"]))
            if file:
                options.append({**option, "file": file})
        if len(options) != len(case["options"]):
            continue
        randomizer.shuffle(options)
        trials.append({
            "id": case["id"],
            "kind": case["kind"],
            "intention": case["intention"],
            "text": case["text"],
            "options": [
                {"letter": letter, **option}
                for letter, option in zip("ABCD", options)
            ],
        })

    payload = json.dumps({"version": 1, "trials": trials}, ensure_ascii=False).replace("</", "<\\/")
    html = f"""<!doctype html><html lang='fr'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Duel expressif — Voice Casting Lab</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.45}}.card{{border:1px solid #888;border-radius:12px;padding:1rem;margin:1rem 0}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}audio{{width:100%}}button{{padding:.7rem 1rem;margin:.25rem}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style>
<h1>Duel expressif</h1><p>Choisis la variante qui joue le mieux l'intention. Si aucune ne fonctionne réellement, rejette le cas. Les traitements restent masqués.</p>
<p id='progress'></p><div id='app'></div><button id='export'>Exporter les résultats JSON</button>
<script>const data={payload};let i=0;const answers={{}};const app=document.getElementById('app');const progress=document.getElementById('progress');
function render(){{const t=data.trials[i];progress.textContent=t?`Cas ${{i+1}} / ${{data.trials.length}} · ${{t.intention}}`:'Test terminé';if(!t){{app.innerHTML='<p>Exportez les résultats.</p>';return;}}const players=t.options.map(o=>`<div><h3>${{o.letter}}</h3><audio controls preload='none' src='${{o.file}}'></audio></div>`).join('');const buttons=t.options.map(o=>`<button data-v='${{o.letter}}'>${{o.letter}} est meilleure</button>`).join('');app.innerHTML=`<div class='card'><h2>${{t.intention}}</h2><p><em>${{t.text}}</em></p><div class='grid'>${{players}}</div><p>${{buttons}}<button data-v='none'>Aucune acceptable</button><button data-v='invalid-pronunciation'>Prononciation invalide</button></p></div>`;app.querySelectorAll('button[data-v]').forEach(b=>b.onclick=()=>{{answers[t.id]=b.dataset.v;i++;render();}});}}
document.getElementById('export').onclick=()=>{{const result={{schema:'voice-casting-expressive-provider-duel-v1',exported_at:new Date().toISOString(),responses:answers,mapping:data.trials}};const blob=new Blob([JSON.stringify(result,null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='voice-casting-expressive-duel-results.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}};render();</script></html>"""
    (output_dir / "index.html").write_text(html, encoding="utf-8")
    return {"trial_count": len(trials)}
