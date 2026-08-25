"""Panic-robust casting follow-up for Qwen3 VoiceDesign.

The previous contrasted pair was human-qualified in neutral speech and remained
recognisable for wonder and contained sadness, but failed identity under panic.
This experiment therefore reuses all existing evidence and generates only the two
missing panic clips needed to compare all four candidate pairings.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
from pathlib import Path

from .voice_casting_distance import compare_anchors
from .voice_lab_qwen3_contrast_casting import CANDIDATES

QWEN_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
VOICE_DESIGN_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
VOICE_DESIGN_MODEL_REVISION = "5ecdb67327fd37bb2e042aab12ff7391903235d3"
SOURCE_RUN_ID = 32818950167
SOURCE_ANCHOR_ARTIFACTS = {
    "claire": "qwen3-contrast-anchors-claire",
    "lucie": "qwen3-contrast-anchors-lucie",
}
FAILING_RUN_ID = 32823632721
FAILING_ARTIFACT = "voice-casting-qwen3-contrast-emotion-killer-recovery"
CURRENT_FAILING_PAIR = ("claire-a", "lucie-b")
NEUTRAL_REQUIRED_SCORE = 33.334
PANIC_MINIMUM_RATIO = 1.35
PANIC_MINIMUM_MARGIN = 15.0
BLIND_SEED = 2026082511

ANCHOR_SHA256 = {
    "claire-a": "3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe",
    "claire-b": "b32cdcdacddec0912a2de988e5621ecc8e22015994f4e6b0656669d2718dcb1c",
    "lucie-a": "614e09f75b6ad9b0332dfd2a12ec35524bb28d20f63fa66f22868ad941ec2134",
    "lucie-b": "9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822",
}
FAILING_PANIC_SHA256 = {
    "claire-a": "ac92fd1f8346b981ac7518e1e698cf8b1c31a96dff069ad60a2d017a17ff9d7f",
    "lucie-b": "8168d32c7a1ee81485396ff426f1fa6ad306a54765d60351e10dbe7231da3a09",
}

PANIC = {
    "id": "panic",
    "label": "Panique urgente",
    "text": "Vite ! Ils arrivent ! Fermez la porte !",
    "acting": (
        "Panique urgente et crédible : souffle court, débit accéléré, tension élevée. "
        "Reste intelligible et naturelle, sans caricature et sans déformer le timbre."
    ),
}
CONFIRM = {
    "id": "panic-confirm",
    "label": "Danger immédiat",
    "text": "Non ! Ne restez pas là ! Sortez, maintenant !",
    "acting": (
        "Danger immédiat et crédible : urgence forte, souffle court, débit vif et tension nette. "
        "Reste intelligible, naturelle et conserve l'identité vocale."
    ),
}
NEW_CANONICAL_CANDIDATES = ("claire-b", "lucie-a")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def candidate_spec(candidate_id: str) -> dict:
    if candidate_id not in CANDIDATES:
        raise ValueError(f"unknown candidate: {candidate_id}")
    return {"candidate_id": candidate_id, **CANDIDATES[candidate_id]}


def expressive_instruction(candidate_id: str, case_id: str) -> str:
    case = PANIC if case_id == PANIC["id"] else CONFIRM if case_id == CONFIRM["id"] else None
    if case is None:
        raise ValueError(f"unknown case: {case_id}")
    return (
        candidate_spec(candidate_id)["instruct"]
        + " Conserve cette identité vocale de façon reconnaissable. Interprétation : "
        + case["acting"]
    )


def panic_required_score(baseline_score: float) -> float:
    return round(
        max(
            float(baseline_score) * PANIC_MINIMUM_RATIO,
            float(baseline_score) + PANIC_MINIMUM_MARGIN,
        ),
        3,
    )


def pair_is_eligible(*, neutral_score: float, panic_score: float, baseline_panic_score: float) -> bool:
    return (
        float(neutral_score) >= NEUTRAL_REQUIRED_SCORE
        and float(panic_score) >= panic_required_score(baseline_panic_score)
    )


def _unique(root: Path, name: str) -> Path:
    matches = list(Path(root).rglob(name))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {name}, got {len(matches)}")
    return matches[0]


def _verified_anchor(root: Path, candidate_id: str) -> Path:
    path = _unique(root, f"{candidate_id}.wav")
    actual = _sha256(path)
    expected = ANCHOR_SHA256[candidate_id]
    if actual != expected:
        raise ValueError(f"anchor hash mismatch for {candidate_id}: {actual}")
    return path


def select_pair(neutral_root, new_panic_root, failing_bundle, output_dir) -> dict:
    neutral_root = Path(neutral_root)
    new_panic_root = Path(new_panic_root)
    failing_bundle = Path(failing_bundle)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    neutral = {candidate_id: _verified_anchor(neutral_root, candidate_id) for candidate_id in CANDIDATES}

    failing_panic = {
        "claire-a": failing_bundle / "clips" / "claire--panic.wav",
        "lucie-b": failing_bundle / "clips" / "lucie--panic.wav",
    }
    for candidate_id, path in failing_panic.items():
        if not path.is_file() or _sha256(path) != FAILING_PANIC_SHA256[candidate_id]:
            raise ValueError(f"failing panic source mismatch for {candidate_id}")

    panic = {
        "claire-a": failing_panic["claire-a"],
        "lucie-b": failing_panic["lucie-b"],
        "claire-b": _unique(new_panic_root, "claire-b.wav"),
        "lucie-a": _unique(new_panic_root, "lucie-a.wav"),
    }

    baseline = compare_anchors(panic["claire-a"], panic["lucie-b"])
    required_panic = panic_required_score(baseline["score"])
    comparisons = []
    for claire_id in ("claire-a", "claire-b"):
        for lucie_id in ("lucie-a", "lucie-b"):
            neutral_distance = compare_anchors(neutral[claire_id], neutral[lucie_id])
            panic_distance = compare_anchors(panic[claire_id], panic[lucie_id])
            current = (claire_id, lucie_id) == CURRENT_FAILING_PAIR
            eligible = (
                not current
                and pair_is_eligible(
                    neutral_score=neutral_distance["score"],
                    panic_score=panic_distance["score"],
                    baseline_panic_score=baseline["score"],
                )
            )
            comparisons.append(
                {
                    "claire_id": claire_id,
                    "lucie_id": lucie_id,
                    "current_failing_pair": current,
                    "eligible": eligible,
                    "neutral_score": neutral_distance["score"],
                    "panic_score": panic_distance["score"],
                    "neutral_components": neutral_distance["components"],
                    "panic_components": panic_distance["components"],
                }
            )

    eligible = [item for item in comparisons if item["eligible"]]
    winner = max(eligible, key=lambda item: (item["panic_score"], item["neutral_score"])) if eligible else None
    result = {
        "schema": "qwen3-panic-robust-casting-v1",
        "status": "selected" if winner else "rejected",
        "source_run_id": SOURCE_RUN_ID,
        "failing_run_id": FAILING_RUN_ID,
        "current_failing_pair": list(CURRENT_FAILING_PAIR),
        "baseline_panic_score": baseline["score"],
        "required_panic_score": required_panic,
        "neutral_required_score": NEUTRAL_REQUIRED_SCORE,
        "comparisons": comparisons,
        "selected": winner,
        "claim": "acoustic-prefilter-only-not-speaker-identity-qualification",
    }
    if winner:
        for role, candidate_id in (("claire", winner["claire_id"]), ("lucie", winner["lucie_id"])):
            shutil.copy2(neutral[candidate_id], output_dir / f"reference-{role}.wav")
            shutil.copy2(panic[candidate_id], output_dir / f"panic-{role}.wav")
        result["selected_anchor_sha256"] = {
            role: _sha256(output_dir / f"reference-{role}.wav") for role in ("claire", "lucie")
        }
        result["selected_panic_sha256"] = {
            role: _sha256(output_dir / f"panic-{role}.wav") for role in ("claire", "lucie")
        }
    (output_dir / "selection.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def selected_candidate(selection_dir, role: str) -> dict:
    selection = json.loads((Path(selection_dir) / "selection.json").read_text(encoding="utf-8"))
    if selection.get("status") != "selected":
        raise ValueError("panic-robust casting did not select a pair")
    key = f"{role}_id"
    candidate_id = selection["selected"][key]
    spec = candidate_spec(candidate_id)
    if spec["role"] != role:
        raise ValueError("selected role mismatch")
    return spec


def assemble_bundle(selection_dir, confirmation_root, output_dir, *, seed=BLIND_SEED) -> dict:
    selection_dir = Path(selection_dir)
    confirmation_root = Path(confirmation_root)
    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    selection = json.loads((selection_dir / "selection.json").read_text(encoding="utf-8"))
    if selection.get("status") != "selected":
        raise ValueError("cannot assemble rejected panic-robust casting")

    refs = {}
    canonical = {}
    confirm = {}
    for role in ("claire", "lucie"):
        ref_name = f"reference-{role}.wav"
        shutil.copy2(selection_dir / ref_name, output_dir / ref_name)
        refs[role] = ref_name
        canonical_name = f"{role}--panic.wav"
        shutil.copy2(selection_dir / f"panic-{role}.wav", clips_dir / canonical_name)
        canonical[role] = f"clips/{canonical_name}"
        confirmation = _unique(confirmation_root, f"{role}--panic-confirm.wav")
        confirm_name = f"{role}--panic-confirm.wav"
        shutil.copy2(confirmation, clips_dir / confirm_name)
        confirm[role] = f"clips/{confirm_name}"

    cases = (
        (PANIC, canonical),
        (CONFIRM, confirm),
    )
    rnd = random.Random(seed)
    trials = []
    for case, files in cases:
        options = [{"role": role, "file": files[role]} for role in ("claire", "lucie")]
        rnd.shuffle(options)
        trials.append(
            {
                "id": case["id"],
                "label": case["label"],
                "text": case["text"],
                "references": [
                    {"role": "claire", "label": "Référence 1", "file": refs["claire"]},
                    {"role": "lucie", "label": "Référence 2", "file": refs["lucie"]},
                ],
                "options": [{"letter": letter, **option} for letter, option in zip("AB", options)],
                "correct_reference_for_A": "Référence 1" if options[0]["role"] == "claire" else "Référence 2",
            }
        )

    manifest = {
        "schema": "qwen3-panic-robust-human-gate-v1",
        "status": "success",
        "selected": selection["selected"],
        "baseline_panic_score": selection["baseline_panic_score"],
        "required_panic_score": selection["required_panic_score"],
        "trial_count": 2,
        "gates": {
            "identity": "2/2 blind A-to-reference mappings correct",
            "french": "both-good on both screens",
            "acting": "4/4 yes",
        },
        "claims": {
            "panic_qualified": False,
            "broader_emotion_qualified": False,
            "long_form_qualified": False,
            "age_lineage": False,
            "production_promoted": False,
        },
        "trials": trials,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
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
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Robustesse identité — panique</title><style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}.card{{border:1px solid #999;border-radius:12px;padding:1rem}}audio{{width:100%}}label{{display:block;margin:.55rem 0}}fieldset{{border:0;padding:0;margin:1rem 0}}legend{{font-weight:700;margin-bottom:.35rem}}button{{padding:.7rem 1rem;margin:.4rem}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><h1>Robustesse identité — forte urgence</h1><p>2 écrans. Tous les choix sont visibles. Écoutez les références, puis A et B.</p><main id="app"></main><script>const trials={public_json};const mapping={mapping_json};let i=0;const responses={{}};function audio(src){{return `<audio controls preload="none" src="${{src}}"></audio>`}}function radio(name,value,label){{return `<label><input type="radio" name="${{name}}" value="${{value}}"> ${{label}}</label>`}}function checked(name){{const el=document.querySelector(`input[name="${{name}}"]:checked`);return el?el.value:''}}function render(){{const t=trials[i];document.getElementById('app').innerHTML=`<h2>${{i+1}}/2 — ${{t.label}}</h2><p>${{t.text}}</p><div class="grid"><div class="card"><h3>Référence 1</h3>${{audio(t.references[0].file)}}<h3>Référence 2</h3>${{audio(t.references[1].file)}}</div><div class="card"><h3>A</h3>${{audio(t.options[0].file)}}<h3>B</h3>${{audio(t.options[1].file)}}</div></div><fieldset><legend>À quelle référence correspond A ?</legend>${{radio('identity','Référence 1','Référence 1')}}${{radio('identity','Référence 2','Référence 2')}}${{radio('identity','uncertain','Impossible à distinguer')}}</fieldset><fieldset><legend>Le jeu de A correspond-il à l'intention ?</legend>${{radio('actingA','yes','Oui')}}${{radio('actingA','no','Non')}}</fieldset><fieldset><legend>Le jeu de B correspond-il à l'intention ?</legend>${{radio('actingB','yes','Oui')}}${{radio('actingB','no','Non')}}</fieldset><fieldset><legend>Français</legend>${{radio('french','both-good','Les deux sont bons')}}${{radio('french','a-defect','Défaut éliminatoire sur A')}}${{radio('french','b-defect','Défaut éliminatoire sur B')}}${{radio('french','both-defect','Défaut éliminatoire sur les deux')}}</fieldset><p><button onclick="save()">${{i===trials.length-1?'Terminer':'Suivant'}}</button></p>`}}function save(){{const identity=checked('identity'),actingA=checked('actingA'),actingB=checked('actingB'),french=checked('french');if(!identity||!actingA||!actingB||!french){{alert('Répondez aux quatre questions.');return}}responses[trials[i].id]={{identity,actingA,actingB,french}};i++;if(i<trials.length)render();else finish()}}function finish(){{document.getElementById('app').innerHTML=`<h2>Terminé</h2><p>Exportez le JSON et envoyez-le dans la conversation.</p><button onclick="download()">Exporter le JSON</button>`}}function download(){{const blob=new Blob([JSON.stringify({{schema:'qwen3-panic-robust-results-v1',exported_at:new Date().toISOString(),responses,mapping}},null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='qwen3-panic-robust-results.json';a.click();URL.revokeObjectURL(a.href)}}render();</script></body></html>'''
    if "<select" in html.lower():
        raise AssertionError("Voice Lab questionnaires must be radio-only")
    (output_dir / "index.html").write_text(html, encoding="utf-8")
