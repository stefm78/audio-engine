from pathlib import Path

import pytest

from audio_engine.voice_lab import AGE_STAGES, build_campaign, probe_catalog, render_campaign
from audio_engine.voices import resolve_segments


VOICE_CONFIG = {
    "version": 1,
    "presets": [
        {
            "id": "actor-calm",
            "voice": "fr-FR-ActorNeural",
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
            "traits": {"gender": "male", "age": "adult", "energy": 2},
            "tags": ["calm"],
        },
        {
            "id": "actor-intense",
            "voice": "fr-FR-ActorNeural",
            "rate": "+12%",
            "pitch": "+5Hz",
            "volume": "+4%",
            "traits": {"gender": "male", "age": "adult", "energy": 5},
            "tags": ["urgent"],
        },
        {
            "id": "other-actor",
            "voice": "fr-FR-OtherNeural",
            "rate": "+0%",
            "pitch": "+0Hz",
            "volume": "+0%",
            "traits": {"gender": "male", "age": "adult", "energy": 3},
            "tags": [],
        },
    ],
}


class FakeProvider:
    name = "fake"
    processing = "local-test"
    expressive_controls = ("rate", "pitch", "volume")

    def list_voices(self, locale_prefix=None):
        voices = [
            {"voice": "fr-FR-OneNeural", "locale": "fr-FR", "gender": "female", "friendly_name": "One"},
            {"voice": "en-US-TwoNeural", "locale": "en-US", "gender": "male", "friendly_name": "Two"},
        ]
        if locale_prefix:
            voices = [item for item in voices if item["locale"].startswith(locale_prefix)]
        return voices

    def synthesize(self, segment, path):
        Path(path).write_bytes(b"fake-mp3")


def test_probe_catalog_separates_identity_emotion_and_age():
    catalog = probe_catalog()
    assert catalog["principles"]["identity_first"] is True
    assert catalog["principles"]["emotion_never_implies_recast"] is True
    assert tuple(catalog["age_stages"]) == AGE_STAGES
    assert any(item["kind"] == "age-lineage" for item in catalog["probes"])
    assert any(item["kind"] == "performance" for item in catalog["probes"])


def test_campaign_plan_can_scan_provider_french_voices_without_invented_traits():
    plan = build_campaign(
        voice_config=VOICE_CONFIG,
        provider=FakeProvider(),
        scope="provider",
        stage="fingerprint",
    )
    assert plan["candidate_count"] == 1
    assert plan["probe_count"] == 3
    assert plan["job_count"] == 3
    assert plan["jobs"][0]["candidate"]["voice"] == "fr-FR-OneNeural"
    assert "traits" not in plan["jobs"][0]["candidate"]


def test_render_campaign_is_best_effort_and_persists_manifest(tmp_path):
    result = render_campaign(
        tmp_path,
        voice_config=VOICE_CONFIG,
        provider=FakeProvider(),
        scope="presets",
        stage="age",
    )
    assert result["status"] == "success"
    assert result["rendered_count"] == len(VOICE_CONFIG["presets"])
    assert (tmp_path / "campaign.json").exists()
    assert len(list((tmp_path / "clips").glob("*.mp3"))) == len(VOICE_CONFIG["presets"])


def test_character_target_changes_do_not_recast_identity():
    program = {
        "segments": [
            {
                "character_id": "captain",
                "target": {"gender": "male", "age": "adult", "energy": 2},
                "text": "Calme.",
            },
            {
                "character_id": "captain",
                "target": {"gender": "male", "age": "adult", "energy": 5, "tags": ["urgent"]},
                "text": "Urgence.",
                "rate": "+15%",
            },
        ]
    }
    resolved = resolve_segments(program, VOICE_CONFIG)
    assert resolved[0]["voice"] == resolved[1]["voice"]
    assert resolved[1]["rate"] == "+15%"
    assert resolved[0]["casting_identity"] == "fr-FR-ActorNeural"


def test_same_provider_voice_may_change_preset_for_performance():
    program = {
        "segments": [
            {"character_id": "captain", "preset": "actor-calm", "text": "Calme."},
            {"character_id": "captain", "preset": "actor-intense", "text": "Courez !"},
        ]
    }
    resolved = resolve_segments(program, VOICE_CONFIG)
    assert resolved[0]["voice"] == resolved[1]["voice"] == "fr-FR-ActorNeural"
    assert resolved[0]["resolved_preset"] == "actor-calm"
    assert resolved[1]["resolved_preset"] == "actor-intense"


def test_different_provider_voice_for_same_character_is_rejected():
    program = {
        "segments": [
            {"character_id": "captain", "preset": "actor-calm", "text": "Calme."},
            {"character_id": "captain", "preset": "other-actor", "text": "Autre voix."},
        ]
    }
    with pytest.raises(ValueError, match="cannot silently change provider voice"):
        resolve_segments(program, VOICE_CONFIG)
