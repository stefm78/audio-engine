import json
from collections import Counter, defaultdict
from pathlib import Path

from .voice_lab import AGE_STAGES


HUMAN_EVALUATION_SCHEMA = "voice-casting-human-evaluation-v1"


def _load_payload(value):
    if isinstance(value, dict):
        return value
    path = Path(value)
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(payload):
    if payload.get("schema") != HUMAN_EVALUATION_SCHEMA:
        raise ValueError(f"unsupported human evaluation schema: {payload.get('schema')!r}")
    if not isinstance(payload.get("responses"), dict):
        raise ValueError("human evaluation payload is missing responses")
    if not isinstance(payload.get("mapping"), dict):
        raise ValueError("human evaluation payload is missing mapping")


def summarize_human_evaluation(value):
    """Summarize one exported listening session without promoting voices automatically.

    Pairwise points are descriptive within the tested comparison graph only:
    win=1, tie=0.5, loss/reject=0. A reject-both decision is tracked separately and
    is not silently turned into an ordinary loss.
    """
    payload = _load_payload(value)
    _validate(payload)
    responses = payload["responses"]
    mapping = payload["mapping"]

    gate_mapping = {item["id"]: item for item in mapping.get("gate", [])}
    gate_stats = defaultdict(lambda: {
        "wins": 0,
        "ties": 0,
        "losses": 0,
        "rejects": 0,
        "comparisons": 0,
        "points": 0.0,
    })
    gate_answer_count = 0
    for comparison_id, decision in responses.get("gate", {}).items():
        item = gate_mapping.get(comparison_id)
        if not item:
            continue
        left = item["left_voice"]
        right = item["right_voice"]
        gate_stats[left]["comparisons"] += 1
        gate_stats[right]["comparisons"] += 1
        gate_answer_count += 1
        if decision == "A":
            gate_stats[left]["wins"] += 1
            gate_stats[left]["points"] += 1.0
            gate_stats[right]["losses"] += 1
        elif decision == "B":
            gate_stats[right]["wins"] += 1
            gate_stats[right]["points"] += 1.0
            gate_stats[left]["losses"] += 1
        elif decision == "tie":
            gate_stats[left]["ties"] += 1
            gate_stats[right]["ties"] += 1
            gate_stats[left]["points"] += 0.5
            gate_stats[right]["points"] += 0.5
        elif decision == "reject-both":
            gate_stats[left]["rejects"] += 1
            gate_stats[right]["rejects"] += 1
        else:
            raise ValueError(f"unsupported gate decision {decision!r} for {comparison_id}")

    gate_voices = []
    for voice, stats in gate_stats.items():
        comparisons = stats["comparisons"]
        gate_voices.append({
            "voice": voice,
            **stats,
            "pairwise_score": round(stats["points"] / comparisons, 6) if comparisons else None,
        })
    gate_voices.sort(key=lambda item: (
        -(item["pairwise_score"] if item["pairwise_score"] is not None else -1),
        -item["wins"],
        item["voice"],
    ))

    abx_mapping = {item["id"]: item for item in mapping.get("abx", [])}
    by_emotion = defaultdict(lambda: {"correct": 0, "total": 0})
    by_voice = defaultdict(lambda: {"correct": 0, "total": 0})
    abx_correct = 0
    abx_total = 0
    for trial_id, decision in responses.get("identity_abx", {}).items():
        item = abx_mapping.get(trial_id)
        if not item:
            continue
        correct = decision == item.get("correct")
        emotion = item.get("emotion") or "unknown"
        voice = item.get("reference_voice")
        abx_total += 1
        abx_correct += int(correct)
        by_emotion[emotion]["total"] += 1
        by_emotion[emotion]["correct"] += int(correct)
        if voice:
            by_voice[voice]["total"] += 1
            by_voice[voice]["correct"] += int(correct)

    def accuracy_rows(source, key_name):
        rows = []
        for key, stats in source.items():
            rows.append({
                key_name: key,
                **stats,
                "accuracy": round(stats["correct"] / stats["total"], 6) if stats["total"] else None,
            })
        return sorted(rows, key=lambda item: item[key_name])

    age_mapping = {item["id"]: item for item in mapping.get("age", [])}
    age_distribution = Counter()
    age_voices = []
    favorite_voices = []
    for item_id, answer in responses.get("age", {}).items():
        item = age_mapping.get(item_id)
        if not item:
            continue
        stage = answer.get("stage")
        if stage and stage not in AGE_STAGES and stage != "uncertain":
            raise ValueError(f"unsupported age stage {stage!r} for {item_id}")
        voice = item.get("voice_id")
        favorite = bool(answer.get("favorite", False))
        if stage:
            age_distribution[stage] += 1
        row = {"voice": voice, "stage": stage, "favorite": favorite}
        age_voices.append(row)
        if favorite and voice:
            favorite_voices.append(voice)
    age_voices.sort(key=lambda item: item.get("voice") or "")

    observed_stages = set(age_distribution)
    missing_stages = [stage for stage in AGE_STAGES if stage not in observed_stages]

    return {
        "version": 1,
        "source_schema": payload.get("schema"),
        "exported_at": payload.get("exported_at"),
        "mode": payload.get("mode"),
        "gate": {
            "dimension": "french_pronunciation",
            "answer_count": gate_answer_count,
            "voices": gate_voices,
            "interpretation": (
                "pairwise_score is relative to the tested comparison graph; it is not an absolute French-quality score"
            ),
        },
        "identity_abx": {
            "correct": abx_correct,
            "total": abx_total,
            "accuracy": round(abx_correct / abx_total, 6) if abx_total else None,
            "by_emotion": accuracy_rows(by_emotion, "emotion"),
            "by_voice": accuracy_rows(by_voice, "voice"),
            "interpretation": (
                "ABX accuracy measures recognizability against the tested distractor and emotion only; it is not all-pairs identity proof"
            ),
        },
        "age": {
            "distribution": dict(sorted(age_distribution.items())),
            "voices": age_voices,
            "favorite_voices": sorted(favorite_voices),
            "missing_stages": missing_stages,
            "interpretation": (
                "age labels are perceived age for the tested clip, not biological age and not lineage validation"
            ),
        },
        "promotion": {
            "automatic": False,
            "note": "Human listening evidence informs casting; no voice is promoted to the production catalog by this summary alone.",
        },
    }
