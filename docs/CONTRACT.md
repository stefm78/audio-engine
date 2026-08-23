# Contract

Audio Engine accepts three program schema versions plus assembly schema v1.

- **Program v1** — stable narration; mono by default.
- **Program v2** — v1 plus semantic stereo placement and one optional legacy ambience bed.
- **Program v3** — v2 plus one bounded deterministic `soundscape`.
- **Assembly v1** — joins already-rendered listening units.

Older contracts remain valid unchanged. Newer-only fields are rejected rather than silently ignored.

## Shared program fields

Every program requires:
- `schema_version`: `1`, `2`, or `3`;
- `id`: stable output identifier;
- `title`: human-readable title;
- non-empty `segments`.

Useful optional top-level fields include `language`, `profile`, `lead_in_ms`, `sources`, and, for v2/v3, `actors`.

Each segment requires `text` and one of `voice`, `preset`, or `target`. Optional fields include `speaker`, `character_id`, `pause_after_ms`, `rate`, `pitch`, `volume`, and in v2/v3 semantic `placement`.

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

Spatial placement, legacy ambience and soundscape are not valid v1 fields.

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

Public placements are strictly `left`, `center`, and `right`. The mixer owns the moderate constant-power numeric mapping; numeric pan is not public contract surface.

A segment-level placement overrides its actor placement. Scene positions should represent stable scene intent rather than decorative movement.

### v2 legacy ambience

A v2 program may declare one background file:

```json
{
  "ambience": {
    "file": "../assets/cathedral-roomtone.flac",
    "gain_db": -22,
    "loop": true,
    "fade_in_ms": 1000,
    "fade_out_ms": 1500,
    "ducking": "speech",
    "license": "CC0-1.0",
    "attribution": "Optional attribution"
  }
}
```

`file` is local, relative and workspace-bounded. HTTP(S), absolute paths and workspace escapes are rejected. Gain is `-60..+6` dB; ducking is `speech` or `off`. Legacy ambience remains supported in schema v3 for compatibility, but a program may not declare both `ambience` and `soundscape`.

## Program v3 — deterministic soundscape

Schema v3 introduces sound composition without introducing an arbitrary DAW timeline.

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

### Bounds

A soundscape supports:
- zero or one `bed`;
- at most **2** `layers`;
- at most **16** `events`;
- one global `ducking`: `speech` (default) or `off`.

At least one of bed/layers/events must be present.

These limits are deliberate API constraints, not current performance limits.

### Sound references

Every bed/layer/event declares **exactly one** of:

```json
{"sound": "validated-catalog-id"}
```

or:

```json
{"file": "assets/product-specific.wav"}
```

A `sound` resolves through the validated sound meta-index supplied by `--sounds` or the bundled catalog. Catalog ids are type checked:
- bed/layer require an intrinsic `ambience` resource;
- event requires an intrinsic `event` resource.

The materialized catalog file must match the catalog `content_sha256` exactly before it is accepted for rendering.

Local `file` inputs remain workspace-bounded and network-free.

### Bed and layers

Continuous components support:
- `gain_db`: default `-22` for bed and `-28` for layer, range `-60..+6`;
- `loop`: default `true`;
- `fade_in_ms`: default `1000`, non-negative;
- `fade_out_ms`: default `1500`, non-negative.

`layer` is a soundscape role, not a catalog resource type. The same validated ambience may serve as the main bed or a secondary layer.

### Events

Events require:
- `at_ms`: explicit non-negative timestamp;
- optional `gain_db`, default `-18`, range `-60..+6`;
- optional `placement`: `left`, `center` (default), or `right`.

P2 intentionally has no random/recurring scheduling. An event whose start time lies beyond the rendered program duration is rejected.

## Validated sound meta-index

The public `sounds` catalog contains only production-approved entries. Each entry must have:
- unique stable id;
- intrinsic type `ambience` or `event`;
- `status: validated`;
- semantic tags;
- exact lowercase SHA-256 content hash;
- verified per-asset licence metadata;
- locked asset information.

`asset.file` must be a local relative path. A location-only asset can document licensed/private storage but is not directly renderable by catalog id until materialized locally.

See [`SOUNDS.md`](SOUNDS.md).

## Rendering model

Soundscape composition remains bounded internally:

```text
bed + layers + events
        ↓
 deterministic environment.wav
        ↓
speech + environment.wav
        ↓
      ducking
        ↓
    final loudnorm
```

One soundscape therefore does not turn `mix` into a general multitrack engine.

## Stereo

`speech` remains mono 80 kbit/s when no scene feature needs stereo. Non-center dialogue, legacy ambience, or a v3 soundscape automatically produces stereo and raises speech output to at least 96 kbit/s.

## Stage-level caching

Expensive TTS clips are content-addressed independently from placement and sound design.

Environment caches include exact source hashes, declared processing settings, target duration/format and relevant engine code. Changing only an event timestamp, layer gain, fades, ducking or speaker placement normally remixes locally without synthesizing unchanged speech again.

## Output

For program id `episode-01`:

```text
OUT/episode-01/
  audio.mp3
  manifest.json
  transcript.json
```

The manifest records engine/provider/profile data, source and render fingerprints, audio properties, stage-cache information and, when present, legacy ambience or soundscape component metadata including content hashes and catalog provenance/licence data.

Internal caches live below `OUT/.cache/` and are not publication assets.

## Batch

`audio-engine batch "path/**/*.json"` renders members independently and writes `OUT/render-report.json`. A failed program does not remove successful outputs.

## Assembly

Assembly remains schema v1 and joins existing listening units:

```json
{
  "schema_version": 1,
  "id": "long-program",
  "profile": "speech",
  "inputs": [
    {"file": "chapter-01.mp3", "pause_after_ms": 1200},
    {"file": "chapter-02.mp3"}
  ]
}
```

## Explicit non-goals

The public program schemas do not define:
- front/rear/height or HRTF/binaural 3D;
- distance/room simulation or reverb design;
- overlapping dialogue authoring;
- random event scheduling;
- unlimited tracks/events or arbitrary automation;
- plugin/effects chains;
- Internet search/download during rendering;
- a general-purpose DAW timeline.
