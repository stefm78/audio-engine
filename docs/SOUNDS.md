# Validated sounds and soundscapes

Audio Engine separates **finding sounds** from **using sounds in production**.

- `ambience discover` / `ambience qualify` handle candidates before production.
- `sounds` exposes only resources that have passed provenance, licence, listening, content-hash and asset-locking gates.
- schema v3 `soundscape` combines validated or explicit local assets deterministically.

## Public sound meta-index

```bash
audio-engine sounds
audio-engine sounds --type ambience
audio-engine sounds --type event --tag bell
audio-engine sounds --id cathedral-calm
```

The intrinsic resource types are deliberately limited to:

- `ambience` — continuous material suitable as a bed or secondary layer;
- `event` — punctual material such as a bell, thunder, knock or impact.

`layer` is a **mix role**, not a duplicated catalog type. The same rain recording may be the main bed in one scene and a secondary layer in another.

A public catalog entry is rejected unless it is explicitly `validated`, has a verified licence, a SHA-256 content hash and a locked asset reference. A catalog id is usable at render time only when its materialized file matches the recorded SHA-256 exactly.

## Soundscape contract

Schema v3 adds a bounded soundscape:

```json
{
  "schema_version": 3,
  "id": "cathedral-scene",
  "title": "Inside the cathedral",
  "soundscape": {
    "bed": {
      "sound": "cathedral-calm",
      "gain_db": -23
    },
    "layers": [
      {
        "sound": "crowd-distant",
        "gain_db": -30
      }
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

Bounds are intentional:

- zero or one bed;
- at most two continuous layers;
- at most sixteen explicit events;
- event timing is explicit `at_ms`;
- optional semantic event placement is `left`, `center` or `right`;
- one global environment ducking mode: `speech` or `off`.

There is no random scheduling in P2. Two renders of the same declared program and assets must produce the same scene structure.

## Local files versus catalog ids

Each bed, layer or event declares exactly one of:

```json
{"sound": "forest-light"}
```

or:

```json
{"file": "assets/my-field-recording.wav"}
```

Catalog ids are preferred for reusable validated resources. Local files remain useful for product-specific recordings or experiments. HTTP(S), absolute paths and workspace escapes are rejected during rendering.

## Rendering boundary

The sound module first creates **one environment track**:

```text
bed + up to 2 layers + explicit events
                 ↓
        deterministic environment.wav
```

The existing mixer then stays simple:

```text
speech + environment.wav
          ↓
      speech ducking
          ↓
       final loudnorm
          ↓
          master
```

This is intentionally not a general-purpose DAW or arbitrary multitrack timeline.

## Caching

Soundscape preparation has its own content-addressed cache. Its fingerprint includes source hashes, declared settings, target duration/format and sound-engine code. Changing only an event time or an environment level remixes locally and does not invalidate cached voice synthesis.

## Asset governance

A validated catalog entry should contain at least:

- stable `id`;
- `type`: `ambience` or `event`;
- useful semantic tags;
- source/provider provenance;
- verified licence and attribution obligations;
- exact `content_sha256`;
- a locked/materialized asset strategy;
- optional safe defaults such as recommended gain.

Commercial-library assets whose licence forbids raw redistribution may still be represented in the meta-index, but their raw file must live in an authorized location. `asset.location` may document that state; rendering by catalog id requires an available local `asset.file` whose hash matches the validated entry.

The central rule remains:

> Discover broadly. Validate narrowly. Render from exact locked content.
