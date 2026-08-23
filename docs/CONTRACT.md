# Contract

Audio Engine accepts two program schema versions plus the assembly contract.

- **Program schema v1**: stable narration contract, mono by default.
- **Program schema v2**: adds declarative stereo placement and one optional ambience bed.
- **Assembly schema v1**: joins already-rendered listening units.

A v1 program remains valid unchanged. Spatial or ambience fields in v1 are rejected rather than silently ignored.

## Program v1

```json
{
  "schema_version": 1,
  "id": "episode-01",
  "title": "Episode 1",
  "segments": [
    {
      "text": "Text to synthesize.",
      "voice": "fr-FR-RemyMultilingualNeural"
    }
  ]
}
```

Top-level fields:

- `schema_version`: `1` or `2` for programs.
- `id`: stable output identifier.
- `title`: human-readable title.
- `segments`: non-empty ordered array.
- `language`: optional metadata such as `fr-FR`.
- `profile`: optional; `speech` by default or `speech-high`.
- `lead_in_ms`: optional initial silence, default 250 ms.
- `sources`: optional provenance URLs or identifiers.

Each segment requires `text` and one of `voice`, `preset`, or `target`.

Useful optional segment fields are `speaker`, `character_id`, `pause_after_ms` (default 350), `rate`, `pitch`, and `volume`.

`voice` directly selects a provider voice. `preset` selects a configured voice preset. `target` lets the bundled simple casting scorer choose a preset from declared traits.

## Program v2: stereo dialogue

Schema v2 lets a client describe **where a speaker sits in a stable scene** without exposing channel gains or FFmpeg details.

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

Supported public placements are deliberately limited to:
- `left`;
- `center`;
- `right`.

The current mapping intentionally stays moderate: left/right are not hard-panned. The mixer uses constant-power panning. Numeric pan is **not** a public contract field; clients describe scene intent and Audio Engine owns the DSP mapping.

A segment-level `placement` overrides the actor-level declaration. Scene positions should be stable and meaningful. Do not move voices merely for decoration.

If no non-center placement and no ambience is present, `speech` remains mono at 80 kbit/s. If stereo is required, Audio Engine automatically renders two channels and raises the speech bitrate to at least 96 kbit/s.

## Program v2: ambience

A program may declare **one background ambience bed**:

```json
{
  "schema_version": 2,
  "id": "scene-with-roomtone",
  "title": "Scene with ambience",
  "ambience": {
    "file": "../assets/cathedral-roomtone.flac",
    "gain_db": -22,
    "loop": true,
    "fade_in_ms": 1000,
    "fade_out_ms": 1500,
    "ducking": "speech",
    "license": "CC0-1.0",
    "attribution": "Optional human-readable attribution"
  },
  "segments": [
    {"preset": "narrateur-vif", "text": "Bienvenue."}
  ]
}
```

Rules:
- `file` is required and is resolved relative to the program JSON file;
- arbitrary HTTP(S) URLs and absolute paths are rejected;
- when rendering inside a repository, a relative path may not escape the caller workspace;
- `gain_db` defaults to `-22` and must be between `-60` and `+6`;
- `loop` defaults to `true`;
- fades default to 1000 ms in and 1500 ms out;
- `ducking` is `speech` (default) or `off`;
- optional `license` and `attribution` metadata are copied to the manifest.

The background file belongs to the consumer or to a separately locked asset snapshot. Discovery on the Web is outside the render contract. Production inputs should be licence-checked and content-addressed before publication.

An ambience bed forces stereo so an existing stereo recording can retain its width. The final master is normalized only after voice and ambience are mixed.

## Stage-level caching

Audio Engine separates expensive synthesis from cheap mixing:

```text
text + resolved voice settings
        ↓
content-addressed voice clip cache
        ↓
placement / ambience preparation
        ↓
master mix
```

Changing only `placement`, ambience gain, fades, or ducking does **not** require a new TTS call when the text and resolved voice settings are unchanged.

The ambience preparation cache includes the source file hash, preparation settings, target duration, output format, and ambience-engine code. A change to ambience processing therefore cannot silently reuse an old prepared asset.

## Render output

For program id `episode-01`:

```text
OUT/episode-01/
  audio.mp3
  manifest.json
  transcript.json
```

`manifest.json` records the render status, source SHA-256, voice-config SHA-256, engine version, provider processing mode, profile, codec, bitrate, sample rate, channels, duration, cache information, and ambience source identity/provenance when present.

`transcript.json` contains resolved segments, resolved semantic placement, internal resolved pan for diagnostics, and sources. Consumers should use the manifest instead of probing the MP3.

Internal caches are stored below `OUT/.cache/` and are implementation details, not published listening assets.

## Batch

`audio-engine batch "path/**/*.json"` renders each matched program independently. It writes `OUT/render-report.json`.

A bad member does not roll back or delete successful renders.

## Assembly

Assembly joins already-rendered listening units and remains schema v1. It does **not** imply that every series should be concatenated.

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

Paths are relative to the assembly JSON file. Output is `OUT/long-program/audio.mp3` plus `manifest.json`.

Audioguide visit/route episodes should normally remain separate because movement occurs between listening units. Audiobooks are a typical case where `assemble` can be useful.

## Errors

Single `render`/`assemble`:
- malformed contract or missing input → non-zero exit;
- provider or FFmpeg failure → non-zero exit;
- forbidden or escaping ambience asset → non-zero exit.

`batch`:
- failures are isolated and recorded in `render-report.json`;
- successful outputs remain valid.

## Provider boundary

Program schemas do not expose provider-specific processing concepts other than optional explicit provider voice names. A later provider may implement the same synthesis interface without changing scene placement, ambience, or mixing semantics.

## Explicit non-goals for v2

Schema v2 does **not** define:
- front/rear or height rendering;
- HRTF/binaural 3D;
- distance or room simulation;
- reverb design;
- overlapping dialogue tracks;
- arbitrary multi-track sound design;
- Internet search/download during rendering.

Those features require separate evidence before they become contract surface.
