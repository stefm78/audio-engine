"""kNN-VC killer for post-expression speaker identity locking.

Lab only. Reuses existing expressive French audio and fixed neutral references.
No new TTS is generated. The first paid step is one Claire-panic -> Lucie
conversion; the remaining three conversions are allowed only if an independent
speaker verifier ranks that output closer to Lucie than Claire.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path

SCHEMA = "knnvc-identity-lock-killer-v1"
KNNVC_REVISION = "c616845c4e309e24d5927f15adbdf277a3d65358"
KNNVC_RELEASE = "v0.1"
WAVLM_LARGE_SHA256 = "6fb4b3c3e6aa567f0a997b30855859cb81528ee8078802af439f7b2da0bf100f"
ECAPA_REVISION = "eac27266f68caa806381260bd44ace38b136c76a"
SOURCE_RUN_ID = 32823632721
SOURCE_ARTIFACT = "voice-casting-qwen3-contrast-emotion-killer-recovery"
SOURCE_ROLE = "claire"
BLIND_SEED = 2026082583
TOPK = 4

REFERENCE_SHA256 = {
    "claire": "3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe",
    "lucie": "9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822",
}
CASES = (
    {"id": "panic", "label": "Panique urgente"},
    {"id": "sadness-contained", "label": "Tristesse contenue"},
)
TARGETS = ("claire", "lucie")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def experiment_spec() -> dict:
    return {
        "schema": SCHEMA,
        "architecture": "expressive-source-then-reference-retrieval-voice-conversion",
        "engine": {
            "name": "kNN-VC",
            "source_revision": KNNVC_REVISION,
            "release": KNNVC_RELEASE,
            "topk": TOPK,
            "wavlm_large_sha256": WAVLM_LARGE_SHA256,
            "conversion_training": False,
        },
        "independent_verifier": {
            "name": "speechbrain/spkrec-ecapa-voxceleb",
            "revision": ECAPA_REVISION,
            "license": "Apache-2.0",
            "used_by_converter": False,
        },
        "source": {
            "run_id": SOURCE_RUN_ID,
            "artifact": SOURCE_ARTIFACT,
            "role": SOURCE_ROLE,
            "new_tts_generation": False,
            "cases": [dict(case) for case in CASES],
        },
        "targets": list(TARGETS),
        "reference_sha256": dict(REFERENCE_SHA256),
        "conversion_budget": {
            "smoke_first": "panic:claire-source -> lucie-target",
            "maximum_conversions": 4,
            "new_tts_clips": 0,
        },
        "automatic_gate": {
            "smoke": "independent ECAPA: Lucie-target output must be closer to Lucie reference than Claire reference",
            "nearest_reference": "all four outputs must rank their intended target first",
            "topology": "min(same-target cross-emotion similarity) > max(cross-target same-emotion similarity)",
            "absolute_threshold": False,
            "claim": "independent speaker-embedding prefilter only; human identity proof still required",
        },
        "human_gate": {
            "screens": 2,
            "identity": "2/2 blind mappings correct",
            "acting": "4/4 yes",
            "french": "both-good on both screens",
            "ui": "radio-only",
        },
        "licenses": {
            "knnvc_code": "MIT",
            "wavlm": "MIT",
            "ecapa": "Apache-2.0",
            "checkpoint_legal_qualification": False,
            "note": "Official kNN-VC release assets are evaluated in Lab; capture their SHA256 in the run before any production qualification.",
        },
        "claims": {
            "identity_lock_qualified": False,
            "emotion_preservation_qualified": False,
            "french_qualified": False,
            "long_form_qualified": False,
            "age_lineage": False,
            "production_promoted": False,
        },
    }


def validate_source_bundle(source_dir) -> dict:
    root = Path(source_dir)
    refs = {}
    for role, expected in REFERENCE_SHA256.items():
        path = root / f"reference-{role}.wav"
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256(path)
        if actual != expected:
            raise ValueError(f"{role} reference hash mismatch: {actual}")
        refs[role] = path

    sources = {}
    for case in CASES:
        path = root / "clips" / f"{SOURCE_ROLE}--{case['id']}.wav"
        if not path.is_file():
            raise FileNotFoundError(path)
        sources[case["id"]] = path
    return {"references": refs, "sources": sources}


def smoke_gate(similarity_to_claire: float, similarity_to_lucie: float) -> dict:
    claire = float(similarity_to_claire)
    lucie = float(similarity_to_lucie)
    margin = lucie - claire
    return {
        "eligible": margin > 0.0,
        "similarity_to_claire": round(claire, 6),
        "similarity_to_lucie": round(lucie, 6),
        "target_margin": round(margin, 6),
        "rule": "lucie > claire",
        "absolute_threshold": False,
        "verifier_independent_of_converter": True,
    }


def topology_gate(reference_scores: dict, pair_scores: dict) -> dict:
    expected_outputs = {f"{case['id']}:{target}" for case in CASES for target in TARGETS}
    if set(reference_scores) != expected_outputs:
        raise ValueError("reference score keys do not match the four-conversion contract")

    nearest = {}
    for output_id, scores in reference_scores.items():
        if set(scores) != set(TARGETS):
            raise ValueError(f"invalid reference scores for {output_id}")
        target = output_id.split(":", 1)[1]
        other = "lucie" if target == "claire" else "claire"
        intended = float(scores[target])
        alternate = float(scores[other])
        nearest[output_id] = {
            "pass": intended > alternate,
            "intended": round(intended, 6),
            "alternate": round(alternate, 6),
            "margin": round(intended - alternate, 6),
        }

    required_pairs = {"same_claire", "same_lucie", "cross_panic", "cross_sadness-contained"}
    if set(pair_scores) != required_pairs:
        raise ValueError("pair score keys do not match the topology contract")
    pairs = {key: float(value) for key, value in pair_scores.items()}
    min_same = min(pairs["same_claire"], pairs["same_lucie"])
    max_cross = max(pairs["cross_panic"], pairs["cross_sadness-contained"])
    topology_margin = min_same - max_cross
    eligible = all(item["pass"] for item in nearest.values()) and topology_margin > 0.0
    return {
        "eligible": eligible,
        "nearest_reference": nearest,
        "min_same_target_cross_emotion": round(min_same, 6),
        "max_cross_target_same_emotion": round(max_cross, 6),
        "topology_margin": round(topology_margin, 6),
        "pair_scores": {key: round(value, 6) for key, value in pairs.items()},
        "rule": "all intended refs rank first AND min_same > max_cross",
        "absolute_threshold": False,
        "verifier_independent_of_converter": True,
        "claim": "prefilter only, not human identity proof",
    }


def _build_trials(rendered: dict, *, seed: int = BLIND_SEED) -> list[dict]:
    rnd = random.Random(seed)
    trials = []
    for case in CASES:
        case_id = case["id"]
        options = [{"role": role, "file": rendered[f"{case_id}:{role}"]} for role in TARGETS]
        rnd.shuffle(options)
        trials.append(
            {
                "id": case_id,
                "label": case["label"],
                "references": [
                    {"role": "claire", "label": "Référence 1", "file": "reference-claire.wav"},
                    {"role": "lucie", "label": "Référence 2", "file": "reference-lucie.wav"},
                ],
                "options": [{"letter": letter, **item} for letter, item in zip("AB", options)],
                "correct_reference_for_A": "Référence 1" if options[0]["role"] == "claire" else "Référence 2",
            }
        )
    return trials


def assemble_bundle(source_dir, conversion_dir, output_dir, *, seed: int = BLIND_SEED) -> dict:
    source = validate_source_bundle(source_dir)
    conversion_dir, output_dir = Path(conversion_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    result = json.loads((conversion_dir / "conversion-result.json").read_text(encoding="utf-8"))
    if result.get("status") != "success" or int(result.get("conversion_count", 0)) != 4:
        raise ValueError("four successful conversions required for full gate")
    smoke = smoke_gate(result["smoke"]["similarity_to_claire"], result["smoke"]["similarity_to_lucie"])
    if not smoke["eligible"]:
        raise ValueError("full bundle cannot be assembled after failed smoke gate")

    expected = {f"{case['id']}:{target}" for case in CASES for target in TARGETS}
    outputs = result.get("outputs") or {}
    if set(outputs) != expected:
        raise ValueError("conversion outputs violate four-clip budget")
    rendered = {}
    for output_id, relative in outputs.items():
        src = conversion_dir / relative
        if not src.is_file():
            raise FileNotFoundError(src)
        name = output_id.replace(":", "--") + ".wav"
        shutil.copy2(src, clips_dir / name)
        rendered[output_id] = f"clips/{name}"
    for role, src in source["references"].items():
        shutil.copy2(src, output_dir / f"reference-{role}.wav")

    prefilter = topology_gate(result["reference_scores"], result["pair_scores"])
    manifest = {
        **experiment_spec(),
        "status": "human-gate-ready" if prefilter["eligible"] else "auto-rejected",
        "release_asset_sha256": result.get("release_asset_sha256", {}),
        "smoke": smoke,
        "prefilter": prefilter,
        "rendered": rendered,
        "trial_count": 2 if prefilter["eligible"] else 0,
    }
    if prefilter["eligible"]:
        trials = _build_trials(rendered, seed=seed)
        manifest["trials"] = trials
        _write_player(output_dir, trials)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def _write_player(output_dir: Path, trials: list[dict]) -> None:
    public = [
        {
            "id": trial["id"],
            "label": trial["label"],
            "references": trial["references"],
            "options": [{"letter": item["letter"], "file": item["file"]} for item in trial["options"]],
        }
        for trial in trials
    ]
    public_json = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    mapping_json = json.dumps({"trials": trials}, ensure_ascii=False).replace("</", "<\\/")
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>kNN-VC — verrouillage d’identité</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}.card{{border:1px solid #999;border-radius:12px;padding:1rem}}audio{{width:100%}}label{{display:block;margin:.55rem 0}}fieldset{{border:0;padding:0;margin:1rem 0}}legend{{font-weight:700}}button{{padding:.7rem 1rem;margin:.4rem}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><h1>kNN-VC — verrouillage d’identité après jeu</h1><p>2 écrans. Sur chaque écran, A et B partent exactement du même jeu source ; seule la référence d’identité change.</p><main id="app"></main><script>const trials={public_json};const mapping={mapping_json};let i=0;const responses={{}};function audio(src){{return `<audio controls preload="none" src="${{src}}"></audio>`}}function radio(name,value,label){{return `<label><input type="radio" name="${{name}}" value="${{value}}"> ${{label}}</label>`}}function checked(name){{const el=document.querySelector(`input[name="${{name}}"]:checked`);return el?el.value:''}}function render(){{const t=trials[i];document.getElementById('app').innerHTML=`<h2>${{i+1}}/2 — ${{t.label}}</h2><div class="grid"><div class="card"><h3>Référence 1</h3>${{audio(t.references[0].file)}}<h3>Référence 2</h3>${{audio(t.references[1].file)}}</div><div class="card"><h3>A</h3>${{audio(t.options[0].file)}}<h3>B</h3>${{audio(t.options[1].file)}}</div></div><fieldset><legend>À quelle référence correspond A ?</legend>${{radio('identity','Référence 1','Référence 1')}}${{radio('identity','Référence 2','Référence 2')}}${{radio('identity','uncertain','Impossible à distinguer')}}</fieldset><fieldset><legend>Le jeu de A correspond-il à l’émotion annoncée ?</legend>${{radio('actingA','yes','Oui')}}${{radio('actingA','no','Non')}}</fieldset><fieldset><legend>Le jeu de B correspond-il à l’émotion annoncée ?</legend>${{radio('actingB','yes','Oui')}}${{radio('actingB','no','Non')}}</fieldset><fieldset><legend>Français</legend>${{radio('french','both-good','Les deux sont bons')}}${{radio('french','a-defect','Défaut éliminatoire sur A')}}${{radio('french','b-defect','Défaut éliminatoire sur B')}}${{radio('french','both-defect','Défaut éliminatoire sur les deux')}}</fieldset><p><button onclick="save()">${{i===trials.length-1?'Terminer':'Suivant'}}</button></p>`}}function save(){{const identity=checked('identity'),actingA=checked('actingA'),actingB=checked('actingB'),french=checked('french');if(!identity||!actingA||!actingB||!french){{alert('Répondez aux quatre questions.');return}}responses[trials[i].id]={{identity,actingA,actingB,french}};i++;if(i<trials.length)render();else finish()}}function finish(){{document.getElementById('app').innerHTML=`<h2>Terminé</h2><p>Exportez le JSON et envoyez-le dans la conversation.</p><button onclick="download()">Exporter le JSON</button>`}}function download(){{const blob=new Blob([JSON.stringify({{schema:'knnvc-identity-lock-results-v1',exported_at:new Date().toISOString(),responses,mapping}},null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='knnvc-identity-lock-results.json';a.click();URL.revokeObjectURL(a.href)}}render();</script></body></html>'''
    if "<select" in html.lower():
        raise AssertionError("Voice Lab questionnaires must be radio-only")
    (Path(output_dir) / "index.html").write_text(html, encoding="utf-8")
