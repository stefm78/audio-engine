import json
from pathlib import Path


def _load_candidate(value):
    if isinstance(value, dict):
        return value
    path = Path(value)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Candidate must be a JSON object: {path}")
    return data


def _duration_score(sound_type, duration):
    duration = float(duration or 0)
    if sound_type == "ambience":
        if duration < 20:
            return -100
        if duration >= 120:
            return 20
        return round(8 + 12 * min(1.0, duration / 120.0), 2)
    if duration <= 0 or duration > 120:
        return -100
    if duration <= 30:
        return 20
    return max(5, round(20 - (duration - 30) / 6, 2))


def evaluate_candidate(candidate, *, sound_type, required_tags=None, preferred_tags=None):
    required = set(required_tags or [])
    preferred = set(preferred_tags or [])
    reasons = []
    gates = []

    if candidate.get("status") != "candidate":
        gates.append("status-not-candidate")
    if candidate.get("type", "ambience") != sound_type:
        gates.append("wrong-type")

    source = candidate.get("source", {})
    if source.get("provenance_complete") is not True:
        gates.append("provenance-incomplete")

    license_info = candidate.get("license", {})
    if license_info.get("verified") is not True:
        gates.append("license-not-machine-verified")
    if license_info.get("raw_redistribution") == "forbidden":
        gates.append("raw-use-forbidden")

    review = candidate.get("review", {})
    if review.get("technical_probe") != "passed":
        gates.append("technical-probe-failed")
    if review.get("automated_quality") not in {"passed", None}:
        gates.append("automated-quality-failed")

    tags = set(candidate.get("tags", []))
    missing = sorted(required - tags)
    if missing:
        gates.append("missing-required-tags:" + ",".join(missing))

    audio = candidate.get("audio", {})
    duration_component = _duration_score(sound_type, audio.get("duration_seconds"))
    if duration_component < 0:
        gates.append("duration-out-of-policy")
    if int(audio.get("sample_rate_hz") or 0) < 22050:
        gates.append("sample-rate-too-low")
    if audio.get("channels") not in {1, 2}:
        gates.append("unsupported-channel-layout")

    if gates:
        return {
            "id": candidate.get("id"),
            "eligible": False,
            "score": 0,
            "gates": gates,
            "reasons": reasons,
        }

    score = 40.0 + duration_component
    if audio.get("channels") == 2:
        score += 8
        reasons.append("stereo")
    if int(audio.get("sample_rate_hz") or 0) >= 44100:
        score += 5
        reasons.append("sample-rate>=44.1k")
    if source.get("identifier"):
        score += 2
    if license_info.get("raw_redistribution") == "allowed":
        score += 5
        reasons.append("redistributable")
    if license_info.get("id") in {"CC0-1.0", "PDM-1.0", "Public-Domain"}:
        score += 10
        reasons.append("frictionless-license")

    discovery = candidate.get("discovery", {}) if isinstance(candidate.get("discovery"), dict) else {}
    rank = discovery.get("rank")
    if isinstance(rank, int) and rank > 0:
        rank_bonus = max(0, 10 - 2 * (rank - 1))
        score += rank_bonus
        if rank_bonus:
            reasons.append(f"discovery-rank:{rank}")

    preferred_hits = sorted(preferred & tags)
    if preferred:
        if preferred_hits:
            # Preferred context is soft, but materially relevant. One contextual
            # match should beat a generic technically-perfect sound; more matches
            # remain a bounded bonus.
            score += min(12, 4 * len(preferred_hits))
            reasons.append("preferred-tags:" + ",".join(preferred_hits))
        else:
            # Do not turn a soft preference into a hard gate. Instead cap the
            # practical default quality of a context-free candidate: callers can
            # still explicitly accept it by choosing a lower min_score.
            score -= 35
            reasons.append("preferred-context-miss")

    return {
        "id": candidate.get("id"),
        "eligible": True,
        "score": round(max(0.0, min(score, 100.0)), 2),
        "gates": [],
        "reasons": reasons,
    }


def select_candidates(candidates, *, sound_type, required_tags=None, preferred_tags=None, min_score=70):
    loaded = [_load_candidate(value) for value in candidates]
    evaluations = [
        evaluate_candidate(
            candidate,
            sound_type=sound_type,
            required_tags=required_tags,
            preferred_tags=preferred_tags,
        )
        for candidate in loaded
    ]
    by_id = {candidate.get("id"): candidate for candidate in loaded}
    eligible = [item for item in evaluations if item["eligible"] and item["score"] >= float(min_score)]
    eligible.sort(key=lambda item: (-item["score"], str(item.get("id") or "")))
    if not eligible:
        return {
            "schema_version": 1,
            "status": "no-selection",
            "sound_type": sound_type,
            "threshold": float(min_score),
            "evaluations": evaluations,
            "action": "continue-discovery",
        }
    winner = eligible[0]
    return {
        "schema_version": 1,
        "status": "selected",
        "sound_type": sound_type,
        "threshold": float(min_score),
        "selected_id": winner["id"],
        "selected_score": winner["score"],
        "selected": by_id[winner["id"]],
        "evaluations": evaluations,
        "decision": "automatic",
    }
