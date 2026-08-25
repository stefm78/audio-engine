"""Direct VoiceDesign emotion killer for the contrasted French character pair.

This experiment deliberately avoids conversion and x-vector composition. The only
hypothesis is that a naturally well-separated casting plus a fixed character seed
can preserve recognisable identity while VoiceDesign supplies the acting.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path

from .voice_casting_distance import compare_anchors
from .voice_lab_qwen3_contrast_casting import CANDIDATES

SCHEMA = "qwen3-contrast-emotion-v1"
QWEN_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
MODEL_REVISION = "5ecdb67327fd37bb2e042aab12ff7391903235d3"
SOURCE_RUN_ID = 32818950167
SOURCE_ARTIFACT = "qwen3-contrast-selected-pair"
SELECTED = {"claire": "claire-a", "lucie": "lucie-b"}
EXPECTED_ANCHOR_SHA256 = {
    "claire": "3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe",
    "lucie": "9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822",
}
BLIND_SEED = 2026082510

CASES = (
    {
        "id": "panic",
        "label": "Panique urgente",
        "text": "Vite ! Ils arrivent ! Fermez la porte !",
        "acting": (
            "Panique urgente et crédible : souffle court, débit accéléré, tension élevée. "
            "Reste intelligible et naturelle, sans caricature et sans déformer le timbre."
        ),
    },
    {
        "id": "wonder",
        "label": "Émerveillement",
        "text": "Regardez... La brume se lève. On voit toute la vallée, jusqu'aux montagnes.",
        "acting": (
            "Émerveillement sincère : ouverture, chaleur, légère surprise et respiration plus ample. "
            "Aucune emphase théâtrale."
        ),
    },
    {
        "id": "sadness-contained",
        "label": "Tristesse contenue",
        "text": "Il est parti avant l'aube. Je savais que ce moment viendrait, mais pas si tôt.",
        "acting": (
            "Tristesse réelle mais contenue : énergie basse, légère fragilité du souffle et retenue. "
            "Aucun sanglot, aucun mélodrame."
        ),
    },
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def character_spec(role: str) -> dict:
    if role not in SELECTED:
        raise ValueError(f"unknown role: {role}")
    candidate_id = SELECTED[role]
    spec = CANDIDATES[candidate_id]
    if spec["role"] != role:
        raise ValueError("selected candidate role mismatch")
    return {"role": role, "candidate_id": candidate_id, **spec}


def expressive_instruction(role: str, case_id: str) -> str:
    spec = character_spec(role)
    case = next((item for item in CASES if item["id"] == case_id), None)
    if case is None:
        raise ValueError(f"unknown case: {case_id}")
    return (
        spec["instruct"]
        + " Conserve cette identité vocale de façon reconnaissable. Interprétation : "
        + case["acting"]
    )


def validate_selection(selection_dir) -> dict:
    root = Path(selection_dir)
    data = json.loads((root / "selection.json").read_text(encoding="utf-8"))
    if data.get("status") != "selected":
        raise ValueError("source contrast casting was not selected")
    selected = data.get("selected") or {}
    if selected.get("claire_id") != SELECTED["claire"] or selected.get("lucie_id") != SELECTED["lucie"]:
        raise ValueError("source selected pair differs from qualified contrasted casting")
    hashes = data.get("selected_anchor_sha256") or {}
    for role in ("claire", "lucie"):
        path = root / f"reference-{role}.wav"
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256(path)
        expected = EXPECTED_ANCHOR_SHA256[role]
        if actual != expected or hashes.get(role) != expected:
            raise ValueError(f"selected {role} anchor hash mismatch")
    return data


def experiment_spec() -> dict:
    return {
        "schema": SCHEMA,
        "architecture": "direct-voicedesign-contrasted-casting",
        "qwen_revision": QWEN_REVISION,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
        "source_run_id": SOURCE_RUN_ID,
        "source_artifact": SOURCE_ARTIFACT,
        "selected": dict(SELECTED),
        "expected_anchor_sha256": dict(EXPECTED_ANCHOR_SHA256),
        "characters": {role: character_spec(role) for role in ("claire", "lucie")},
        "cases": [dict(case) for case in CASES],
        "gates": {
            "identity": "3/3 blind A-to-reference mappings correct",
            "french": "both-good on all 3 screens",
            "acting": ">=5/6 total and >=2/3 per character",
        },
        "claims": {
            "neutral_identity_already_human_qualified": True,
            "emotion_qualified": False,
            "long_form_qualified": False,
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


def assemble_bundle(input_root, selection_dir, output_dir, *, seed=BLIND_SEED):
    selection = validate_selection(selection_dir)
    input_root, output_dir = Path(input_root), Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    roots = {role: _role_root(input_root, role) for role in ("claire", "lucie")}

    references, rendered = {}, {}
    for role in ("claire", "lucie"):
        reference_name = f"reference-{role}.wav"
        shutil.copy2(Path(selection_dir) / reference_name, output_dir / reference_name)
        references[role] = reference_name
        result = json.loads((roots[role] / "character-result.json").read_text(encoding="utf-8"))
        if result.get("status") != "success" or result.get("candidate_id") != SELECTED[role]:
            raise ValueError(f"invalid expressive result for {role}")
        by_id = {item["id"]: item for item in result.get("rendered", [])}
        if set(by_id) != {case["id"] for case in CASES}:
            raise ValueError(f"incomplete expressive cases for {role}")
        for case in CASES:
            src = roots[role] / by_id[case["id"]]["file"]
            dst_name = f"{role}--{case['id']}.wav"
            shutil.copy2(src, clips_dir / dst_name)
            rendered[(role, case["id"])] = f"clips/{dst_name}"

    rnd = random.Random(seed)
    trials = []
    distance_diagnostics = {}
    for case in CASES:
        options = [
            {"role": role, "file": rendered[(role, case["id"])]}
            for role in ("claire", "lucie")
        ]
        rnd.shuffle(options)
        distance_diagnostics[case["id"]] = compare_anchors(
            output_dir / rendered[("claire", case["id"])],
            output_dir / rendered[("lucie", case["id"])],
        )
        trials.append(
            {
                "id": case["id"],
                "label": case["label"],
                "text": case["text"],
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
        **experiment_spec(),
        "status": "success",
        "trial_count": len(trials),
        "source_selection_score": selection["selected"]["candidate_score"],
        "distance_diagnostics_not_a_gate": distance_diagnostics,
        "trials": trials,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_player(output_dir, trials)
    return manifest


def _write_player(output_dir: Path, trials) -> None:
    public = [
        {
            "id": t["id"], "label": t["label"], "text": t["text"],
            "references": t["references"],
            "options": [{"letter": o["letter"], "file": o["file"]} for o in t["options"]],
        }
        for t in trials
    ]
    public_json = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    mapping_json = json.dumps({"trials": trials}, ensure_ascii=False).replace("</", "<\\/")
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Émotions — casting contrasté</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}.card{{border:1px solid #999;border-radius:12px;padding:1rem}}audio{{width:100%}}label{{display:block;margin:.55rem 0}}button{{padding:.7rem 1rem;margin:.4rem}}.hidden{{display:none}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><h1>Émotions — personnages contrastés</h1><p>3 écrans. Écoutez les deux références, puis A et B. Identifiez A, jugez le jeu de A et B, puis le français.</p><main id="app"></main><script>const trials={public_json};const mapping={mapping_json};let i=0;const responses={{}};function audio(src){{return `<audio controls preload="none" src="${{src}}"></audio>`}}function render(){{const t=trials[i];document.getElementById('app').innerHTML=`<h2>${{i+1}}/3 — ${{t.label}}</h2><p>${{t.text}}</p><div class="grid"><div class="card"><h3>Référence 1</h3>${{audio(t.references[0].file)}}<h3>Référence 2</h3>${{audio(t.references[1].file)}}</div><div class="card"><h3>A</h3>${{audio(t.options[0].file)}}<h3>B</h3>${{audio(t.options[1].file)}}</div></div><h3>À quelle référence correspond A ?</h3><label><input type="radio" name="identity" value="Référence 1"> Référence 1</label><label><input type="radio" name="identity" value="Référence 2"> Référence 2</label><label><input type="radio" name="identity" value="uncertain"> Impossible à distinguer</label><h3>Le jeu correspond-il à l'intention ?</h3><label>A : <select id="actingA"><option value="">—</option><option value="yes">Oui</option><option value="no">Non</option></select></label><label>B : <select id="actingB"><option value="">—</option><option value="yes">Oui</option><option value="no">Non</option></select></label><h3>Français</h3><label><select id="french"><option value="">—</option><option value="both-good">Les deux sont bons</option><option value="a-defect">Défaut éliminatoire sur A</option><option value="b-defect">Défaut éliminatoire sur B</option><option value="both-defect">Défaut éliminatoire sur les deux</option></select></label><p><button onclick="save()">${{i===trials.length-1?'Terminer':'Suivant'}}</button></p>`}}function save(){{const ident=document.querySelector('input[name=identity]:checked');const a=document.getElementById('actingA').value,b=document.getElementById('actingB').value,f=document.getElementById('french').value;if(!ident||!a||!b||!f){{alert('Répondez aux quatre questions.');return}}responses[trials[i].id]={{identity:ident.value,actingA:a,actingB:b,french:f}};i++;if(i<trials.length)render();else finish()}}function finish(){{document.getElementById('app').innerHTML=`<h2>Terminé</h2><p>Exportez le JSON et envoyez-le dans la conversation.</p><button onclick="download()">Exporter le JSON</button>`}}function download(){{const blob=new Blob([JSON.stringify({{schema:'qwen3-contrast-emotion-results-v1',exported_at:new Date().toISOString(),responses,mapping}},null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='qwen3-contrast-emotion-results.json';a.click();URL.revokeObjectURL(a.href)}}render();</script></body></html>'''
    (output_dir / "index.html").write_text(html, encoding="utf-8")
