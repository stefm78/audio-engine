import json
import re
import shutil
from pathlib import Path

from .providers.edge import EdgeProvider
from .voices import load_voice_config


AGE_STAGES = ("child", "teen", "young_adult", "adult", "mature", "older", "very_old")
PROVIDER_CANDIDATE_SETS = ("fr", "fr-plus-multilingual")

PAIRWISE_DIMENSIONS = {
    "french_pronunciation": "Quelle voix prononce le français de la façon la plus correcte et naturelle ?",
    "naturalness": "Quelle voix semble la plus naturelle et la moins synthétique ?",
    "narrative_fit": "Quelle voix donne le plus envie d'écouter la suite de l'histoire ?",
    "acting_fit": "Quelle voix sert le mieux l'intention dramatique de cette réplique ?",
    "long_form_fatigue": "Quelle voix paraît la moins fatigante pour une écoute prolongée ?",
    "lineage_continuity": "Laquelle semble la plus crédible comme autre âge du même personnage de référence ?",
}

PROBES = (
    {
        "id": "identity-neutral",
        "stage": "fingerprint",
        "kind": "identity",
        "intention": "neutral",
        "text": "À l'aube, personne dans la ville ne savait encore ce qui allait se produire.",
    },
    {
        "id": "identity-confidence",
        "stage": "fingerprint",
        "kind": "identity",
        "intention": "confidence",
        "text": "Approchez. Ce que je vais vous dire ne doit sortir d'ici sous aucun prétexte.",
    },
    {
        "id": "identity-authority",
        "stage": "fingerprint",
        "kind": "identity",
        "intention": "authority",
        "text": "Vous ferez exactement ce que je vous demande, et personne ne quittera sa position.",
    },
    {
        "id": "emotion-joy",
        "stage": "expressive",
        "kind": "performance",
        "intention": "joy",
        "text": "Vous êtes là ! Je n'osais plus croire que nous nous reverrions un jour.",
    },
    {
        "id": "emotion-tenderness",
        "stage": "expressive",
        "kind": "performance",
        "intention": "tenderness",
        "text": "Ne vous inquiétez pas. Je resterai près de vous jusqu'au matin.",
    },
    {
        "id": "emotion-sadness-contained",
        "stage": "expressive",
        "kind": "performance",
        "intention": "sadness-contained",
        "text": "Il était mon frère. Je n'en parlerai pas davantage.",
    },
    {
        "id": "emotion-fear-contained",
        "stage": "expressive",
        "kind": "performance",
        "intention": "fear-contained",
        "text": "Restez derrière moi. Quoi qu'il arrive, surtout, ne faites aucun bruit.",
    },
    {
        "id": "emotion-panic",
        "stage": "expressive",
        "kind": "performance",
        "intention": "panic",
        "text": "Courez ! Ils arrivent ! Fermez la porte, vite !",
    },
    {
        "id": "emotion-anger-contained",
        "stage": "expressive",
        "kind": "performance",
        "intention": "anger-contained",
        "text": "Je vous avais donné ma parole. Vous venez de me donner une raison de la reprendre.",
    },
    {
        "id": "emotion-threat-polite",
        "stage": "expressive",
        "kind": "performance",
        "intention": "threat-polite",
        "text": "Je vous conseille très sincèrement de reconsidérer votre réponse.",
    },
    {
        "id": "emotion-irony",
        "stage": "expressive",
        "kind": "performance",
        "intention": "irony",
        "text": "Évidemment. Votre plan était parfait. C'est sans doute pour cela que tout brûle.",
    },
    {
        "id": "emotion-mystery",
        "stage": "expressive",
        "kind": "performance",
        "intention": "mystery",
        "text": "Depuis trois nuits, la même lumière apparaît derrière cette fenêtre condamnée.",
    },
    {
        "id": "emotion-fatigue-determined",
        "stage": "expressive",
        "kind": "performance",
        "intention": "fatigue-determined",
        "text": "Je n'ai presque plus de forces. Mais nous irons jusqu'au bout.",
    },
    {
        "id": "emotion-wonder",
        "stage": "expressive",
        "kind": "performance",
        "intention": "wonder",
        "text": "Regardez... On distingue toute la vallée, jusqu'aux montagnes derrière la brume.",
    },
    {
        "id": "age-anchor",
        "stage": "age",
        "kind": "age-lineage",
        "intention": "neutral",
        "text": "Je me souviens très bien de cette maison. J'y revenais chaque été, toujours par le même chemin.",
    },
    {
        "id": "long-form",
        "stage": "long-form",
        "kind": "endurance",
        "intention": "narration",
        "text": (
            "La route suivait encore la rivière lorsque les premières maisons apparurent. "
            "À cette heure, les volets s'ouvraient un à un et le marché commençait à gagner la place. "
            "Rien, à première vue, ne distinguait cette matinée des précédentes. Pourtant, avant midi, "
            "un événement allait changer durablement la mémoire de ceux qui vivaient ici."
        ),
    },
)


def probe_catalog():
    return {
        "version": 2,
        "age_stages": list(AGE_STAGES),
        "provider_candidate_sets": list(PROVIDER_CANDIDATE_SETS),
        "pairwise_dimensions": PAIRWISE_DIMENSIONS,
        "principles": {
            "identity_first": True,
            "emotion_never_implies_recast": True,
            "age_is_a_lineage_problem": True,
            "runtime_ml_required": False,
            "provider_controls_are_measured_not_assumed": True,
            "multilingual_french_is_benchmarked_not_assumed": True,
            "artistic_scores_require_listening_evidence": True,
        },
        "probes": list(PROBES),
    }


def _slug(value):
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(value)).strip("-")
    return value or "voice"


def _preset_candidates(voice_config):
    result = []
    for preset in voice_config.get("presets", []):
        result.append({
            "candidate_id": preset["id"],
            "source": "validated-preset",
            "voice": preset["voice"],
            "rate": preset.get("rate", "+0%"),
            "pitch": preset.get("pitch", "+0Hz"),
            "volume": preset.get("volume", "+0%"),
            "traits": preset.get("traits", {}),
            "tags": preset.get("tags", []),
        })
    return result


def _provider_candidates(provider, candidate_set="fr"):
    if candidate_set == "fr":
        voices = provider.list_voices(locale_prefix="fr-")
    elif candidate_set == "fr-plus-multilingual":
        voices = provider.list_voices(locale_prefix=None)
        voices = [
            item
            for item in voices
            if str(item.get("locale") or "").startswith("fr-")
            or "multilingual" in str(item.get("voice") or "").lower()
        ]
    else:
        raise ValueError(
            "candidate_set must be one of: " + ", ".join(PROVIDER_CANDIDATE_SETS)
        )

    result = []
    seen = set()
    for item in voices:
        voice = item.get("voice")
        if not voice or voice in seen:
            continue
        seen.add(voice)
        result.append({
            "candidate_id": voice,
            "source": "provider-voice",
            "voice": voice,
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
            "provider_metadata": item,
        })
    return result


def build_campaign(
    voice_config=None,
    provider=None,
    scope="presets",
    stage="fingerprint",
    limit=None,
    candidate_set="fr",
):
    if stage not in {"fingerprint", "expressive", "age", "long-form", "all"}:
        raise ValueError("stage must be fingerprint, expressive, age, long-form, or all")
    provider = provider or EdgeProvider()
    if voice_config is None:
        voice_config, _ = load_voice_config()

    if scope == "presets":
        candidates = _preset_candidates(voice_config)
    elif scope == "provider":
        candidates = _provider_candidates(provider, candidate_set=candidate_set)
    else:
        raise ValueError("scope must be presets or provider")

    probes = list(PROBES) if stage == "all" else [probe for probe in PROBES if probe["stage"] == stage]
    jobs = []
    for candidate in candidates:
        for probe in probes:
            job = {
                "id": f"{_slug(candidate['candidate_id'])}--{probe['id']}",
                "candidate": candidate,
                "probe": probe,
            }
            jobs.append(job)
            if limit is not None and len(jobs) >= limit:
                break
        if limit is not None and len(jobs) >= limit:
            break

    return {
        "version": 2,
        "scope": scope,
        "stage": stage,
        "candidate_set": candidate_set if scope == "provider" else None,
        "provider": provider.name,
        "provider_processing": provider.processing,
        "provider_expressive_controls": list(getattr(provider, "expressive_controls", ())),
        "candidate_count": len(candidates),
        "probe_count": len(probes),
        "job_count": len(jobs),
        "jobs": jobs,
        "evaluation": {
            "required_dimensions": [
                "french_pronunciation",
                "naturalness",
                "identity_stability",
                "acting_fit",
                "age_plausibility",
                "lineage_continuity",
                "long_form_fatigue",
            ],
            "preferred_comparison": "pairwise-or-abx",
            "note": "Scores describe observed campaign evidence; do not infer untested emotions or age continuity.",
        },
    }


def render_campaign(
    output_dir,
    voice_config=None,
    provider=None,
    scope="presets",
    stage="fingerprint",
    limit=None,
    candidate_set="fr",
):
    provider = provider or EdgeProvider()
    plan = build_campaign(
        voice_config=voice_config,
        provider=provider,
        scope=scope,
        stage=stage,
        limit=limit,
        candidate_set=candidate_set,
    )
    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    rendered = []
    failures = []
    for job in plan["jobs"]:
        candidate = job["candidate"]
        segment = {
            "text": job["probe"]["text"],
            "voice": candidate["voice"],
            "rate": candidate.get("rate", "+0%"),
            "pitch": candidate.get("pitch", "+0Hz"),
            "volume": candidate.get("volume", "+0%"),
        }
        filename = f"{_slug(job['id'])}.mp3"
        path = clips_dir / filename
        try:
            provider.synthesize(segment, path)
            rendered.append({"job_id": job["id"], "file": f"clips/{filename}"})
        except Exception as exc:
            failures.append({"job_id": job["id"], "error": str(exc)})

    result = {
        **plan,
        "status": "success" if not failures else ("partial" if rendered else "failed"),
        "rendered_count": len(rendered),
        "failure_count": len(failures),
        "rendered": rendered,
        "failures": failures,
    }
    (output_dir / "campaign.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def _candidate_map(campaign):
    candidates = {}
    for job in campaign.get("jobs", []):
        candidate = job.get("candidate") or {}
        candidate_id = candidate.get("candidate_id")
        if candidate_id:
            candidates[candidate_id] = candidate
    return candidates


def _rendered_map(campaign):
    return {
        item.get("job_id"): item.get("file")
        for item in campaign.get("rendered", [])
        if item.get("job_id") and item.get("file")
    }


def _round_robin_pairs(items, rounds):
    items = list(items)
    if len(items) < 2 or rounds <= 0:
        return []
    if len(items) % 2:
        items.append(None)
    count = len(items)
    maximum_rounds = count - 1
    rounds = min(rounds, maximum_rounds)
    rotation = list(items)
    result = []
    for round_index in range(rounds):
        pairs = []
        for index in range(count // 2):
            left = rotation[index]
            right = rotation[count - 1 - index]
            if left is None or right is None:
                continue
            if (round_index + index) % 2:
                left, right = right, left
            pairs.append((left, right, round_index + 1))
        result.extend(pairs)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return result


def build_pairwise_plan(
    campaign,
    probe_id="identity-neutral",
    dimension="french_pronunciation",
    rounds=4,
    same_gender=True,
):
    if dimension not in PAIRWISE_DIMENSIONS:
        raise ValueError(
            "dimension must be one of: " + ", ".join(sorted(PAIRWISE_DIMENSIONS))
        )
    candidates = _candidate_map(campaign)
    rendered = _rendered_map(campaign)
    available = []
    for candidate_id, candidate in sorted(candidates.items()):
        job_id = f"{_slug(candidate_id)}--{probe_id}"
        if job_id in rendered:
            available.append(candidate_id)
    if len(available) < 2:
        raise ValueError(f"campaign has fewer than two rendered candidates for probe {probe_id}")

    groups = {}
    for candidate_id in available:
        candidate = candidates[candidate_id]
        gender = (candidate.get("provider_metadata") or {}).get("gender")
        if not gender:
            gender = (candidate.get("traits") or {}).get("gender")
        group = gender if same_gender and gender else "all"
        groups.setdefault(group, []).append(candidate_id)

    comparisons = []
    for group, candidate_ids in sorted(groups.items()):
        for left_id, right_id, round_index in _round_robin_pairs(candidate_ids, rounds):
            left_job = f"{_slug(left_id)}--{probe_id}"
            right_job = f"{_slug(right_id)}--{probe_id}"
            comparisons.append({
                "id": f"{_slug(dimension)}--{_slug(probe_id)}--{len(comparisons)+1:03d}",
                "dimension": dimension,
                "question": PAIRWISE_DIMENSIONS[dimension],
                "probe_id": probe_id,
                "group": group,
                "round": round_index,
                "left": {
                    "candidate_id": left_id,
                    "voice": candidates[left_id].get("voice"),
                    "file": rendered[left_job],
                },
                "right": {
                    "candidate_id": right_id,
                    "voice": candidates[right_id].get("voice"),
                    "file": rendered[right_job],
                },
            })

    return {
        "version": 1,
        "kind": "pairwise",
        "dimension": dimension,
        "question": PAIRWISE_DIMENSIONS[dimension],
        "probe_id": probe_id,
        "same_gender": bool(same_gender),
        "rounds_requested": rounds,
        "candidate_count": len(available),
        "comparison_count": len(comparisons),
        "comparisons": comparisons,
        "result_contract": {
            "decision_values": ["left", "right", "tie", "reject-both"],
            "note": "Listening evidence is required. The plan contains no pre-decided artistic winner.",
        },
    }


def _pairwise_html(plan):
    data = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang=\"fr\">
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Voice Casting Pairwise</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.45}}
.card{{border:1px solid #ccc;border-radius:12px;padding:1rem;margin:1rem 0}}
.row{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
button{{padding:.7rem 1rem;margin:.25rem;cursor:pointer}}
audio{{width:100%}}
.small{{opacity:.7;font-size:.9rem}}
@media(max-width:640px){{.row{{grid-template-columns:1fr}}}}
</style>
<h1>Voice Casting — comparaison pairwise</h1>
<p id=\"summary\"></p>
<div id=\"app\"></div>
<button id=\"export\">Exporter les décisions JSON</button>
<script>
const plan={data};
const decisions={{}};
let index=0;
const app=document.getElementById('app');
const summary=document.getElementById('summary');
function render(){{
 const c=plan.comparisons[index];
 summary.textContent=`${{plan.dimension}} — ${{index+1}}/${{plan.comparisons.length}}`;
 if(!c){{app.innerHTML='<p>Évaluation terminée. Exportez les décisions.</p>';return;}}
 app.innerHTML=`<div class=\"card\"><h2>${{c.question}}</h2><p class=\"small\">Probe: ${{c.probe_id}} · groupe: ${{c.group}}</p><div class=\"row\"><div><strong>A</strong><audio controls preload=\"none\" src=\"${{c.left.file}}\"></audio></div><div><strong>B</strong><audio controls preload=\"none\" src=\"${{c.right.file}}\"></audio></div></div><p><button data-v=\"left\">A gagne</button><button data-v=\"right\">B gagne</button><button data-v=\"tie\">Égalité</button><button data-v=\"reject-both\">Rejeter les deux</button></p></div>`;
 app.querySelectorAll('button[data-v]').forEach(b=>b.onclick=()=>{{decisions[c.id]=b.dataset.v;index++;render();}});
}}
document.getElementById('export').onclick=()=>{{
 const result={{version:1,kind:'pairwise-results',dimension:plan.dimension,probe_id:plan.probe_id,decisions}};
 const blob=new Blob([JSON.stringify(result,null,2)],{{type:'application/json'}});
 const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='pairwise-results.json';a.click();URL.revokeObjectURL(a.href);
}};
render();
</script>
</html>"""


def write_pairwise_bundle(
    campaign_path,
    output_dir,
    probe_id="identity-neutral",
    dimension="french_pronunciation",
    rounds=4,
    same_gender=True,
):
    campaign_path = Path(campaign_path)
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    plan = build_pairwise_plan(
        campaign,
        probe_id=probe_id,
        dimension=dimension,
        rounds=rounds,
        same_gender=same_gender,
    )
    output_dir = Path(output_dir)
    clips_dir = output_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    source_root = campaign_path.parent

    copied = {}
    for comparison in plan["comparisons"]:
        for side in ("left", "right"):
            relative = comparison[side]["file"]
            source = source_root / relative
            if not source.exists():
                raise FileNotFoundError(f"missing campaign clip: {source}")
            filename = Path(relative).name
            destination = clips_dir / filename
            if filename not in copied:
                shutil.copyfile(source, destination)
                copied[filename] = True
            comparison[side]["file"] = f"clips/{filename}"

    (output_dir / "pairwise-plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "index.html").write_text(_pairwise_html(plan), encoding="utf-8")
    return {
        "status": "success",
        "output": str(output_dir),
        "candidate_count": plan["candidate_count"],
        "comparison_count": plan["comparison_count"],
        "copied_clip_count": len(copied),
        "plan": "pairwise-plan.json",
        "player": "index.html",
    }
