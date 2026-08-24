"""Stage-2 Chatterbox Multilingual V3 benchmark for the Voice Casting Lab.

This follows a 2/2 human-listening win for the fixed Chatterbox dramatic bundle
(exaggeration=0.8, cfg_weight=0.3) over Edge on Vivienne.  Stage 2 asks whether
that result generalizes across voice gender/timbre and harder intentions, while
adding an explicit identity-continuity ABX gate.

The experiment remains lab-only and cannot promote a production provider.
"""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

from .providers.chatterbox_lab import ChatterboxLabProvider
from .providers.edge import EdgeProvider


REFERENCE_TEXT = (
    "À l'aube, personne dans la ville ne savait encore ce qui allait se produire. "
    "Approchez. Ce que je vais vous dire ne doit sortir d'ici sous aucun prétexte."
)

VOICES = (
    {
        "id": "vivienne",
        "voice": "fr-FR-VivienneMultilingualNeural",
        "label": "Voix 1",
    },
    {
        "id": "william",
        "voice": "en-AU-WilliamMultilingualNeural",
        "label": "Voix 2",
    },
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
    {
        "id": "polite-threat",
        "intention": "menace polie",
        "text": "Je vous conseille très sincèrement de reconsidérer votre réponse.",
    },
    {
        "id": "wonder",
        "intention": "émerveillement",
        "text": "Regardez... On distingue toute la vallée, jusqu'aux montagnes derrière la brume.",
    },
)

CHATTERBOX_BUNDLE = {
    "exaggeration": 0.8,
    "cfg_weight": 0.3,
    "temperature": 0.8,
    "seed": 20260824,
}

IDENTITY_INTENTIONS = ("panic", "mystery")


def experiment_spec():
    return {
        "version": 1,
        "kind": "chatterbox-v3-stage2",
        "production_promotion": False,
        "model": {
            "family": "Chatterbox Multilingual",
            "t3_model": "v3",
            "language_id": "fr",
            "optional_dependency": True,
        },
        "reference": {
            "text": REFERENCE_TEXT,
            "source": "synthetic-edge-reference",
        },
        "voices": [dict(item) for item in VOICES],
        "cases": [dict(item) for item in CASES],
        "chatterbox_bundle": dict(CHATTERBOX_BUNDLE),
        "identity_intentions": list(IDENTITY_INTENTIONS),
        "decision": {
            "acting_pass": (
                "Chatterbox wins at least 6 of 8 acting comparisons, with at least "
                "2 wins for each reference voice, and no repeated French-pronunciation defect."
            ),
            "identity_pass": "4/4 cross-provider ABX identity decisions correct.",
            "identity_borderline": "3/4 correct triggers a targeted identity retest, not promotion.",
            "next_if_pass": "qualify Chatterbox as an experimental acting provider; then test age lineage.",
            "next_if_fail": "skip tuning loops and move to semantic-instruction challenger CosyVoice 3.",
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
    chatterbox = chatterbox or ChatterboxLabProvider(device="cpu", t3_model="v3")
    spec = experiment_spec()
    references = {}
    rendered = []
    failures = []

    for voice in spec["voices"]:
        reference_mp3 = output_dir / f"reference-{voice['id']}-edge.mp3"
        reference_wav = output_dir / f"reference-{voice['id']}-edge-16k.wav"
        try:
            edge.synthesize(
                {
                    "text": REFERENCE_TEXT,
                    "voice": voice["voice"],
                    "rate": "+0%",
                    "pitch": "+0Hz",
                    "volume": "+0%",
                    "language_locale": "fr-FR",
                },
                reference_mp3,
            )
            _convert_reference(reference_mp3, reference_wav)
            reference_mp3.unlink(missing_ok=True)
            references[voice["id"]] = f"{reference_wav.name}"
        except Exception as exc:
            failures.append({"voice_id": voice["id"], "kind": "reference", "error": str(exc)})

    for voice in spec["voices"]:
        reference_file = references.get(voice["id"])
        if not reference_file:
            continue
        reference_path = output_dir / reference_file
        for case in spec["cases"]:
            # Edge baseline
            edge_wav = clips_dir / f"{voice['id']}--{case['id']}--edge.wav"
            edge_mp3 = clips_dir / f"{voice['id']}--{case['id']}--edge.mp3"
            try:
                edge.synthesize(
                    {
                        "text": case["text"],
                        "voice": voice["voice"],
                        "rate": "+0%",
                        "pitch": "+0Hz",
                        "volume": "+0%",
                        "language_locale": "fr-FR",
                    },
                    edge_mp3,
                )
                _convert_reference(edge_mp3, edge_wav)
                edge_mp3.unlink(missing_ok=True)
                rendered.append(
                    {
                        "voice_id": voice["id"],
                        "case_id": case["id"],
                        "provider": "edge",
                        "file": f"clips/{edge_wav.name}",
                    }
                )
            except Exception as exc:
                failures.append(
                    {
                        "voice_id": voice["id"],
                        "case_id": case["id"],
                        "provider": "edge",
                        "error": str(exc),
                    }
                )

            # Fixed Chatterbox bundle that won 2/2 in the killer test.
            chatterbox_wav = clips_dir / f"{voice['id']}--{case['id']}--chatterbox.wav"
            try:
                chatterbox.synthesize(
                    {
                        "text": case["text"],
                        "audio_prompt_path": str(reference_path),
                        "language_id": "fr",
                        **CHATTERBOX_BUNDLE,
                    },
                    chatterbox_wav,
                )
                rendered.append(
                    {
                        "voice_id": voice["id"],
                        "case_id": case["id"],
                        "provider": "chatterbox",
                        "file": f"clips/{chatterbox_wav.name}",
                    }
                )
            except Exception as exc:
                failures.append(
                    {
                        "voice_id": voice["id"],
                        "case_id": case["id"],
                        "provider": "chatterbox",
                        "error": str(exc),
                    }
                )

    result = {
        **spec,
        "status": "success" if not failures else ("partial" if rendered else "failed"),
        "rendered_count": len(rendered),
        "failure_count": len(failures),
        "references": references,
        "rendered": rendered,
        "failures": failures,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_blind_player(result, output_dir)
    return result


def _acting_trials(manifest, randomizer):
    rendered = {
        (item["voice_id"], item["case_id"], item["provider"]): item["file"]
        for item in manifest.get("rendered", [])
    }
    trials = []
    for voice in manifest["voices"]:
        for case in manifest["cases"]:
            options = []
            for provider in ("edge", "chatterbox"):
                file = rendered.get((voice["id"], case["id"], provider))
                if file:
                    options.append({"provider": provider, "file": file})
            if len(options) != 2:
                continue
            randomizer.shuffle(options)
            trials.append(
                {
                    "id": f"acting-{voice['id']}--{case['id']}",
                    "kind": "acting",
                    "voice_id": voice["id"],
                    "voice_label": voice["label"],
                    "case_id": case["id"],
                    "intention": case["intention"],
                    "text": case["text"],
                    "options": [
                        {"letter": letter, **option}
                        for letter, option in zip("AB", options)
                    ],
                }
            )
    return trials


def _identity_trials(manifest, randomizer):
    rendered = {
        (item["voice_id"], item["case_id"], item["provider"]): item["file"]
        for item in manifest.get("rendered", [])
    }
    voices = {item["id"]: item for item in manifest["voices"]}
    voice_ids = list(voices)
    trials = []
    for reference_voice_id in voice_ids:
        distractor_voice_id = next(item for item in voice_ids if item != reference_voice_id)
        reference_file = manifest.get("references", {}).get(reference_voice_id)
        if not reference_file:
            continue
        for case_id in manifest["identity_intentions"]:
            same_file = rendered.get((reference_voice_id, case_id, "chatterbox"))
            distractor_file = rendered.get((distractor_voice_id, case_id, "chatterbox"))
            if not same_file or not distractor_file:
                continue
            options = [
                {"voice_id": reference_voice_id, "same_identity": True, "file": same_file},
                {"voice_id": distractor_voice_id, "same_identity": False, "file": distractor_file},
            ]
            randomizer.shuffle(options)
            trials.append(
                {
                    "id": f"identity-{reference_voice_id}--{case_id}",
                    "kind": "identity-abx",
                    "reference_voice_id": reference_voice_id,
                    "reference_voice_label": voices[reference_voice_id]["label"],
                    "case_id": case_id,
                    "reference_file": reference_file,
                    "options": [
                        {"letter": letter, **option}
                        for letter, option in zip("AB", options)
                    ],
                    "correct": next(
                        letter
                        for letter, option in zip("AB", options)
                        if option["same_identity"]
                    ),
                }
            )
    return trials


def write_blind_player(manifest, output_dir, *, seed=20260824):
    output_dir = Path(output_dir)
    randomizer = random.Random(seed)
    acting = _acting_trials(manifest, randomizer)
    identity = _identity_trials(manifest, randomizer)
    payload = json.dumps(
        {"version": 1, "acting": acting, "identity": identity}, ensure_ascii=False
    ).replace("</", "<\\/")
    html = f"""<!doctype html><html lang='fr'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Chatterbox V3 — stage 2</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.45}}.card{{border:1px solid #888;border-radius:12px;padding:1rem;margin:1rem 0}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}audio{{width:100%}}button{{padding:.7rem 1rem;margin:.25rem}}.small{{opacity:.75}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style>
<h1>Chatterbox V3 — validation stage 2</h1><p>12 décisions : 8 sur le jeu, puis 4 sur la continuité d'identité. Les moteurs et identités candidates restent masqués.</p>
<p id='progress'></p><div id='app'></div><button id='export'>Exporter les résultats JSON</button>
<script>const data={payload};const KEY='voice-casting-chatterbox-stage2-v1';let state={{section:'acting',index:0,responses:{{}}}};try{{state=JSON.parse(localStorage.getItem(KEY))||state}}catch(e){{}}const app=document.getElementById('app');const progress=document.getElementById('progress');function save(){{localStorage.setItem(KEY,JSON.stringify(state));}}function currentList(){{return state.section==='acting'?data.acting:data.identity;}}function answer(id,value){{state.responses[id]=value;state.index++;const list=currentList();if(state.index>=list.length&&state.section==='acting'){{state.section='identity';state.index=0;}}save();render();}}function render(){{const list=currentList();const t=list[state.index];const done=Object.keys(state.responses).length;const total=data.acting.length+data.identity.length;progress.textContent=`Décision ${{Math.min(done+1,total)}} / ${{total}} · ${{state.section==='acting'?'jeu':'identité'}}`;if(!t){{app.innerHTML='<p>Évaluation terminée. Exportez les résultats.</p>';progress.textContent=`Terminé · ${{done}} / ${{total}}`;return;}}if(t.kind==='acting'){{const players=t.options.map(o=>`<div><h3>${{o.letter}}</h3><audio controls preload='none' src='${{o.file}}'></audio></div>`).join('');app.innerHTML=`<div class='card'><span class='small'>${{t.voice_label}}</span><h2>Quelle version joue le mieux : ${{t.intention}} ?</h2><p><em>${{t.text}}</em></p><div class='grid'>${{players}}</div><p><button data-v='A'>A est meilleure</button><button data-v='B'>B est meilleure</button><button data-v='none'>Aucune acceptable</button><button data-v='invalid-pronunciation'>Prononciation invalide</button></p></div>`;}}else{{const players=t.options.map(o=>`<div><h3>${{o.letter}}</h3><audio controls preload='none' src='${{o.file}}'></audio></div>`).join('');app.innerHTML=`<div class='card'><span class='small'>Test d'identité · ${{t.reference_voice_label}}</span><h2>Quelle proposition correspond au même personnage que la référence ?</h2><p>Référence</p><audio controls preload='none' src='${{t.reference_file}}'></audio><div class='grid'>${{players}}</div><p><button data-v='A'>A</button><button data-v='B'>B</button><button data-v='uncertain'>Impossible à déterminer</button><button data-v='invalid-pronunciation'>Prononciation invalide</button></p></div>`;}}app.querySelectorAll('button[data-v]').forEach(b=>b.onclick=()=>answer(t.id,b.dataset.v));window.scrollTo({{top:0,behavior:'smooth'}});}}document.getElementById('export').onclick=()=>{{const result={{schema:'voice-casting-chatterbox-stage2-v1',exported_at:new Date().toISOString(),responses:state.responses,mapping:{{acting:data.acting,identity:data.identity}}}};const blob=new Blob([JSON.stringify(result,null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='voice-casting-chatterbox-stage2-results.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}};render();</script></html>"""
    (output_dir / "index.html").write_text(html, encoding="utf-8")
    return {"acting_trial_count": len(acting), "identity_trial_count": len(identity)}
