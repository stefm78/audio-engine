# Contract v1

Audio Engine has two input contracts: **program** (`render`) and **assembly** (`assemble`).

## Program

Required:

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

- `schema_version`: must be `1`.
- `id`: stable output identifier.
- `title`: human-readable title.
- `segments`: non-empty ordered array.
- `language`: optional metadata such as `fr-FR`.
- `profile`: optional; `speech` by default or `speech-high`.
- `lead_in_ms`: optional initial silence, default 250 ms.
- `sources`: optional provenance URLs or identifiers.

Each segment requires:
- `text`;
- one of `voice`, `preset`, or `target`.

Useful optional segment fields:
- `speaker`;
- `character_id`;
- `pause_after_ms` (default 350);
- `rate`, `pitch`, `volume`.

`voice` directly selects a provider voice. `preset` selects a configured voice preset. `target` lets the bundled simple casting scorer choose a preset from declared traits.

### Render output

For program id `episode-01`:

```text
OUT/episode-01/
  audio.mp3
  manifest.json
  transcript.json
```

`manifest.json` records the render status, source SHA-256, voice-config SHA-256, engine version, provider processing mode, profile, codec, bitrate, sample rate, channels, duration, and warnings.

`transcript.json` contains resolved segments and sources. Consumers should use the manifest instead of probing the MP3.

## Batch

`audio-engine batch "path/**/*.json"` renders each matched program independently. It writes `OUT/render-report.json`.

A bad member does not roll back or delete successful renders.

## Assembly

Assembly joins already-rendered listening units. It does **not** imply that every series should be concatenated.

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

Paths are relative to the assembly JSON file.

Output is `OUT/long-program/audio.mp3` plus `manifest.json`.

Audioguide visit/route episodes should normally remain separate because movement occurs between listening units. Audiobooks are a typical case where `assemble` can be useful.

## Errors

Single `render`/`assemble`:
- malformed contract or missing input → non-zero exit;
- provider or FFmpeg failure → non-zero exit.

`batch`:
- failures are isolated and recorded in `render-report.json`;
- successful outputs remain valid.

## Provider boundary

Schema v1 does not expose provider-specific concepts other than explicit provider voice names. A later provider may implement the same synthesis interface without changing the rest of the contract.
