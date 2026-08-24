import json
import re
from pathlib import Path

from .providers.edge import EdgeProvider
from .voices import load_voice_config


AGE_STAGES = ("child", "teen", "young_adult", "adult", "mature", "older", "very_old")

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
        "version": 1,
        "age_stages": list(AGE_STAGES),
        "principles": {
            "identity_first": True,
            "emotion_never_implies_recast": True,
            "age_is_a_lineage_problem": True,
            "runtime_ml_required": False,
            "provider_controls_are_measured_not_assumed": True,
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


def _provider_candidates(provider, locale_prefix="fr-"):
    return [
        {
            "candidate_id": item["voice"],
            "source": "provider-voice",
            "voice": item["voice"],
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
            "provider_metadata": item,
        }
        for item in provider.list_voices(locale_prefix=locale_prefix)
    ]


def build_campaign(voice_config=None, provider=None, scope="presets", stage="fingerprint", limit=None):
    if stage not in {"fingerprint", "expressive", "age", "long-form", "all"}:
        raise ValueError("stage must be fingerprint, expressive, age, long-form, or all")
    provider = provider or EdgeProvider()
    if voice_config is None:
        voice_config, _ = load_voice_config()

    if scope == "presets":
        candidates = _preset_candidates(voice_config)
    elif scope == "provider":
        candidates = _provider_candidates(provider)
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
        "version": 1,
        "scope": scope,
        "stage": stage,
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


def render_campaign(output_dir, voice_config=None, provider=None, scope="presets", stage="fingerprint", limit=None):
    provider = provider or EdgeProvider()
    plan = build_campaign(
        voice_config=voice_config,
        provider=provider,
        scope=scope,
        stage=stage,
        limit=limit,
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
