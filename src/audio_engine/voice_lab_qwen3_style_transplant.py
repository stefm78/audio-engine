"""Qwen3 style-transplant killer: frozen character identity + foreign ICL style codes.

Research only. This intentionally exercises an unsupported prompt-component mix to
see whether Qwen3 Base can preserve a frozen character while borrowing expression
from a separate donor example.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import time
from pathlib import Path

from .providers.qwen3_style_transplant_lab import Qwen3StyleTransplantLabProvider

UPSTREAM_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
BASE_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
BASE_MODEL_REVISION = "74a6279626edc2d5a787d5b6467668eba0b86ef6"
VOICE_DESIGN_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
VOICE_DESIGN_MODEL_REVISION = "5ecdb67327fd37bb2e042aab12ff7391903235d3"
SOURCE_RUN_ID = 32772435007
SOURCE_ARTIFACT = "voice-casting-qwen3-xvector-identity-confirm"
BLIND_SEED = 2026082501

CHARACTERS = {
    "claire": {
        "label": "Référence 1",
        "anchor_file": "reference-claire-qwen3.wav",
        "sha256": "1012fdc137a848e71a9403140267e62140ad87b14ee9a3236e106b57775afa55",
    },
    "lucie": {
        "label": "Référence 2",
        "anchor_file": "reference-lucie-qwen3.wav",
        "sha256": "f42c27ce633e0d009a95079cdfddc605772bbf48e9806fba6fba3749e5aa1ee2",
    },
}

CASES = (
    {
        "id": "mystery",
        "label": "mystère inquiet",
        "text": "Écoutez... Il y a quelqu'un derrière cette porte. Pourtant, cette pièce est vide depuis des années.",
        "donor_text": "Attendez... J'ai entendu quelque chose, juste derrière nous.",
        "donor_instruct": "Voix féminine adulte française claire et naturelle. Joue un mystère inquiet retenu : voix plus basse, prudente, tension discrète, sans caricature.",
    },
    {
        "id": "wonder",
        "label": "émerveillement",
        "text": "Regardez... La brume se lève. On voit toute la vallée, jusqu'aux montagnes.",
        "donor_text": "C'est magnifique... Je n'avais jamais vu une lumière pareille.",
        "donor_instruct": "Voix féminine adulte française claire et naturelle. Joue un émerveillement sincère : ouverture, chaleur, surprise lumineuse, sans emphase théâtrale.",
    },
    {
        "id": "sadness-contained",
        "label": "tristesse contenue",
        "text": "Il est parti avant l'aube. Je savais que ce moment viendrait, mais pas si tôt.",
        "donor_text": "Je savais que ce jour viendrait... mais cela fait quand même mal.",
        "donor_instruct": "Voix féminine adulte française claire et naturelle. Joue une tristesse contenue : émotion réelle mais retenue, souffle légèrement fragile, sans sanglot ni mélodrame.",
    },
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _seed(character_id: str, case_id: str) -> int:
    return int.from_bytes(hashlib.sha256(f"20260825\0{character_id}\0{case_id}".encode()).digest()[:4], "big")


def experiment_spec():
    return {
        "schema": "qwen3-style-transplant-killer-v1",
        "architecture": "frozen character speaker embedding + foreign ICL donor speech codes",
        "upstream_revision": UPSTREAM_REVISION,
        "base_model": {"id": BASE_MODEL_ID, "revision": BASE_MODEL_REVISION},
        "voice_design_model": {"id": VOICE_DESIGN_MODEL_ID, "revision": VOICE_DESIGN_MODEL_REVISION},
        "characters": {k: dict(v) for k, v in CHARACTERS.items()},
        "cases": [dict(c) for c in CASES],
        "decision": {
            "identity_pass": "3/3 pair mappings correct",
            "french_pass": "zero invalid-French veto",
            "acting_pass": ">=5/6 clear intentions and >=2/3 per character",
            "no_tuning": True,
            "production_promotion": False,
            "age_lineage": False,
        },
    }


def render_character(character_id, anchor_dir, style_dir, output_dir, *, provider=None, model_dir=None):
    if character_id not in CHARACTERS:
        raise ValueError(f"unknown character: {character_id}")
    character = CHARACTERS[character_id]
    anchor = Path(anchor_dir) / character["anchor_file"]
    if not anchor.is_file():
        raise FileNotFoundError(anchor)
    actual = _sha256(anchor)
    if actual != character["sha256"]:
        raise ValueError(f"qualified anchor mismatch for {character_id}: expected {character['sha256']}, got {actual}")
    style_dir = Path(style_dir)
    for case in CASES:
        if not (style_dir / f"{case['id']}.wav").is_file():
            raise FileNotFoundError(style_dir / f"{case['id']}.wav")

    if provider is None:
        if model_dir is None:
            raise ValueError("model_dir is required when provider is not injected")
        provider = Qwen3StyleTransplantLabProvider(model_dir=model_dir, device="cpu")
    if getattr(provider, "identity_mode", None) != "frozen-xvector-plus-foreign-icl-style":
        raise ValueError("provider must explicitly declare style-transplant identity mode")

    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(anchor, output_dir / "reference.wav")
    identity = provider.build_identity_embedding(anchor)
    rendered = []
    started = time.monotonic()
    for index, case in enumerate(CASES, 1):
        clip_started = time.monotonic()
        print(f"START {index}/{len(CASES)} · {character_id} · {case['id']}", flush=True)
        prompt = provider.build_style_prompt(identity, style_dir / f"{case['id']}.wav", case["donor_text"])
        out = clips_dir / f"{case['id']}.wav"
        seed = _seed(character_id, case["id"])
        provider.synthesize(
            {"text": case["text"], "language": "French", "seed": seed},
            out,
            voice_clone_prompt=prompt,
        )
        elapsed = time.monotonic() - clip_started
        rendered.append({"id": case["id"], "file": f"clips/{case['id']}.wav", "seed": seed, "render_seconds": round(elapsed, 2)})
        avg = (time.monotonic() - started) / index
        print(f"SUCCESS {index}/{len(CASES)} · clip={elapsed:.1f}s · ETA≈{avg*(len(CASES)-index):.1f}s", flush=True)

    if _sha256(anchor) != character["sha256"]:
        raise ValueError("qualified anchor changed during render")
    result = {
        "schema": "qwen3-style-transplant-character-v1",
        "character_id": character_id,
        "status": "success",
        "anchor_sha256": character["sha256"],
        "rendered_count": len(rendered),
        "rendered": rendered,
        "production_promoted": False,
    }
    (output_dir / "character-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _find_root(root: Path, character_id: str) -> Path:
    matches = []
    for p in root.rglob("character-result.json"):
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("character_id") == character_id:
            matches.append(p.parent)
    if len(matches) != 1:
        raise ValueError(f"expected one result root for {character_id}, got {len(matches)}")
    return matches[0]


def assemble_bundle(input_root, output_dir, *, seed=BLIND_SEED):
    input_root, output_dir = Path(input_root), Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    roots = {c: _find_root(input_root, c) for c in CHARACTERS}
    refs, rendered = {}, {}
    for cid, character in CHARACTERS.items():
        root = roots[cid]
        result = json.loads((root / "character-result.json").read_text(encoding="utf-8"))
        if result.get("status") != "success" or result.get("rendered_count") != len(CASES):
            raise ValueError(f"incomplete render for {cid}")
        ref = root / "reference.wav"
        if _sha256(ref) != character["sha256"]:
            raise ValueError(f"reference mismatch for {cid}")
        ref_name = f"reference-{cid}.wav"
        shutil.copy2(ref, output_dir / ref_name)
        refs[cid] = ref_name
        for item in result["rendered"]:
            name = f"{cid}--{item['id']}.wav"
            shutil.copy2(root / item["file"], clips_dir / name)
            rendered[(cid, item["id"])] = f"clips/{name}"

    rnd = random.Random(seed)
    trials = []
    for case in CASES:
        options = [{"character_id": cid, "file": rendered[(cid, case["id"])]} for cid in CHARACTERS]
        rnd.shuffle(options)
        trials.append({
            "id": case["id"], "label": case["label"], "text": case["text"],
            "references": [{"id": cid, "label": CHARACTERS[cid]["label"], "file": refs[cid]} for cid in CHARACTERS],
            "options": [{"letter": letter, **option} for letter, option in zip("AB", options)],
            "correct_reference_for_A": CHARACTERS[options[0]["character_id"]]["label"],
        })
    manifest = {**experiment_spec(), "status": "success", "trial_count": len(trials), "trials": trials}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_player(output_dir, trials)
    return manifest


def _write_player(output_dir: Path, trials):
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
    payload = json.dumps(public, ensure_ascii=False).replace("</", "<\\/")
    mapping = json.dumps(trials, ensure_ascii=False).replace("</", "<\\/")
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Qwen3 style transplant</title><style>body{{font-family:system-ui,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}.card{{border:1px solid #999;border-radius:12px;padding:1rem}}audio{{width:100%}}label{{display:block;margin:.55rem 0}}button{{padding:.7rem 1rem;margin:.4rem}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><h1>Test personnage + style</h1><p>3 écrans. Évaluez uniquement ce que vous entendez.</p><p id="progress"></p><div id="app"></div><button id="back">Précédent</button><button id="next">Suivant</button><button id="export">Exporter le JSON</button><script>const trials={payload};const mapping={mapping};const KEY='qwen3-style-transplant-killer-v1';let state={{index:0,responses:{{}}}};try{{state=JSON.parse(localStorage.getItem(KEY))||state}}catch(e){{}}function save(){{try{{localStorage.setItem(KEY,JSON.stringify(state))}}catch(e){{}}}}function chosen(name){{const x=document.querySelector('input[name="'+name+'"]:checked');return x?x.value:null}}function render(){{const t=trials[state.index];document.getElementById('progress').textContent='Écran '+(state.index+1)+'/'+trials.length+' · '+t.label;const refs=t.references.map(r=>`<div><h3>${{r.label}}</h3><audio controls src="${{r.file}}"></audio></div>`).join('');const opts=t.options.map(o=>`<div><h3>Candidat ${{o.letter}}</h3><audio controls src="${{o.file}}"></audio></div>`).join('');document.getElementById('app').innerHTML=`<div class="card"><p><strong>${{t.label}}</strong> — <em>${{t.text}}</em></p><h2>Références</h2><div class="grid">${{refs}}</div><h2>Candidats</h2><div class="grid">${{opts}}</div><fieldset><legend>À quelle référence correspond A ?</legend><label><input type=radio name=identity value="Référence 1"> Référence 1</label><label><input type=radio name=identity value="Référence 2"> Référence 2</label><label><input type=radio name=identity value=uncertain> Impossible à distinguer</label></fieldset><fieldset><legend>L'intention est-elle immédiatement perceptible ?</legend><label>A : <input type=radio name=actingA value=yes> Oui <input type=radio name=actingA value=no> Non</label><label>B : <input type=radio name=actingB value=yes> Oui <input type=radio name=actingB value=no> Non</label></fieldset><fieldset><legend>Français</legend><label><input type=radio name=french value=both-good> Les deux corrects/naturels</label><label><input type=radio name=french value=bad-A> Défaut éliminatoire A</label><label><input type=radio name=french value=bad-B> Défaut éliminatoire B</label><label><input type=radio name=french value=bad-both> Défaut éliminatoire sur les deux</label></fieldset></div>`;const old=state.responses[t.id];if(old){{for(const [n,v] of Object.entries({{identity:old.identity,actingA:old.acting_A,actingB:old.acting_B,french:old.french}})){{const e=document.querySelector(`input[name="${{n}}"][value="${{v}}"]`);if(e)e.checked=true}}}}}}function commit(){{const t=trials[state.index],r={{identity:chosen('identity'),acting_A:chosen('actingA'),acting_B:chosen('actingB'),french:chosen('french')}};if(Object.values(r).some(v=>!v))return false;state.responses[t.id]=r;save();return true}}document.getElementById('next').onclick=()=>{{if(!commit())return alert('Répondez aux quatre questions.');if(state.index<trials.length-1)state.index++;render()}};document.getElementById('back').onclick=()=>{{commit();if(state.index>0)state.index--;render()}};document.getElementById('export').onclick=()=>{{commit();if(Object.keys(state.responses).length!==trials.length)return alert('Complétez les 3 écrans.');const blob=new Blob([JSON.stringify({{schema:KEY,exported_at:new Date().toISOString(),responses:state.responses,mapping:{{trials:mapping}}}},null,2)],{{type:'application/json'}});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='qwen3-style-transplant-killer-results.json';a.click();URL.revokeObjectURL(a.href)}};render();</script></body></html>'''
    (output_dir / "index.html").write_text(html, encoding="utf-8")
