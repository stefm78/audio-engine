"""Qwen3 CustomVoice killer for explicit speaker-id / emotion separation.

Lab only. This experiment does not attempt to reproduce the failed Claire/Lucie
VoiceDesign cast. It tests a narrower architectural hypothesis: a fixed speaker
identifier must remain more stable across emotion than two different speaker
identities are similar within the same emotion.
"""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

from .voice_casting_distance import compare_anchors

SCHEMA = "qwen3-customvoice-identity-emotion-killer-v1"
QWEN_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
MODEL_REVISION = "b611c9f8f2ad5c741ed9c7a0a6a3750e43e0dfd7"
BLIND_SEED = 2026082567

# Built-in Qwen speaker IDs: identity is categorical and separate from `instruct`.
CHARACTERS = {
    "serena": {"speaker": "Serena", "seed": 2026082561},
    "vivian": {"speaker": "Vivian", "seed": 2026082571},
}

# Same text in both emotions removes text/duration as a confound for the cheap gate.
COMMON_TEXT = (
    "Ils sont là, juste derrière la porte. "
    "Je savais qu'ils finiraient par revenir."
)

CASES = (
    {
        "id": "panic",
        "label": "Panique urgente",
        "instruction": (
            "Panique urgente et crédible. Parle avec un souffle court, un débit accéléré "
            "et une tension élevée. Reste intelligible et naturelle, sans caricature."
        ),
    },
    {
        "id": "sadness-contained",
        "label": "Tristesse contenue",
        "instruction": (
            "Tristesse contenue et résignée. Parle avec une énergie basse, un souffle "
            "légèrement fragile et beaucoup de retenue. Aucun sanglot, aucun mélodrame."
        ),
    },
)


def character_spec(role: str) -> dict:
    if role not in CHARACTERS:
        raise ValueError(f"unknown role: {role}")
    return {"role": role, **CHARACTERS[role]}


def case_spec(case_id: str) -> dict:
    case = next((item for item in CASES if item["id"] == case_id), None)
    if case is None:
        raise ValueError(f"unknown case: {case_id}")
    return dict(case)


def experiment_spec() -> dict:
    return {
        "schema": SCHEMA,
        "architecture": "qwen3-customvoice-fixed-speaker-id-plus-independent-instruct",
        "qwen_revision": QWEN_REVISION,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
        "language": "French",
        "text": COMMON_TEXT,
        "characters": {role: character_spec(role) for role in CHARACTERS},
        "cases": [dict(case) for case in CASES],
        "generation_contract": {
            "speaker_channel": "fixed built-in speaker id",
            "emotion_channel": "instruct only",
            "same_text_across_emotions": True,
            "clip_count": 4,
        },
        "automatic_gate": {
            "rule": "min(cross-speaker same-emotion) > max(same-speaker cross-emotion)",
            "threshold_tuning": False,
            "claim": "cheap topology prefilter only; not speaker-identity proof",
        },
        "human_gate": {
            "screens": 2,
            "identity": "2/2 blind cross-emotion mappings correct",
            "acting": "4/4 yes",
            "french": "both-good on both screens",
            "ui": "radio-only",
        },
        "claims": {
            "architecture_qualified": False,
            "custom_character_catalog_qualified": False,
            "long_form_qualified": False,
            "age_lineage": False,
            "production_promoted": False,
        },
    }


def topology_gate(distances: dict) -> dict:
    required = {"same_serena", "same_vivian", "cross_panic", "cross_sadness-contained"}
    if set(distances) != required:
        missing = sorted(required - set(distances))
        extra = sorted(set(distances) - required)
        raise ValueError(f"invalid topology distances; missing={missing}, extra={extra}")
    scores = {key: float(value["score"]) for key, value in distances.items()}
    max_within = max(scores["same_serena"], scores["same_vivian"])
    min_cross = min(scores["cross_panic"], scores["cross_sadness-contained"])
    margin = min_cross - max_within
    return {
        "eligible": margin > 0.0,
        "max_same_speaker_cross_emotion": round(max_within, 3),
        "min_cross_speaker_same_emotion": round(min_cross, 3),
        "topology_margin": round(margin, 3),
        "rule": "min_cross > max_within",
        "claim": "prefilter-only-not-speaker-identity-qualification",
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


def assemble_bundle(input_root, output_dir, *, seed: int = BLIND_SEED) -> dict:
    input_root, output_dir = Path(input_root), Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    rendered = {}
    for role in CHARACTERS:
        root = _role_root(input_root, role)
        result = json.loads((root / "character-result.json").read_text(encoding="utf-8"))
        spec = character_spec(role)
        if result.get("status") != "success":
            raise ValueError(f"render failed for {role}")
        if result.get("speaker") != spec["speaker"] or int(result.get("seed")) != int(spec["seed"]):
            raise ValueError(f"speaker contract mismatch for {role}")
        by_id = {item["id"]: item for item in result.get("rendered", [])}
        expected = {case["id"] for case in CASES}
        if set(by_id) != expected:
            raise ValueError(f"incomplete cases for {role}")
        for case in CASES:
            source = root / by_id[case["id"]]["file"]
            name = f"{role}--{case['id']}.wav"
            shutil.copy2(source, clips_dir / name)
            rendered[(role, case["id"])] = f"clips/{name}"

    distances = {
        "same_serena": compare_anchors(
            output_dir / rendered[("serena", "panic")],
            output_dir / rendered[("serena", "sadness-contained")],
        ),
        "same_vivian": compare_anchors(
            output_dir / rendered[("vivian", "panic")],
            output_dir / rendered[("vivian", "sadness-contained")],
        ),
        "cross_panic": compare_anchors(
            output_dir / rendered[("serena", "panic")],
            output_dir / rendered[("vivian", "panic")],
        ),
        "cross_sadness-contained": compare_anchors(
            output_dir / rendered[("serena", "sadness-contained")],
            output_dir / rendered[("vivian", "sadness-contained")],
        ),
    }
    prefilter = topology_gate(distances)

    manifest = {
        **experiment_spec(),
        "status": "human-gate-ready" if prefilter["eligible"] else "auto-rejected",
        "distance_diagnostics_not_identity_proof": distances,
        "prefilter": prefilter,
        "trial_count": 2 if prefilter["eligible"] else 0,
        "rendered": {
            f"{role}:{case['id']}": rendered[(role, case["id"])]
            for role in CHARACTERS
            for case in CASES
        },
    }

    if prefilter["eligible"]:
        trials = _build_trials(rendered, seed=seed)
        manifest["trials"] = trials
        _write_player(output_dir, trials)

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def _build_trials(rendered: dict, *, seed: int) -> list[dict]:
    rnd = random.Random(seed)
    by_id = {case["id"]: case for case in CASES}
    pairs = (("panic", "sadness-contained"), ("sadness-contained", "panic"))
    trials = []
    for target_id, reference_id in pairs:
        options = [{"role": role, "file": rendered[(role, target_id)]} for role in CHARACTERS]
        rnd.shuffle(options)
        trials.append(
            {
                "id": f"{target_id}-from-{reference_id}",
                "label": by_id[target_id]["label"],
                "text": COMMON_TEXT,
                "reference_emotion": reference_id,
                "target_emotion": target_id,
                "references": [
                    {"role": "serena", "label": "Référence 1", "file": rendered[("serena", reference_id)]},
                    {"role": "vivian", "label": "Référence 2", "file": rendered[("vivian", reference_id)]},
                ],
                "options": [
                    {"letter": letter, **option} for letter, option in zip("AB", options)
                ],
                "correct_reference_for_A": (
                    "Référence 1" if options[0]["role"] == "serena" else "Référence 2"
                ),
            }
        )
    return trials


def _write_player(output_dir: Path, trials: list[dict]) -> None:
    public = [
        {
            "id": trial["id"],
            "label": trial["label"],
            "text": trial["text"],
            "references": trial["references"],
            "options": [{"letter": item["letter"], "file": item["file"]} for item in trial["options"]],
        }
        for trial in trials
    ]
    public_json = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    mapping_json = json.dumps({"trials": trials}, ensure_ascii=False).replace("</", "<\\/")
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Identité fixe + émotion séparée</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}.card{{border:1px solid #999;border-radius:12px;padding:1rem}}audio{{width:100%}}label{{display:block;margin:.55rem 0}}fieldset{{border:0;padding:0;margin:1rem 0}}legend{{font-weight:700;margin-bottom:.35rem}}button{{padding:.7rem 1rem;margin:.4rem}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><h1>Identité fixe + émotion séparée</h1><p>2 écrans. Les références jouent la même phrase dans l’émotion opposée. Associez A à sa voix de référence, puis jugez le jeu et le français.</p><main id="app"></main><script>const trials={public_json};const mapping={mapping_json};let i=0;const responses={{}};function audio(src){{return `<audio controls preload="none" src="${{src}}"></audio>`}}function radio(name,value,label){{return `<label><input type="radio" name="${{name}}" value="${{value}}"> ${{label}}</label>`}}function checked(name){{const el=document.querySelector(`input[name="${{name}}"]:checked`);return el?el.value:''}}function render(){{const t=trials[i];document.getElementById('app').innerHTML=`<h2>${{i+1}}/2 — ${{t.label}}</h2><p>${{t.text}}</p><div class="grid"><div class="card"><h3>Référence 1</h3>${{audio(t.references[0].file)}}<h3>Référence 2</h3>${{audio(t.references[1].file)}}</div><div class="card"><h3>A</h3>${{audio(t.options[0].file)}}<h3>B</h3>${{audio(t.options[1].file)}}</div></div><fieldset><legend>À quelle référence correspond A ?</legend>${{radio('identity','Référence 1','Référence 1')}}${{radio('identity','Référence 2','Référence 2')}}${{radio('identity','uncertain','Impossible à distinguer')}}</fieldset><fieldset><legend>Le jeu de A correspond-il à l’émotion annoncée ?</legend>${{radio('actingA','yes','Oui')}}${{radio('actingA','no','Non')}}</fieldset><fieldset><legend>Le jeu de B correspond-il à l’émotion annoncée ?</legend>${{radio('actingB','yes','Oui')}}${{radio('actingB','no','Non')}}</fieldset><fieldset><legend>Français</legend>${{radio('french','both-good','Les deux sont bons')}}${{radio('french','a-defect','Défaut éliminatoire sur A')}}${{radio('french','b-defect','Défaut éliminatoire sur B')}}${{radio('french','both-defect','Défaut éliminatoire sur les deux')}}</fieldset><p><button onclick="save()">${{i===trials.length-1?'Terminer':'Suivant'}}</button></p>`}}function save(){{const identity=checked('identity'),actingA=checked('actingA'),actingB=checked('actingB'),french=checked('french');if(!identity||!actingA||!actingB||!french){{alert('Répondez aux quatre questions.');return}}responses[trials[i].id]={{identity,actingA,actingB,french}};i++;if(i<trials.length)render();else finish()}}function finish(){{document.getElementById('app').innerHTML=`<h2>Terminé</h2><p>Exportez le JSON et envoyez-le dans la conversation.</p><button onclick="download()">Exporter le JSON</button>`}}function download(){{const blob=new Blob([JSON.stringify({{schema:'qwen3-customvoice-identity-emotion-results-v1',exported_at:new Date().toISOString(),responses,mapping}},null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='qwen3-customvoice-identity-emotion-results.json';a.click();URL.revokeObjectURL(a.href)}}render();</script></body></html>'''
    if "<select" in html.lower():
        raise AssertionError("Voice Lab questionnaires must be radio-only")
    (Path(output_dir) / "index.html").write_text(html, encoding="utf-8")
