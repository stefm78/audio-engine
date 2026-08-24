"""Broader emotional composition stage for qualified Qwen3 frozen characters.

This stage uses the real frozen-character contract and the exact Claire/Lucie
anchors qualified in issue #65. It expands the expressive envelope without
changing identity, provider, model or seeds by hand.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import time
from pathlib import Path

from .providers.qwen3_xvector_lab import Qwen3XVectorLabProvider
from .voice_character_lab import freeze_character_identity, render_character_lines

UPSTREAM_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
MODEL_REVISION = "74a6279626edc2d5a787d5b6467668eba0b86ef6"
SOURCE_RUN_ID = 32772435007
SOURCE_ARTIFACT = "voice-casting-qwen3-xvector-identity-confirm"
BLIND_SEED = 2026082409

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
        "id": "tenderness",
        "label": "tendresse rassurante",
        "text": "Ne vous inquiétez pas. Je reste avec vous. On attendra ici jusqu'au matin.",
    },
    {
        "id": "mystery",
        "label": "mystère inquiet",
        "text": "Écoutez... Il y a quelqu'un derrière cette porte. Pourtant, cette pièce est vide depuis des années.",
    },
    {
        "id": "wonder",
        "label": "émerveillement",
        "text": "Regardez... La brume se lève. On voit toute la vallée, jusqu'aux montagnes.",
    },
    {
        "id": "sadness-contained",
        "label": "tristesse contenue",
        "text": "Il est parti avant l'aube. Je savais que ce moment viendrait, mais pas si tôt.",
    },
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def experiment_spec():
    return {
        "schema": "qwen3-character-composition-v1",
        "provider": "qwen3-xvector-lab",
        "identity_mode": "x_vector_only",
        "upstream_revision": UPSTREAM_REVISION,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "license": "Apache-2.0"},
        "source": {"run_id": SOURCE_RUN_ID, "artifact": SOURCE_ARTIFACT},
        "characters": {key: dict(value) for key, value in CHARACTERS.items()},
        "cases": [dict(case) for case in CASES],
        "decision": {
            "identity_pass": "4/4 pair mappings correct (equivalent to both characters correct on all four new intentions).",
            "french_pass": "No invalid-French veto on any generated candidate.",
            "acting_pass": "At least 7/8 generated samples clearly convey the intended emotion, with at least 3/4 per character.",
            "next_if_pass": "Proceed to a separate long-form endurance stage; production promotion remains explicit and separate.",
            "next_if_fail": "Do not tune broadly; keep qualification limited to the already demonstrated expressive envelope.",
            "automatic_production_promotion": False,
            "age_lineage": False,
        },
    }


class _ProgressProvider:
    identity_mode = "x_vector_only"

    def __init__(self, provider, *, character_id: str, total: int):
        self._provider = provider
        self.character_id = character_id
        self.total = total
        self.index = 0
        self.started = time.monotonic()
        self.durations = []

    def build_identity_prompt(self, anchor):
        return self._provider.build_identity_prompt(anchor)

    def synthesize(self, segment, path, *, voice_clone_prompt):
        self.index += 1
        clip_started = time.monotonic()
        print(f"::group::Qwen3 composition {self.character_id} {self.index}/{self.total}", flush=True)
        print(
            f"START {self.index}/{self.total} · {self.character_id} · elapsed={time.monotonic()-self.started:.1f}s",
            flush=True,
        )
        try:
            self._provider.synthesize(segment, path, voice_clone_prompt=voice_clone_prompt)
        except Exception:
            print(
                f"FAIL {self.index}/{self.total} · clip={time.monotonic()-clip_started:.1f}s",
                flush=True,
            )
            raise
        else:
            duration = time.monotonic() - clip_started
            self.durations.append(duration)
            remaining = self.total - self.index
            eta = (sum(self.durations) / len(self.durations)) * remaining if self.durations else 0.0
            print(
                f"SUCCESS {self.index}/{self.total} · clip={duration:.1f}s · "
                f"total={time.monotonic()-self.started:.1f}s · ETA≈{eta:.1f}s",
                flush=True,
            )
        finally:
            print("::endgroup::", flush=True)


def render_character(character_id, anchor_dir, output_dir, *, provider=None, model_dir=None):
    if character_id not in CHARACTERS:
        raise ValueError(f"unknown composition character: {character_id}")
    character = CHARACTERS[character_id]
    anchor_dir = Path(anchor_dir)
    anchor = anchor_dir / character["anchor_file"]
    if not anchor.is_file():
        raise FileNotFoundError(anchor)
    actual = _sha256(anchor)
    if actual != character["sha256"]:
        raise ValueError(
            f"qualified anchor mismatch for {character_id}: expected {character['sha256']}, got {actual}"
        )

    output_dir = Path(output_dir)
    pack_dir = output_dir / "character-pack"
    render_dir = output_dir / "render"
    freeze_character_identity(
        character_id,
        anchor,
        pack_dir,
        source={
            "qualification_issue": 65,
            "qualification_run": SOURCE_RUN_ID,
            "qualification_artifact": SOURCE_ARTIFACT,
            "qualified_anchor_sha256": character["sha256"],
        },
    )

    if provider is None:
        if model_dir is None:
            raise ValueError("model_dir is required when provider is not injected")
        provider = Qwen3XVectorLabProvider(model_dir=model_dir, device="cpu")
    progress_provider = _ProgressProvider(provider, character_id=character_id, total=len(CASES))
    result = render_character_lines(
        pack_dir / "character.json",
        [{"id": case["id"], "text": case["text"]} for case in CASES],
        render_dir,
        provider=progress_provider,
    )
    summary = {
        "schema": "qwen3-character-composition-character-v1",
        "character_id": character_id,
        "qualified_anchor_sha256": character["sha256"],
        "status": result["status"],
        "rendered_count": result["rendered_count"],
        "failure_count": result["failure_count"],
    }
    (output_dir / "composition-character.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def _find_character_root(input_root: Path, character_id: str) -> Path:
    candidates = []
    for manifest in input_root.rglob("composition-character.json"):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("character_id") == character_id:
            candidates.append(manifest.parent)
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one artifact root for {character_id}, got {len(candidates)}")
    return candidates[0]


def assemble_bundle(input_root, output_dir, *, seed=BLIND_SEED):
    input_root = Path(input_root)
    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    roots = {character_id: _find_character_root(input_root, character_id) for character_id in CHARACTERS}

    references = {}
    rendered = {}
    for character_id, character in CHARACTERS.items():
        root = roots[character_id]
        summary = json.loads((root / "composition-character.json").read_text(encoding="utf-8"))
        if summary.get("status") != "success" or summary.get("rendered_count") != len(CASES):
            raise ValueError(f"incomplete composition render for {character_id}: {summary}")
        anchor = root / "character-pack" / "anchor.wav"
        if _sha256(anchor) != character["sha256"]:
            raise ValueError(f"anchor changed before bundle assembly for {character_id}")
        reference_name = f"reference-{character_id}.wav"
        shutil.copy2(anchor, output_dir / reference_name)
        references[character_id] = reference_name

        manifest = json.loads((root / "render" / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("character_id") != character_id or manifest.get("anchor_sha256") != character["sha256"]:
            raise ValueError(f"render manifest identity mismatch for {character_id}")
        for item in manifest.get("rendered", []):
            case_id = item["id"]
            source = root / "render" / item["file"]
            destination_name = f"{character_id}--{case_id}.wav"
            shutil.copy2(source, clips_dir / destination_name)
            rendered[(character_id, case_id)] = f"clips/{destination_name}"

    rnd = random.Random(seed)
    trials = []
    for case in CASES:
        options = [
            {"character_id": character_id, "file": rendered[(character_id, case["id"])]}
            for character_id in CHARACTERS
        ]
        rnd.shuffle(options)
        trials.append(
            {
                "id": case["id"],
                "label": case["label"],
                "text": case["text"],
                "references": [
                    {"id": character_id, "label": CHARACTERS[character_id]["label"], "file": references[character_id]}
                    for character_id in CHARACTERS
                ],
                "options": [{"letter": letter, **option} for letter, option in zip("AB", options)],
                "correct_reference_for_A": CHARACTERS[options[0]["character_id"]]["label"],
            }
        )

    manifest = {
        **experiment_spec(),
        "status": "success",
        "trial_count": len(trials),
        "references": references,
        "trials": trials,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_player(output_dir, trials)
    return manifest


def _write_player(output_dir: Path, trials):
    public_trials = []
    for trial in trials:
        public_trials.append(
            {
                "id": trial["id"],
                "label": trial["label"],
                "text": trial["text"],
                "references": trial["references"],
                "options": [
                    {"letter": option["letter"], "file": option["file"]}
                    for option in trial["options"]
                ],
            }
        )
    payload = json.dumps({"trials": public_trials}, ensure_ascii=False).replace("</", "<\\/")
    hidden_mapping = json.dumps({"trials": trials}, ensure_ascii=False).replace("</", "<\\/")
    html = f"""<!doctype html><html lang='fr'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Qwen3 — composition personnage</title><style>body{{font-family:system-ui,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem}}.card{{border:1px solid #888;border-radius:12px;padding:1rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}audio{{width:100%}}label{{display:block;margin:.5rem 0}}button{{padding:.7rem 1rem;margin:.4rem}}fieldset{{margin:1rem 0}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}}}</style>
<h1>Composition émotionnelle — personnages figés</h1><p>4 écrans seulement. Pour chaque intention : identité, jeu et français.</p><p id='progress'></p><div id='app'></div><button id='back'>Précédent</button><button id='export'>Exporter le JSON</button>
<script>const data={payload};const mapping={hidden_mapping};const KEY='qwen3-character-composition-v1';let s={{index:0,responses:{{}}}};try{{s=JSON.parse(localStorage.getItem(KEY))||s}}catch(e){{}}const app=document.getElementById('app'),p=document.getElementById('progress');function save(){{try{{localStorage.setItem(KEY,JSON.stringify(s))}}catch(e){{}}}}function render(){{const t=data.trials[s.index];if(!t){{p.textContent=`Terminé · ${{Object.keys(s.responses).length}}/${{data.trials.length}}`;app.innerHTML='<p>Exportez le JSON.</p>';return}}p.textContent=`Écran ${{s.index+1}}/${{data.trials.length}} · ${{t.label}}`;const refs=t.references.map(r=>`<div><h3>${{r.label}}</h3><audio controls src='${{r.file}}'></audio></div>`).join('');const opts=t.options.map(o=>`<div><h3>Candidat ${{o.letter}}</h3><audio controls src='${{o.file}}'></audio></div>`).join('');app.innerHTML=`<div class='card'><p><strong>Intention :</strong> ${{t.label}}</p><p><em>${{t.text}}</em></p><h2>Références</h2><div class='grid'>${{refs}}</div><h2>Candidats</h2><div class='grid'>${{opts}}</div><fieldset><legend>Identité — à quelle référence correspond le candidat A ?</legend><label><input type=radio name=identity value='Référence 1'> Référence 1</label><label><input type=radio name=identity value='Référence 2'> Référence 2</label><label><input type=radio name=identity value=uncertain> Impossible à distinguer</label></fieldset><fieldset><legend>Le jeu rend-il l'intention immédiatement perceptible ?</legend><label>Candidat A : <input type=radio name=actingA value=yes> Oui <input type=radio name=actingA value=no> Non</label><label>Candidat B : <input type=radio name=actingB value=yes> Oui <input type=radio name=actingB value=no> Non</label></fieldset><fieldset><legend>Français</legend><label><input type=radio name=french value=both-good> Les deux sont naturels/corrects</label><label><input type=radio name=french value=bad-A> Défaut éliminatoire sur A</label><label><input type=radio name=french value=bad-B> Défaut éliminatoire sur B</label><label><input type=radio name=french value=bad-both> Défaut éliminatoire sur les deux</label></fieldset><button id=next>Valider</button></div>`;document.getElementById('next').onclick=()=>{{const i=document.querySelector('input[name=identity]:checked'),a=document.querySelector('input[name=actingA]:checked'),b=document.querySelector('input[name=actingB]:checked'),f=document.querySelector('input[name=french]:checked');if(!i||!a||!b||!f)return alert('Choisissez toutes les réponses.');s.responses[t.id]={{identity:i.value,acting_A:a.value,acting_B:b.value,french:f.value}};s.index++;save();render()}};window.scrollTo({{top:0,behavior:'smooth'}})}}document.getElementById('back').onclick=()=>{{if(s.index>0)s.index--;save();render()}};document.getElementById('export').onclick=()=>{{const out={{schema:'qwen3-character-composition-v1',exported_at:new Date().toISOString(),responses:s.responses,mapping:mapping}};const blob=new Blob([JSON.stringify(out,null,2)],{{type:'application/json'}}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='qwen3-character-composition-results.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}};render();</script></html>"""
    (output_dir / "index.html").write_text(html, encoding="utf-8")
