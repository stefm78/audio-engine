# Contract

Audio Engine accepts four program schema versions plus assembly schema v1.

- **Program v1** — stable narration; mono by default.
- **Program v2** — v1 plus semantic stereo placement and one optional legacy ambience bed.
- **Program v3** — v2 plus one bounded deterministic `soundscape` with explicitly timed events.
- **Program v4** — v3 plus semantic acoustic spaces, safe event fades, and narration-free `scene` windows anchored after segments.
- **Assembly v1** — joins already-rendered listening units.

Older contracts remain valid unchanged. Newer-only fields are rejected rather than silently ignored.

## Shared program fields

Every program requires:
- `schema_version`: `1`, `2`, `3`, or `4`;
- `id`: stable output identifier;
- `title`: human-readable title;
- non-empty `segments`.

Useful optional top-level fields include `language`, `profile`, `lead_in_ms`, and `sources`. V2+ may use `actors`; v3+ may use `soundscape`; v4 may use `acoustic_space`.

Each segment requires `text` and one of `voice`, `preset`, or `target`. Optional fields include `speaker`, `character_id`, `pause_after_ms`, `rate`, `pitch`, `volume`; v2+ may use semantic `placement`; v4 may use `acoustic_space`.

## Program v1 — narration

```json
{
  "schema_version": 1,
  "id": "episode-01",
  "title": "Episode 1",
  "segments": [
    {"preset": "narrateur-vif", "text": "Text to synthesize."}
  ]
}
```

Spatial placement, legacy ambience, soundscape and acoustic-space processing are not valid v1 fields.

## Program v2 — stereo scene

```json
{
  "schema_version": 2,
  "id": "dialogue-01",
  "title": "Dialogue",
  "actors": {
    "narrator": {"placement": "center"},
    "alice": {"placement": "left"},
    "bob": {"placement": "right"}
  },
  "segments": [
    {"character_id": "narrator", "preset": "narrateur-vif", "text": "Deux personnes discutent."},
    {"character_id": "alice", "preset": "conteuse-chaleureuse", "text": "Bonjour."},
    {"character_id": "bob", "preset": "officier-autorite", "text": "Bonjour."}
  ]
}
```

Public placements are strictly `left`, `center`, and `right`. Numeric pan remains internal. A segment-level placement overrides its actor placement.

### v2 legacy ambience

A v2+ program may declare one background file:

```json
{
  "ambience": {
    "file": "../assets/cathedral-roomtone.flac",
    "gain_db": -22,
    "loop": true,
    "fade_in_ms": 1000,
    "fade_out_ms": 1500,
    "ducking": "speech"
  }
}
```

`file` is local, relative and workspace-bounded. HTTP(S), absolute paths and workspace escapes are rejected. Gain is `-60..+6` dB; ducking is `speech` or `off`. A program may not declare both `ambience` and `soundscape`.

## Program v3 — deterministic soundscape

```json
{
  "schema_version": 3,
  "id": "cathedral-scene",
  "title": "Inside the cathedral",
  "soundscape": {
    "bed": {"sound": "cathedral-calm", "gain_db": -23},
    "layers": [
      {"sound": "crowd-distant", "gain_db": -30}
    ],
    "events": [
      {
        "sound": "church-bell-distant",
        "at_ms": 42000,
        "gain_db": -18,
        "placement": "right"
      }
    ],
    "ducking": "speech"
  },
  "segments": [
    {"preset": "narrateur-vif", "text": "Bienvenue dans la nef."}
  ]
}
```

### Bounds

A v3/v4 soundscape supports:
- zero or one `bed`;
- at most **2** `layers`;
- at most **16** `events`;
- one global `ducking`: `speech` (default) or `off`.

At least one bed/layer/event must be present. These limits are deliberate API constraints, not current performance limits.

### Sound references

Every bed/layer/event declares exactly one of:

```json
{"sound": "validated-catalog-id"}
```

or:

```json
{"file": "assets/product-specific.wav"}
```

Catalog ids are type checked: bed/layer require intrinsic `ambience`; event requires intrinsic `event`. Materialized catalog content must match its exact `content_sha256`. Local file inputs remain workspace-bounded and network-free.

### Bed and layers

Continuous components support:
- `gain_db`: default `-22` for bed and `-28` for layer, range `-60..+6`;
- `loop`: default `true`;
- `fade_in_ms`: default `1000`, non-negative;
- `fade_out_ms`: default `1500`, non-negative.

Bed and layer carry the narrative role `texture`.

### V3 events

V3 events require:
- `at_ms`: explicit non-negative timestamp;
- optional `gain_db`, default `-18`;
- optional `placement`: `left`, `center`, or `right`.

V4-only event fields are rejected in v3. This prevents older engines from silently ignoring newer sound direction.

## Program v4 — narrative sound direction

V4 adds two independent concepts: **acoustic space for voices** and **narrative intent for sound events**.

### Acoustic space

```json
{
  "schema_version": 4,
  "acoustic_space": "large-stone-interior",
  "segments": [
    {
      "preset": "narrateur-vif",
      "text": "Le volume de pierre change notre perception de la voix."
    },
    {
      "preset": "narrateur-vif",
      "acoustic_space": "dry",
      "text": "Puis le narrateur revient au premier plan."
    }
  ]
}
```

Available ids are published by:

```bash
audio-engine capabilities --category acoustic_spaces
```

Initial ids are:
- `dry`;
- `outdoor-open`;
- `small-stone-room`;
- `large-stone-interior`;
- `confined-stone`.

Resolution order is segment → actor → program → `dry`.

These are restrained synthetic acoustic evocations. They are not authentic impulse responses of named places. TTS clips remain dry in cache; acoustic processing happens locally afterwards.

### V4 punctuation events

A punctuation event remains explicitly timed:

```json
{
  "sound": "church-bell-distant",
  "role": "punctuation",
  "at_ms": 42000,
  "gain_db": -24,
  "placement": "right"
}
```

`role` defaults to `punctuation`. V4 punctuation defaults to `fade_in_ms: 0` and `fade_out_ms: 250`. A hard edge is possible only by explicitly declaring a zero fade.

### V4 scene events

A `scene` event is anchored to the narration rather than an absolute millisecond:

```json
{
  "sound": "historic-horse-hooves",
  "role": "scene",
  "after_segment": 3,
  "space_ms": 3200,
  "gain_db": -18,
  "placement": "left"
}
```

Rules:
- `after_segment` references an existing 1-based segment number;
- `space_ms` is bounded from **750** to **15000** ms;
- `scene` may not also declare `at_ms`;
- Audio Engine makes the effective pause after that segment at least `space_ms`;
- the event starts after a short engine-owned pre-roll and stops before a short post-roll;
- long source audio is trimmed to the available window;
- default fades are 180 ms in and 500 ms out, clamped for short assets.

The narration therefore genuinely stops while a scene sound carries information or emotion. This is not simulated by merely raising background volume.

## Capability catalog

`audio-engine capabilities` is the machine-readable source of truth for what an application may offer. It publishes:
- supported program schema versions;
- acoustic spaces;
- narrative sound roles;
- transition defaults;
- placement and ducking vocabularies;
- hard limits and explicit non-capabilities.

The capability catalog and the sound catalog answer different questions: **what operations can the engine perform?** versus **which validated audio resources are available?**

See [`EFFECTS.md`](EFFECTS.md) and [`SOUNDS.md`](SOUNDS.md).

## Rendering model

```text
dry voice cache
      ↓
semantic acoustic-space processing
      ↓
  speech.wav

bed + layers + punctuation + scenes
              ↓
 deterministic environment.wav
              ↓
       speech + environment
              ↓
           ducking
              ↓
        final loudnorm
```

One soundscape does not turn `mix` into a general multitrack engine.

## Stereo

`speech` remains mono 80 kbit/s when no scene feature needs stereo. Non-center dialogue, legacy ambience, or a v3/v4 soundscape produces stereo and raises output to at least 96 kbit/s. Acoustic-space processing alone does not force stereo.

## Stage-level caching

Expensive TTS clips are content-addressed independently from placement, acoustic space and sound design.

Environment caches include exact source hashes, declared processing settings, resolved scene timing, target duration/format and relevant engine code. Changing only an event timestamp, scene spacing, fade, layer gain, acoustic space, ducking or speaker placement normally remixes locally without synthesizing unchanged speech again.

## Output

For program id `episode-01`:

```text
OUT/episode-01/
  audio.mp3
  manifest.json
  transcript.json
```

The manifest records engine/provider/profile data, source and render fingerprints, audio properties, stage-cache information, resolved acoustic spaces/timeline, and soundscape component provenance/licence/transition metadata.

Internal caches live below `OUT/.cache/` and are not publication assets.

## Batch

`audio-engine batch "path/**/*.json"` renders members independently and writes `OUT/render-report.json`. A failed program does not remove successful outputs.

## Assembly

Assembly remains schema v1 and joins existing listening units.

## Explicit non-goals

The public program schemas do not define:
- HRTF/binaural 3D or front/rear/height positioning;
- arbitrary user-defined reverb/plugin parameters;
- claims of authentic named-room acoustics from synthetic presets;
- overlapping dialogue authoring;
- random event scheduling;
- unlimited tracks/events or arbitrary automation;
- plugin/effects chains;
- Internet search/download during rendering.
