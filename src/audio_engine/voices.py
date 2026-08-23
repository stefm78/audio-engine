import json
from pathlib import Path

AGE_ORDER = {"child": 0, "young_adult": 1, "adult": 2, "older": 3}
NUMERIC_TRAITS = {
    "energy": 1.5,
    "authority": 1.4,
    "warmth": 1.0,
    "darkness": 1.1,
    "proximity": 1.0,
}
GENDER_MISMATCH_PENALTY = 25.0
AGE_DISTANCE_PENALTY = 7.0
TAG_MATCH_BONUS = 2.0
QUALITY_VALIDATION = {
    "origin": "initial blind French voice benchmark and subsequent human casting tests",
    "principle": "language quality is checked before role fit",
    "criteria": [
        {
            "id": "french_pronunciation",
            "label": "Prononciation française",
            "priority": 1,
            "eliminatory": True,
        },
        {
            "id": "fluency_prosody",
            "label": "Fluidité et prosodie",
            "priority": 2,
            "eliminatory": False,
        },
        {
            "id": "naturalness",
            "label": "Naturel / absence d’effet synthétique",
            "priority": 3,
            "eliminatory": False,
        },
        {
            "id": "narrative_potential",
            "label": "Potentiel de narration / conteur",
            "priority": 4,
            "eliminatory": False,
        },
    ],
    "benchmark_note": "The original benchmark compared French voices on the same difficult French text before revealing voice identity. No fabricated historical aggregate score is published here.",
}


def default_voice_config():
    return Path(__file__).with_name("voices.json")


def load_voice_config(path=None):
    source = Path(path) if path else default_voice_config()
    data = json.loads(source.read_text(encoding="utf-8"))
    return data, source


def selection_rules():
    return {
        "score_direction": "lower-is-better",
        "gender_mismatch_penalty": GENDER_MISMATCH_PENALTY,
        "age_distance_penalty_per_class": AGE_DISTANCE_PENALTY,
        "numeric_trait_weights": NUMERIC_TRAITS,
        "tag_match_bonus_per_tag": TAG_MATCH_BONUS,
    }


def public_catalog(voice_config):
    return {
        "version": voice_config.get("version"),
        "description": voice_config.get("description"),
        "quality_validation": voice_config.get("quality_validation", QUALITY_VALIDATION),
        "selection_rules": selection_rules(),
        "presets": voice_config.get("presets", []),
    }


def casting_score(target, preset):
    traits = preset.get("traits", {})
    score = 0.0
    gender = target.get("gender", "any")
    if gender != "any" and traits.get("gender") != gender:
        score += GENDER_MISMATCH_PENALTY
    age = target.get("age", "any")
    if age != "any" and age in AGE_ORDER and traits.get("age") in AGE_ORDER:
        score += AGE_DISTANCE_PENALTY * abs(AGE_ORDER[age] - AGE_ORDER[traits["age"]])
    for key, weight in NUMERIC_TRAITS.items():
        if key in target and key in traits:
            delta = float(target[key]) - float(traits[key])
            score += weight * delta * delta
    score -= TAG_MATCH_BONUS * len(set(target.get("tags", [])) & set(preset.get("tags", [])))
    return score


def rank_presets(target, presets, limit=None):
    ranked = sorted(
        ((casting_score(target, preset), preset) for preset in presets),
        key=lambda item: (item[0], item[1]["id"]),
    )
    if not ranked:
        raise ValueError("Voice config contains no presets")
    if limit is not None:
        ranked = ranked[:limit]
    return ranked


def recommend_presets(target, voice_config, limit=3):
    if limit < 1:
        raise ValueError("limit must be >= 1")
    ranked = rank_presets(target, voice_config.get("presets", []), limit=limit)
    return {
        "target": target,
        "quality_validation": voice_config.get("quality_validation", QUALITY_VALIDATION),
        "selection_rules": selection_rules(),
        "recommendations": [
            {
                "rank": index,
                "score": round(score, 3),
                "preset": preset,
            }
            for index, (score, preset) in enumerate(ranked, start=1)
        ],
    }


def choose_preset(target, presets):
    ranked = rank_presets(target, presets, limit=3)
    return ranked[0][1], ranked


def resolve_segments(program, voice_config):
    presets = voice_config.get("presets", [])
    by_id = {preset["id"]: preset for preset in presets}
    character_cast = {}
    resolved = []
    for index, segment in enumerate(program["segments"], start=1):
        explicit_voice = segment.get("voice")
        preset_id = segment.get("preset")
        character_id = segment.get("character_id") or f"segment-{index}"
        alternatives = []

        if explicit_voice:
            voice = explicit_voice
            rate = segment.get("rate", "+0%")
            pitch = segment.get("pitch", "+0Hz")
            volume = segment.get("volume", "+0%")
            resolved_preset = None
        else:
            if preset_id:
                if preset_id not in by_id:
                    raise ValueError(f"Unknown voice preset: {preset_id}")
                preset = by_id[preset_id]
            elif character_id in character_cast:
                preset = character_cast[character_id]
            else:
                preset, ranked = choose_preset(segment.get("target", {}), presets)
                character_cast[character_id] = preset
                alternatives = [
                    {"preset": candidate["id"], "score": round(score, 3)}
                    for score, candidate in ranked
                ]
            voice = preset["voice"]
            rate = segment.get("rate", preset.get("rate", "+0%"))
            pitch = segment.get("pitch", preset.get("pitch", "+0Hz"))
            volume = segment.get("volume", preset.get("volume", "+0%"))
            resolved_preset = preset["id"]

        resolved.append({
            **segment,
            "sequence": index,
            "resolved_preset": resolved_preset,
            "voice": voice,
            "rate": rate,
            "pitch": pitch,
            "volume": volume,
            "casting_alternatives": alternatives,
        })
    return resolved
