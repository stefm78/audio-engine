"""Minimal direct-VoiceDesign killer for a deliberately far-but-natural French female pair."""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

from .voice_casting_distance import compare_anchors

SCHEMA = "qwen3-extreme-cast-panic-v1"
QWEN_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
MODEL_REVISION = "5ecdb67327fd37bb2e042aab12ff7391903235d3"
BLIND_SEED = 2026082517
NEUTRAL_MIN_SCORE = 80.0
PANIC_MIN_SCORE = 60.0

REFERENCE_TEXT = (
    "La lumière traverse les volets. Je suis ici depuis l'aube, "
    "et je peux enfin vous raconter ce qui s'est passé."
)
PANIC_TEXT = "Vite ! Ils arrivent ! Fermez la porte !"

CHARACTERS = {
    "claire": {
        "seed": 2026082531,
        "instruct": (
            "Femme française d'environ 66 ans. Contralto parlé très bas mais naturel, voix ample, "
            "sombre et boisée, forte résonance de poitrine, léger grain mûr et velouté, articulation "
            "posée, présence calme et chaleureuse. La voix reste clairement féminine, crédible et "
            "non caricaturale."
        ),
    },
    "lucie": {
        "seed": 2026082541,
        "instruct": (
            "Jeune femme française d'environ 21 ans. Soprano parlé clair et franchement haut mais "
            "naturel, timbre cristallin et léger, résonance tête et avant, presque aucun grain, "
            "articulation vive et nette, énergie lumineuse. La voix reste adulte, crédible et non "
            "caricaturale."
        ),
    },
}


def character_spec(role: str) -> dict:
    if role not in CHARACTERS:
        raise ValueError(f"unknown role: {role}")
    return {"role": role, **CHARACTERS[role]}


def reference_instruction(role: str) -> str:
    return character_spec(role)["instruct"] + " Parle calmement, de façon neutre et naturelle."


def panic_instruction(role: str) -> str:
    return (
        character_spec(role)["instruct"]
        + " Conserve cette identité vocale de façon immédiatement reconnaissable. "
        + "Interprétation : panique urgente et crédible, souffle court, débit accéléré, tension élevée, "
        + "tout en restant intelligible et naturelle."
    )


def experiment_spec() -> dict:
    return {
        "schema": SCHEMA,
        "architecture": "direct-voicedesign-extreme-natural-casting",
        "qwen_revision": QWEN_REVISION,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
        "characters": {role: character_spec(role) for role in ("claire", "lucie")},
        "reference_text": REFERENCE_TEXT,
        "panic_text": PANIC_TEXT,
        "automatic_gate": {
            "neutral_min_score": NEUTRAL_MIN_SCORE,
            "panic_min_score": PANIC_MIN_SCORE,
        },
        "human_gate": {
            "identity": "1/1 blind mapping correct",
            "acting": "A=yes and B=yes",
            "french": "both-good",
        },
        "claims": {
            "panic_qualified": False,
            "broader_emotion_qualified": False,
            "age_lineage": False,
            "production_promoted": False,
        },
    }


def _role_root(root: Path, role: str) -> Path:
    matches = []
    for path in Path(root).rglob("character-result.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("role") == role:
            matches.append(path.parent)
    if len(matches) != 1:
        raise ValueError(f"expected one render result for {role}, got {len(matches)}")
    return matches[0]


def assemble_bundle(input_root, output_dir, *, seed=BLIND_SEED):
    input_root, output_dir = Path(input_root), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    roots = {role: _role_root(input_root, role) for role in ("claire", "lucie")}

    refs, panic = {}, {}
    for role, root in roots.items():
        result = json.loads((root / "character-result.json").read_text(encoding="utf-8"))
        if result.get("status") != "success" or result.get("role") != role:
            raise ValueError(f"invalid render result for {role}")
        if set(result.get("rendered", {})) != {"reference", "panic"}:
            raise ValueError(f"incomplete render for {role}")
        ref_name = f"reference-{role}.wav"
        panic_name = f"{role}--panic.wav"
        shutil.copy2(root / result["rendered"]["reference"], output_dir / ref_name)
        shutil.copy2(root / result["rendered"]["panic"], clips_dir / panic_name)
        refs[role] = ref_name
        panic[role] = f"clips/{panic_name}"

    neutral_diag = compare_anchors(output_dir / refs["claire"], output_dir / refs["lucie"])
    panic_diag = compare_anchors(output_dir / panic["claire"], output_dir / panic["lucie"])
    eligible = neutral_diag["score"] >= NEUTRAL_MIN_SCORE and panic_diag["score"] >= PANIC_MIN_SCORE

    manifest = {
        **experiment_spec(),
        "status": "human-gate-ready" if eligible else "auto-rejected",
        "distance_diagnostics_not_identity_proof": {
            "neutral": neutral_diag,
            "panic": panic_diag,
        },
        "trial_count": 1 if eligible else 0,
    }

    if eligible:
        options = [
            {"role": "claire", "file": panic["claire"]},
            {"role": "lucie", "file": panic["lucie"]},
        ]
        random.Random(seed).shuffle(options)
        trial = {
            "id": "panic",
            "label": "Panique urgente",
            "text": PANIC_TEXT,
            "references": [
                {"role": "claire", "label": "Référence 1", "file": refs["claire"]},
                {"role": "lucie", "label": "Référence 2", "file": refs["lucie"]},
            ],
            "options": [
                {"letter": letter, **item} for letter, item in zip("AB", options)
            ],
            "correct_reference_for_A": "Référence 1" if options[0]["role"] == "claire" else "Référence 2",
        }
        manifest["trials"] = [trial]
        _write_player(output_dir, trial)

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def _write_player(output_dir: Path, trial: dict) -> None:
    public = {
        "id": trial["id"],
        "label": trial["label"],
        "text": trial["text"],
        "references": trial["references"],
        "options": [{"letter": o["letter"], "file": o["file"]} for o in trial["options"]],
    }
    public_json = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    mapping_json = json.dumps({"trials": [trial]}, ensure_ascii=False).replace("</", "<\\/")
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Casting extrême naturel — panique</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}.card{{border:1px solid #999;border-radius:12px;padding:1rem}}audio{{width:100%}}label{{display:block;margin:.55rem 0}}button{{padding:.7rem 1rem;margin:.4rem}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><h1>Casting extrême naturel — panique</h1><p>Un seul écran. Écoutez les références neutres, puis A et B.</p><main id="app"></main><script>const t={public_json};const mapping={mapping_json};function audio(src){{return `<audio controls preload="none" src="${{src}}"></audio>`}}function radios(name,values){{return values.map(v=>`<label><input type="radio" name="${{name}}" value="${{v[0]}}"> ${{v[1]}}</label>`).join('')}}document.getElementById('app').innerHTML=`<h2>${{t.label}}</h2><p>${{t.text}}</p><div class="grid"><div class="card"><h3>Référence 1</h3>${{audio(t.references[0].file)}}<h3>Référence 2</h3>${{audio(t.references[1].file)}}</div><div class="card"><h3>A</h3>${{audio(t.options[0].file)}}<h3>B</h3>${{audio(t.options[1].file)}}</div></div><h3>À quelle référence correspond A ?</h3>${{radios('identity',[['Référence 1','Référence 1'],['Référence 2','Référence 2'],['uncertain','Impossible à distinguer']])}}<h3>Le jeu correspond-il à la panique ?</h3><p>A</p>${{radios('actingA',[['yes','Oui'],['no','Non']])}}<p>B</p>${{radios('actingB',[['yes','Oui'],['no','Non']])}}<h3>Français</h3>${{radios('french',[['both-good','Les deux sont bons'],['a-defect','Défaut éliminatoire sur A'],['b-defect','Défaut éliminatoire sur B'],['both-defect','Défaut éliminatoire sur les deux']])}}<p><button onclick="finish()">Terminer</button></p>`;function finish(){{const get=n=>document.querySelector(`input[name="${{n}}"]:checked`);const i=get('identity'),a=get('actingA'),b=get('actingB'),f=get('french');if(!i||!a||!b||!f){{alert('Répondez aux quatre questions.');return}}const data={{schema:'qwen3-extreme-cast-panic-results-v1',exported_at:new Date().toISOString(),responses:{{panic:{{identity:i.value,actingA:a.value,actingB:b.value,french:f.value}}}},mapping}};const blob=new Blob([JSON.stringify(data,null,2)],{{type:'application/json'}});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='qwen3-extreme-cast-panic-results.json';link.click();URL.revokeObjectURL(link.href)}};</script></body></html>'''
    if "<select" in html.lower():
        raise ValueError("Voice Lab questionnaires must be radio-only")
    (output_dir / "index.html").write_text(html, encoding="utf-8")
