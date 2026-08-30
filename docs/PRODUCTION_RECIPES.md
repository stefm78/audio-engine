# Production recipes

These recipes are director-facing combinations of **capabilities already implemented by Audio Engine**. They do not add a second runtime contract.

The machine-readable source of truth remains:

```bash
audio-engine capabilities
audio-engine voices
audio-engine sounds
```

If a recipe and the installed capability catalog ever disagree, the installed catalog wins.

At the PROD-WP-001 baseline, the built-in reusable sound catalog contains no promoted entries (`entries: []`). Sound-directed examples below therefore use consumer-owned, workspace-bounded local files. A director must provision and lock those files before rendering, or promote validated reusable assets through the existing sound-acquisition governance.

## Recipe 1 — Clean narration

**Intent:** spoken narration with no environment.

**Minimum schema:** v1.

```json
{
  "schema_version": 1,
  "id": "clean-narration",
  "title": "Clean narration",
  "segments": [
    {
      "preset": "narrateur-vif",
      "text": "Le récit commence ici.",
      "pause_after_ms": 450
    }
  ]
}
```

Use this as the default. Do not add stereo or sound design when it does not improve the listening experience.

## Recipe 2 — Stable dialogue placement

**Intent:** make speakers easier to distinguish without theatrical hard panning.

**Minimum schema:** v2.

```json
{
  "schema_version": 2,
  "id": "stable-dialogue",
  "title": "Stable dialogue",
  "actors": {
    "narrator": {"placement": "center"},
    "speaker-a": {"placement": "left"},
    "speaker-b": {"placement": "right"}
  },
  "segments": [
    {"character_id": "narrator", "preset": "narrateur-vif", "text": "Ils se font face."},
    {"character_id": "speaker-a", "preset": "conteuse-chaleureuse", "text": "Je reste ici."},
    {"character_id": "speaker-b", "preset": "officier-autorite", "text": "Et moi de l'autre côté."}
  ]
}
```

Keep a character's placement stable unless the story gives a real reason to move it.

## Recipe 3 — Continuous environment under narration

**Intent:** provide subtle context while speech stays dominant.

**Minimum schema:** v3.

```json
{
  "schema_version": 3,
  "id": "texture-under-speech",
  "title": "Texture under speech",
  "soundscape": {
    "bed": {
      "file": "assets/cathedral-room-tone.wav",
      "gain_db": -23
    },
    "ducking": "speech"
  },
  "segments": [
    {"preset": "narrateur-vif", "text": "La nef paraît immense."}
  ]
}
```

Capability mapping:

- bed/layer narrative role: `texture`;
- at most one bed;
- at most two continuous layers;
- global ducking: `speech` or `off`.

Prefer `speech` when the environment competes with intelligibility.

## Recipe 4 — Punctuation event

**Intent:** underline one idea without giving the sound its own narrative space.

**Minimum schema:** v3.

```json
{
  "schema_version": 3,
  "id": "punctuation",
  "title": "Punctuation",
  "soundscape": {
    "events": [
      {
        "file": "assets/church-bell.wav",
        "at_ms": 4200,
        "gain_db": -18,
        "placement": "right"
      }
    ],
    "ducking": "speech"
  },
  "segments": [
    {"preset": "narrateur-vif", "text": "Puis la cloche retentit."}
  ]
}
```

Use explicit `at_ms`. The public placement vocabulary is only `left`, `center`, `right`.

## Recipe 5 — Let the sound take the scene

**Intent:** narration stops and an event briefly carries information or emotion by itself.

**Minimum schema:** v4.

```json
{
  "schema_version": 4,
  "id": "foreground-scene",
  "title": "Foreground scene",
  "soundscape": {
    "events": [
      {
        "file": "assets/horse-hooves.wav",
        "role": "scene",
        "after_segment": 1,
        "space_ms": 3200
      }
    ]
  },
  "segments": [
    {"preset": "narrateur-vif", "text": "Quelque chose approche."},
    {"preset": "narrateur-vif", "text": "Puis le récit reprend."}
  ]
}
```

`space_ms` is the entire narration-free window. Valid range is published in `capabilities.limits.scene_space_ms`.

Use `scene` when the sound should finish before narration resumes.

## Recipe 6 — Short acoustic accent

**Intent:** give one short phrase a restrained spatial character without affecting the full narration.

**Minimum schema:** v4.

Author the meaningful phrase as its own segment:

```json
{
  "schema_version": 4,
  "id": "acoustic-accent",
  "title": "Acoustic accent",
  "segments": [
    {"preset": "narrateur-vif", "text": "Il pousse la porte."},
    {
      "preset": "narrateur-vif",
      "acoustic_space": "large-stone-interior",
      "text": "Écoutez."
    },
    {"preset": "narrateur-vif", "text": "Le silence revient."}
  ]
}
```

The capability catalog recommends at most roughly 2500 ms rendered duration for an accent. If the phrase is too long, split it semantically; do not request arbitrary millisecond reverb automation.

## Recipe 7 — Foreground event, then fixed carry under speech

**Intent:** a sound arrives alone, then continues for a known absolute time after speech resumes.

**Minimum schema:** v5.

```json
{
  "schema_version": 5,
  "id": "fixed-bridge",
  "title": "Fixed bridge",
  "soundscape": {
    "events": [
      {
        "file": "assets/horse-hooves.wav",
        "role": "bridge",
        "after_segment": 1,
        "foreground_ms": 3500,
        "carry_under_speech_ms": 2500,
        "gain_db": -23,
        "placement": "left"
      }
    ],
    "ducking": "speech"
  },
  "segments": [
    {"preset": "narrateur-vif", "text": "Les cavaliers approchent."},
    {"preset": "narrateur-vif", "text": "La voix reprend pendant qu'ils s'éloignent."}
  ]
}
```

Use fixed carry only when the millisecond overlap is itself the artistic intent.

## Recipe 8 — Foreground event, then measured carry through speech

**Intent:** let an event continue through the actual duration of following narration instead of guessing how long the voice will take.

**Minimum schema:** v6.

```json
{
  "schema_version": 6,
  "id": "measured-bridge",
  "title": "Measured bridge",
  "soundscape": {
    "events": [
      {
        "file": "assets/pipe-organ.wav",
        "role": "bridge",
        "after_segment": 1,
        "foreground_ms": 5200,
        "carry_through_segments": 1,
        "tail_ms": 900,
        "gain_db": -24
      }
    ],
    "ducking": "speech"
  },
  "segments": [
    {"preset": "narrateur-vif", "text": "L'orgue prend toute la place."},
    {"preset": "narrateur-vif", "text": "Puis il reste sous la narration jusqu'à la fin de cette phrase."}
  ]
}
```

This is the preferred recipe when the desired instruction is “continue under the next sentence”.

The measured speech timeline is the authority. `carry_through_segments` supports one to three following segments; optional `tail_ms` is bounded by the capability catalog.

## Recipe 9 — Texture plus one narrative event

**Intent:** retain environmental continuity while one event temporarily becomes important.

**Minimum schema:** depends on event role:

- punctuation: v3;
- scene: v4;
- bridge fixed carry: v5;
- bridge measured carry: v6.

Keep the environment bounded: one bed, at most two continuous layers and at most sixteen events. The mixer combines the deterministic environment track with speech and applies global speech ducking when requested.

## Transition defaults

Directors normally express semantics rather than hand-tuning every fade.

Installed defaults are published under `capabilities.effects.transitions`:

- continuous texture: fade in/out defaults;
- punctuation: short exit fade;
- scene: safe fade plus engine-owned pre/post margins;
- bridge: longer fade-out, pre-roll and speech ducking behavior;
- hard cut: supported only by explicit zero fade.

Consult the installed catalog rather than copying numeric defaults into a consumer permanently.

## Sound resources

Prefer validated catalog ids when the installed catalog contains suitable entries. Discover them with:

```bash
audio-engine sounds
audio-engine sounds --type ambience
audio-engine sounds --type event
```

At the current baseline the built-in catalog is empty, so these recipes deliberately show workspace-bounded local files. Those paths are examples only: the consumer must supply the exact locked assets and their provenance/licence evidence before production.

Rendering never resolves arbitrary Web URLs.

## What is not a recipe today

Do not invent a recipe for a capability the engine does not expose.

Not currently supported as first-class production semantics:

- a separate `music` resource type;
- automatic music time-stretch;
- automatic looping of arbitrary event material;
- overlapping dialogue;
- random recurrence;
- arbitrary multitrack automation;
- numeric public panning;
- HRTF/binaural positioning;
- arbitrary reverb/plugin chains;
- authentic acoustic simulation of a named place.

A consumer may have a richer internal Production Plan, but it must either compile an intention to supported Program fields or report it as unsupported before rendering.
