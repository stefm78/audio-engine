"""OpenVoice V2 tone-color killer.

Architecture under test:
1. reuse already-rendered expressive French Qwen VoiceDesign donor audio;
2. extract the frozen Claire/Lucie target tone-color embedding;
3. convert the same donor audio toward each target identity with OpenVoice V2.

This is a genuinely distinct architecture from Qwen prompt/style transplant: Qwen
owns the acting/prosody, while OpenVoice is asked only to replace tone color.
Research only; production is untouched.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import time
import wave
from pathlib import Path

from .providers.openvoice_v2_tone_lab import OpenVoiceV2ToneLabProvider

SCHEMA = "openvoice-v2-tone-killer-v1"
OPENVOICE_SOURCE_REVISION = "74a1d147b17a8c3092dd5430504bd83ef6c7eb23"
OPENVOICE_MODEL_ID = "myshell-ai/OpenVoiceV2"
OPENVOICE_MODEL_REVISION = "fd981100305a0e4291f93a9ad169c6d9f7bed54a"
OPENVOICE_CHECKPOINT_SHA256 = "9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e"
QWEN_SOURCE_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
QWEN_VOICE_DESIGN_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
QWEN_VOICE_DESIGN_MODEL_REVISION = "5ecdb67327fd37bb2e042aab12ff7391903235d3"
ANCHOR_RUN_ID = 32772435007
ANCHOR_ARTIFACT = "voice-casting-qwen3-xvector-identity-confirm"
DONOR_RUN_ID = 32811700540
DONOR_ARTIFACT = "qwen3-style-transplant-donors"
DONOR_ARTIFACT_DIGEST = "sha256:a9cb83397164ec017a6fd20994ad511bb7bac380d0d9c0bffc4acacd6111861a"
BLIND_SEED = 2026082504

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
        "text": "Attendez... J'ai entendu quelque chose, juste derrière nous.",
        "donor_file": "mystery.wav",
        "donor_sha256": "4d8da9df63297c1566c9d2b98557b0fc700ed0a2e2b6f6440123f2911c7d0ff0",
    },
    {
        "id": "wonder",
        "label": "émerveillement",
        "text": "C'est magnifique... Je n'avais jamais vu une lumière pareille.",
        "donor_file": "wonder.wav",
        "donor_sha256": "e4d5aeb8366e7c4f87dd1a185bf8d5d2aa02a168bf9d3a341a7188ddd0afdffe",
    },
    {
        "id": "sadness-contained",
        "label": "tristesse contenue",
        "text": "Je savais que ce jour viendrait... mais cela fait quand même mal.",
        "donor_file": "sadness-contained.wav",
        "donor_sha256": "4194a72b1705ec1820ea13cfdd3a0ed434e2bf63a445ba9f85ea1aeca33fdd25",
    },
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _wav_meta(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        return {
            "channels": wav.getnchannels(),
            "sample_rate": rate,
            "sample_width": wav.getsampwidth(),
            "duration_seconds": round(frames / rate, 3) if rate else 0.0,
        }


def experiment_spec() -> dict:
    return {
        "schema": SCHEMA,
        "architecture": "Qwen VoiceDesign expressive donor audio -> OpenVoice V2 tone-color conversion -> frozen target identity",
        "openvoice": {
            "source_revision": OPENVOICE_SOURCE_REVISION,
            "model_id": OPENVOICE_MODEL_ID,
            "model_revision": OPENVOICE_MODEL_REVISION,
            "checkpoint_sha256": OPENVOICE_CHECKPOINT_SHA256,
        },
        "qwen_donor_provenance": {
            "source_revision": QWEN_SOURCE_REVISION,
            "model_id": QWEN_VOICE_DESIGN_MODEL_ID,
            "model_revision": QWEN_VOICE_DESIGN_MODEL_REVISION,
            "run_id": DONOR_RUN_ID,
            "artifact": DONOR_ARTIFACT,
            "artifact_digest": DONOR_ARTIFACT_DIGEST,
        },
        "characters": {key: dict(value) for key, value in CHARACTERS.items()},
        "cases": [dict(case) for case in CASES],
        "decision": {
            "identity_pass": "3/3 pair mappings correct",
            "french_pass": "zero invalid-French veto",
            "acting_pass": ">=5/6 clear intentions and >=2/3 per character",
            "no_tuning": True,
            "production_promotion": False,
            "age_lineage": False,
        },
    }


def _validate_inputs(anchor_dir: Path, donor_dir: Path, character_id: str) -> tuple[Path, dict]:
    if character_id not in CHARACTERS:
        raise ValueError(f"unknown character: {character_id}")
    character = CHARACTERS[character_id]
    anchor = Path(anchor_dir) / character["anchor_file"]
    if not anchor.is_file():
        raise FileNotFoundError(anchor)
    if _sha256(anchor) != character["sha256"]:
        raise ValueError(f"qualified anchor mismatch for {character_id}")

    donor_dir = Path(donor_dir)
    for case in CASES:
        donor = donor_dir / case["donor_file"]
        if not donor.is_file():
            raise FileNotFoundError(donor)
        if _sha256(donor) != case["donor_sha256"]:
            raise ValueError(f"donor hash mismatch for {case['id']}")
    return anchor, character


def render_character(character_id, anchor_dir, donor_dir, output_dir, *, provider):
    anchor, character = _validate_inputs(Path(anchor_dir), Path(donor_dir), character_id)
    if getattr(provider, "identity_mode", None) != "openvoice-v2-tone-color":
        raise ValueError("provider must explicitly declare OpenVoice V2 tone-color identity mode")

    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(anchor, output_dir / "reference.wav")

    target_embedding = provider.extract_embedding(anchor)
    rendered = []
    for index, case in enumerate(CASES, 1):
        donor = Path(donor_dir) / case["donor_file"]
        out = clips_dir / f"{case['id']}.wav"
        started = time.monotonic()
        print(f"START {index}/{len(CASES)} · {character_id} · {case['id']}", flush=True)
        provider.convert(donor, target_embedding, out)
        elapsed = time.monotonic() - started
        meta = _wav_meta(out)
        if meta["channels"] != 1 or meta["duration_seconds"] <= 1.0:
            raise ValueError(f"invalid converted WAV for {character_id}/{case['id']}: {meta}")
        rendered.append(
            {
                "id": case["id"],
                "file": f"clips/{case['id']}.wav",
                "sha256": _sha256(out),
                "render_seconds": round(elapsed, 2),
                **meta,
            }
        )
        print(f"SUCCESS {index}/{len(CASES)} · {elapsed:.2f}s · audio={meta['duration_seconds']:.2f}s", flush=True)

    if _sha256(anchor) != character["sha256"]:
        raise ValueError("qualified anchor changed during conversion")
    result = {
        "schema": "openvoice-v2-tone-character-v1",
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
    for path in Path(root).rglob("character-result.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("character_id") == character_id:
            matches.append(path.parent)
    if len(matches) != 1:
        raise ValueError(f"expected one result root for {character_id}, got {len(matches)}")
    return matches[0]


def assemble_bundle(input_root, output_dir, *, seed=BLIND_SEED):
    input_root, output_dir = Path(input_root), Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    roots = {cid: _find_root(input_root, cid) for cid in CHARACTERS}
    refs, clips = {}, {}

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
            src = root / item["file"]
            if _sha256(src) != item["sha256"]:
                raise ValueError(f"converted clip hash mismatch for {cid}/{item['id']}")
            name = f"{cid}--{item['id']}.wav"
            shutil.copy2(src, clips_dir / name)
            clips[(cid, item["id"])] = f"clips/{name}"

    rnd = random.Random(seed)
    trials = []
    for case in CASES:
        options = [{"character_id": cid, "file": clips[(cid, case["id"])]} for cid in CHARACTERS]
        rnd.shuffle(options)
        trials.append(
            {
                "id": case["id"],
                "label": case["label"],
                "text": case["text"],
                "references": [
                    {"id": cid, "label": CHARACTERS[cid]["label"], "file": refs[cid]}
                    for cid in CHARACTERS
                ],
                "options": [{"letter": letter, **option} for letter, option in zip("AB", options)],
                "correct_reference_for_A": CHARACTERS[options[0]["character_id"]]["label"],
            }
        )

    manifest = {**experiment_spec(), "status": "success", "trial_count": len(trials), "trials": trials}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_player(output_dir, trials)
    return manifest


def _write_player(output_dir: Path, trials) -> None:
    public_trials = [
        {
            "id": trial["id"],
            "label": trial["label"],
            "text": trial["text"],
            "references": trial["references"],
            "options": [{"letter": option["letter"], "file": option["file"]} for option in trial["options"]],
        }
        for trial in trials
    ]
    public_json = json.dumps(public_trials, ensure_ascii=False).replace("</", "<\\/")
    mapping_json = json.dumps(trials, ensure_ascii=False).replace("</", "<\\/")
    html = """<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>OpenVoice V2 tone-color killer</title><style>body{font-family:system-ui,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem}.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}.card{border:1px solid #999;border-radius:12px;padding:1rem}audio{width:100%}label{display:block;margin:.55rem 0}button{padding:.7rem 1rem;margin:.4rem}@media(max-width:650px){.grid{grid-template-columns:1fr}}</style></head><body><h1>Test identité + émotion</h1><p>3 écrans. Évaluez uniquement ce que vous entendez.</p><p id=\"progress\"></p><div id=\"app\"></div><button id=\"back\">Précédent</button><button id=\"next\">Suivant</button><button id=\"export\">Exporter le JSON</button><script>
const trials=__PUBLIC__;const mapping=__MAPPING__;const KEY='openvoice-v2-tone-killer-v1';let state={index:0,responses:{}};try{state=JSON.parse(localStorage.getItem(KEY))||state}catch(e){}
function save(){try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){}}
function chosen(name){const x=document.querySelector('input[name="'+name+'"]:checked');return x?x.value:null}
function render(){const t=trials[state.index];document.getElementById('progress').textContent='Écran '+(state.index+1)+'/'+trials.length+' · '+t.label;const refs=t.references.map(r=>`<div><h3>${r.label}</h3><audio controls src="${r.file}"></audio></div>`).join('');const opts=t.options.map(o=>`<div><h3>Candidat ${o.letter}</h3><audio controls src="${o.file}"></audio></div>`).join('');document.getElementById('app').innerHTML=`<div class="card"><p><strong>${t.label}</strong> — <em>${t.text}</em></p><h2>Références</h2><div class="grid">${refs}</div><h2>Candidats</h2><div class="grid">${opts}</div><fieldset><legend>À quelle référence correspond A ?</legend><label><input type="radio" name="identity" value="Référence 1"> Référence 1</label><label><input type="radio" name="identity" value="Référence 2"> Référence 2</label><label><input type="radio" name="identity" value="uncertain"> Impossible à distinguer</label></fieldset><fieldset><legend>L'intention est-elle immédiatement perceptible ?</legend><label>A : <input type="radio" name="actingA" value="yes"> Oui <input type="radio" name="actingA" value="no"> Non</label><label>B : <input type="radio" name="actingB" value="yes"> Oui <input type="radio" name="actingB" value="no"> Non</label></fieldset><fieldset><legend>Français</legend><label><input type="radio" name="french" value="both-good"> Les deux corrects/naturels</label><label><input type="radio" name="french" value="bad-A"> Défaut éliminatoire A</label><label><input type="radio" name="french" value="bad-B"> Défaut éliminatoire B</label><label><input type="radio" name="french" value="bad-both"> Défaut éliminatoire sur les deux</label></fieldset></div>`;const old=state.responses[t.id];if(old){for(const [n,v] of Object.entries({identity:old.identity,actingA:old.acting_A,actingB:old.acting_B,french:old.french})){const e=document.querySelector(`input[name="${n}"][value="${v}"]`);if(e)e.checked=true}}}
function commit(){const t=trials[state.index];const r={identity:chosen('identity'),acting_A:chosen('actingA'),acting_B:chosen('actingB'),french:chosen('french')};if(Object.values(r).some(v=>!v))return false;state.responses[t.id]=r;save();return true}
document.getElementById('next').onclick=()=>{if(!commit())return alert('Répondez aux quatre questions.');if(state.index<trials.length-1)state.index++;render()};document.getElementById('back').onclick=()=>{commit();if(state.index>0)state.index--;save();render()};document.getElementById('export').onclick=()=>{if(!commit())return alert('Répondez aux quatre questions.');if(Object.keys(state.responses).length!==trials.length)return alert('Complétez les 3 écrans.');const payload={schema:'openvoice-v2-tone-killer-v1',exported_at:new Date().toISOString(),responses:state.responses,mapping:{trials:mapping}};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='openvoice-v2-tone-killer-results.json';a.click();URL.revokeObjectURL(a.href)};render();
</script></body></html>"""
    html = html.replace("__PUBLIC__", public_json).replace("__MAPPING__", mapping_json)
    (Path(output_dir) / "index.html").write_text(html, encoding="utf-8")
