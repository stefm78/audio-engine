"""Efficient contrasted-casting experiment for Voice Casting Lab.

Four neutral VoiceDesign anchors are screened acoustically against the known-confusable
Claire/Lucie baseline. Only the most separated cross-role pair may proceed to a tiny
Qwen3 Base x-vector identity check. This is an explicit recast experiment; it never
silently replaces the qualified Claire/Lucie anchors.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path

from .providers.qwen3_xvector_lab import Qwen3XVectorLabProvider
from .voice_casting_distance import contrast_gate

QWEN_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
VOICE_DESIGN_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
VOICE_DESIGN_MODEL_REVISION = "5ecdb67327fd37bb2e042aab12ff7391903235d3"
BASE_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
BASE_MODEL_REVISION = "74a6279626edc2d5a787d5b6467668eba0b86ef6"
BASELINE_RUN_ID = 32772435007
BASELINE_ARTIFACT = "voice-casting-qwen3-xvector-identity-confirm"
BLIND_SEED = 2026082509

BASELINE = {
    "claire": {
        "file": "reference-claire-qwen3.wav",
        "sha256": "1012fdc137a848e71a9403140267e62140ad87b14ee9a3236e106b57775afa55",
    },
    "lucie": {
        "file": "reference-lucie-qwen3.wav",
        "sha256": "f42c27ce633e0d009a95079cdfddc605772bbf48e9806fba6fba3749e5aa1ee2",
    },
}

ANCHOR_TEXT = (
    "La lumière traverse les volets. Je suis ici depuis l'aube, "
    "et je peux enfin vous raconter ce qui s'est passé."
)

CANDIDATES = {
    "claire-a": {
        "role": "claire",
        "seed": 2026082511,
        "instruct": (
            "Femme française d'environ 52 ans. Contralto bas, chaud et mat, forte résonance "
            "de poitrine, léger grain velouté, consonnes posées, débit calme et mesuré, "
            "autorité tranquille. Voix naturelle, sans caricature."
        ),
    },
    "claire-b": {
        "role": "claire",
        "seed": 2026082512,
        "instruct": (
            "Femme française d'environ 46 ans. Voix grave de mezzo-contralto, sombre et boisée, "
            "résonance ample, attaque douce, articulation lente et précise, légère rugosité "
            "naturelle, présence stable."
        ),
    },
    "lucie-a": {
        "role": "lucie",
        "seed": 2026082521,
        "instruct": (
            "Jeune femme française d'environ 24 ans. Voix claire et haute, légère mais naturelle, "
            "résonance brillante en avant, très peu de grain, articulation vive et nette, débit "
            "plus rapide, énergie lumineuse."
        ),
    },
    "lucie-b": {
        "role": "lucie",
        "seed": 2026082522,
        "instruct": (
            "Femme française d'environ 29 ans. Voix mezzo claire, légère et aérienne, timbre "
            "lumineux, résonance tête et avant, consonnes rapides, intonation mobile, sourire "
            "discret, aucune gravité sombre."
        ),
    },
}

IDENTITY_LINES = (
    {
        "id": "neutral-one",
        "text": "Nous partirons après le lever du jour. D'ici là, restez près de la fenêtre.",
    },
    {
        "id": "neutral-two",
        "text": "J'ai retrouvé la lettre dans le tiroir. Personne ne l'avait ouverte depuis des années.",
    },
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def experiment_spec():
    return {
        "schema": "qwen3-contrast-casting-v1",
        "recast_experiment": True,
        "production_promotion": False,
        "age_lineage": False,
        "qwen_revision": QWEN_REVISION,
        "voice_design_model": {
            "id": VOICE_DESIGN_MODEL_ID,
            "revision": VOICE_DESIGN_MODEL_REVISION,
        },
        "base_model": {"id": BASE_MODEL_ID, "revision": BASE_MODEL_REVISION},
        "baseline_run_id": BASELINE_RUN_ID,
        "baseline_artifact": BASELINE_ARTIFACT,
        "anchor_text": ANCHOR_TEXT,
        "candidates": {key: dict(value) for key, value in CANDIDATES.items()},
        "identity_lines": [dict(line) for line in IDENTITY_LINES],
        "gates": {
            "acoustic_prefilter": "candidate >= 1.35x baseline and >= baseline + 8 points",
            "human_identity": "2/2 blind mappings correct",
            "human_french": "both-good on both screens",
            "no_emotion_before_identity_pass": True,
        },
    }


def select_pair(candidate_root, baseline_root, output_dir):
    candidate_root = Path(candidate_root)
    baseline_root = Path(baseline_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_paths = {}
    for role, item in BASELINE.items():
        path = baseline_root / item["file"]
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256(path)
        if actual != item["sha256"]:
            raise ValueError(f"baseline hash mismatch for {role}: {actual}")
        baseline_paths[role] = path

    candidate_paths = {}
    for candidate_id in CANDIDATES:
        matches = list(candidate_root.rglob(f"{candidate_id}.wav"))
        if len(matches) != 1:
            raise ValueError(f"expected one anchor for {candidate_id}, got {len(matches)}")
        candidate_paths[candidate_id] = matches[0]

    comparisons = []
    for claire_id, claire_spec in CANDIDATES.items():
        if claire_spec["role"] != "claire":
            continue
        for lucie_id, lucie_spec in CANDIDATES.items():
            if lucie_spec["role"] != "lucie":
                continue
            gate = contrast_gate(
                candidate_paths[claire_id],
                candidate_paths[lucie_id],
                baseline_paths["claire"],
                baseline_paths["lucie"],
            )
            comparisons.append(
                {
                    "claire_id": claire_id,
                    "lucie_id": lucie_id,
                    "eligible": gate["eligible"],
                    "candidate_score": gate["candidate_score"],
                    "baseline_score": gate["baseline_score"],
                    "required_score": gate["required_score"],
                    "components": gate["candidate"]["components"],
                }
            )

    winner = max(comparisons, key=lambda item: item["candidate_score"])
    result = {
        **experiment_spec(),
        "status": "selected" if winner["eligible"] else "rejected",
        "comparisons": comparisons,
        "selected": winner,
        "claim": "acoustic-prefilter-only",
    }
    if winner["eligible"]:
        selected_claire = candidate_paths[winner["claire_id"]]
        selected_lucie = candidate_paths[winner["lucie_id"]]
        shutil.copy2(selected_claire, output_dir / "reference-claire.wav")
        shutil.copy2(selected_lucie, output_dir / "reference-lucie.wav")
        result["selected_anchor_sha256"] = {
            "claire": _sha256(output_dir / "reference-claire.wav"),
            "lucie": _sha256(output_dir / "reference-lucie.wav"),
        }
    (output_dir / "selection.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def render_identity_check(role, selection_dir, output_dir, *, provider=None, model_dir=None):
    if role not in {"claire", "lucie"}:
        raise ValueError(f"unknown role: {role}")
    selection_dir = Path(selection_dir)
    selection = json.loads((selection_dir / "selection.json").read_text(encoding="utf-8"))
    if selection.get("status") != "selected":
        raise ValueError("contrast casting did not pass the acoustic prefilter")
    anchor = selection_dir / f"reference-{role}.wav"
    expected = selection["selected_anchor_sha256"][role]
    if _sha256(anchor) != expected:
        raise ValueError(f"selected {role} anchor hash mismatch")
    if provider is None:
        if model_dir is None:
            raise ValueError("model_dir is required when provider is not injected")
        provider = Qwen3XVectorLabProvider(model_dir=model_dir, device="cpu")
    if getattr(provider, "identity_mode", None) != "x_vector_only":
        raise ValueError("identity check requires x_vector_only provider")

    prompt = provider.build_identity_prompt(anchor)
    output_dir = Path(output_dir)
    clips = output_dir / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    rendered = []
    for index, line in enumerate(IDENTITY_LINES, 1):
        out = clips / f"{line['id']}.wav"
        seed_payload = f"contrast-casting\0{role}\0{line['id']}".encode("utf-8")
        seed = int.from_bytes(hashlib.sha256(seed_payload).digest()[:4], "big")
        provider.synthesize(
            {"text": line["text"], "language": "French", "seed": seed},
            out,
            voice_clone_prompt=prompt,
        )
        rendered.append({"id": line["id"], "file": f"clips/{line['id']}.wav", "seed": seed})
    shutil.copy2(anchor, output_dir / "reference.wav")
    result = {
        "schema": "qwen3-contrast-casting-character-v1",
        "status": "success",
        "role": role,
        "anchor_sha256": expected,
        "rendered_count": len(rendered),
        "rendered": rendered,
    }
    (output_dir / "character-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def _role_root(root: Path, role: str):
    matches = []
    for path in Path(root).rglob("character-result.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("role") == role:
            matches.append(path.parent)
    if len(matches) != 1:
        raise ValueError(f"expected one identity result for {role}, got {len(matches)}")
    return matches[0]


def assemble_bundle(input_root, output_dir, *, seed=BLIND_SEED):
    input_root = Path(input_root)
    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    roots = {role: _role_root(input_root, role) for role in ("claire", "lucie")}

    references = {}
    rendered = {}
    hashes = {}
    for role, root in roots.items():
        result = json.loads((root / "character-result.json").read_text(encoding="utf-8"))
        if result.get("status") != "success" or result.get("rendered_count") != len(IDENTITY_LINES):
            raise ValueError(f"incomplete identity render for {role}")
        ref_name = f"reference-{role}.wav"
        shutil.copy2(root / "reference.wav", output_dir / ref_name)
        references[role] = ref_name
        hashes[role] = result["anchor_sha256"]
        for item in result["rendered"]:
            name = f"{role}--{item['id']}.wav"
            shutil.copy2(root / item["file"], clips_dir / name)
            rendered[(role, item["id"])] = f"clips/{name}"

    rnd = random.Random(seed)
    trials = []
    for line in IDENTITY_LINES:
        options = [
            {"role": role, "file": rendered[(role, line["id"])]}
            for role in ("claire", "lucie")
        ]
        rnd.shuffle(options)
        trials.append(
            {
                "id": line["id"],
                "text": line["text"],
                "references": [
                    {"role": "claire", "label": "Référence 1", "file": references["claire"]},
                    {"role": "lucie", "label": "Référence 2", "file": references["lucie"]},
                ],
                "options": [
                    {"letter": letter, **option} for letter, option in zip("AB", options)
                ],
                "correct_reference_for_A": "Référence 1" if options[0]["role"] == "claire" else "Référence 2",
            }
        )

    manifest = {
        "schema": "qwen3-contrast-casting-identity-v1",
        "status": "success",
        "trial_count": len(trials),
        "anchor_sha256": hashes,
        "decision": {
            "identity_pass": "2/2 pair mappings correct",
            "french_pass": "both-good on both screens",
            "emotion_test": False,
            "production_promotion": False,
        },
        "trials": trials,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_player(output_dir, trials)
    return manifest


def _write_player(output_dir: Path, trials):
    public = [
        {
            "id": trial["id"],
            "text": trial["text"],
            "references": trial["references"],
            "options": [{"letter": o["letter"], "file": o["file"]} for o in trial["options"]],
        }
        for trial in trials
    ]
    public_json = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    mapping_json = json.dumps({"trials": trials}, ensure_ascii=False).replace("</", "<\\/")
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contraste personnages</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}.card{{border:1px solid #999;border-radius:12px;padding:1rem}}audio{{width:100%}}label{{display:block;margin:.6rem 0}}button{{padding:.7rem 1rem;margin:.4rem}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><h1>Test de contraste des personnages</h1><p>2 écrans seulement. Identifiez la voix de A puis vérifiez le français.</p><p id="progress"></p><div id="app"></div><button id="back">Précédent</button><button id="next">Suivant</button><button id="export">Exporter le JSON</button><script>const trials={public_json};const mapping={mapping_json};const KEY='qwen3-contrast-casting-identity-v1';let state={{index:0,responses:{{}}}};try{{state=JSON.parse(localStorage.getItem(KEY))||state}}catch(e){{}}function save(){{try{{localStorage.setItem(KEY,JSON.stringify(state))}}catch(e){{}}}}function chosen(n){{const x=document.querySelector('input[name="'+n+'"]:checked');return x?x.value:null}}function render(){{const t=trials[state.index];document.getElementById('progress').textContent='Écran '+(state.index+1)+'/'+trials.length;const refs=t.references.map(r=>`<div><h3>${{r.label}}</h3><audio controls src="${{r.file}}"></audio></div>`).join('');const opts=t.options.map(o=>`<div><h3>Candidat ${{o.letter}}</h3><audio controls src="${{o.file}}"></audio></div>`).join('');document.getElementById('app').innerHTML=`<div class="card"><p><em>${{t.text}}</em></p><h2>Références</h2><div class="grid">${{refs}}</div><h2>Candidats</h2><div class="grid">${{opts}}</div><fieldset><legend>À quelle référence correspond A ?</legend><label><input type=radio name=identity value="Référence 1"> Référence 1</label><label><input type=radio name=identity value="Référence 2"> Référence 2</label><label><input type=radio name=identity value=uncertain> Impossible à distinguer</label></fieldset><fieldset><legend>Français</legend><label><input type=radio name=french value=both-good> Les deux corrects/naturels</label><label><input type=radio name=french value=bad-A> Défaut éliminatoire A</label><label><input type=radio name=french value=bad-B> Défaut éliminatoire B</label><label><input type=radio name=french value=bad-both> Défaut éliminatoire sur les deux</label></fieldset></div>`;const old=state.responses[t.id];if(old){{for(const [n,v] of Object.entries({{identity:old.identity,french:old.french}})){{const e=document.querySelector(`input[name="${{n}}"][value="${{v}}"]`);if(e)e.checked=true}}}}}}function commit(){{const t=trials[state.index],r={{identity:chosen('identity'),french:chosen('french')}};if(Object.values(r).some(v=>!v))return false;state.responses[t.id]=r;save();return true}}document.getElementById('next').onclick=()=>{{if(!commit())return alert('Répondez aux deux questions.');if(state.index<trials.length-1)state.index++;render()}};document.getElementById('back').onclick=()=>{{commit();if(state.index>0)state.index--;render()}};document.getElementById('export').onclick=()=>{{if(!commit())return alert('Répondez aux deux questions.');if(Object.keys(state.responses).length!==trials.length)return alert('Complétez les deux écrans.');const out={{schema:KEY,exported_at:new Date().toISOString(),responses:state.responses,mapping:mapping}};const blob=new Blob([JSON.stringify(out,null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='qwen3-contrast-casting-results.json';a.click();URL.revokeObjectURL(a.href)}};render();</script></body></html>'''
    (output_dir / "index.html").write_text(html, encoding="utf-8")
