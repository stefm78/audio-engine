# Audio Engine

Small, reusable spoken-audio renderer.

`audio-engine` turns a declared JSON audio program into publication-ready audio assets. It is product-agnostic: consumers own content, storage, publication and playback.

```text
text ──► voice ──────────┐
                         ├──► mix ──► master
validated/local sounds ─► soundscape ┘
```

Consumers still use **one CLI, one program contract and one reusable workflow**.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e .
audio-engine voices
audio-engine sounds
audio-engine ambience discover "quiet cathedral room tone"
audio-engine validate examples/minimal.json
audio-engine validate examples/dialogue.json
audio-engine validate examples/soundscape.json
audio-engine render examples/minimal.json --out output
```

Default `speech` output is MP3 mono, 24 kHz, 80 kbit/s. Stereo dialogue, legacy ambience and schema-v3 soundscapes render stereo at least 96 kbit/s.

## Commands

```bash
audio-engine voices
audio-engine recommend --target '{"gender":"male","age":"adult","energy":5,"tags":["narrateur","vif"]}'

audio-engine sounds
audio-engine sounds --type ambience --tag interior
audio-engine sounds --type event --tag bell
audio-engine sounds --id cathedral-calm

audio-engine ambience discover "quiet cathedral room tone"
audio-engine ambience qualify FILE.wav --source-provider PROVIDER --source-page URL --license LICENSE

audio-engine render PROGRAM.json --out output/ [--sounds SOUNDS.json]
audio-engine batch "content/**/*.json" --out output/ [--sounds SOUNDS.json]
audio-engine assemble ASSEMBLY.json --out output/
audio-engine validate PROGRAM.json
```

`ambience discover/qualify` is the broad **candidate** workflow. `sounds` is the narrow **validated production meta-index**. A discovered file never becomes a public sound merely because it was downloaded.

See [`docs/SOUNDS.md`](docs/SOUNDS.md), [`docs/AMBIENCES.md`](docs/AMBIENCES.md), and [`docs/VOICES.md`](docs/VOICES.md).

## Program schemas

### v1 — narration

```json
{
  "schema_version": 1,
  "id": "demo",
  "title": "Demo",
  "segments": [
    {"preset": "narrateur-vif", "text": "Bonjour."}
  ]
}
```

### v2 — stable stereo dialogue / one legacy ambience

```json
{
  "schema_version": 2,
  "id": "dialogue",
  "title": "Dialogue",
  "actors": {
    "narrator": {"placement": "center"},
    "alice": {"placement": "left"},
    "bob": {"placement": "right"}
  },
  "segments": [
    {"character_id": "narrator", "preset": "narrateur-vif", "text": "Ils discutent."},
    {"character_id": "alice", "preset": "conteuse-chaleureuse", "text": "Bonjour."},
    {"character_id": "bob", "preset": "officier-autorite", "text": "Bonjour."}
  ]
}
```

Public placement vocabulary is only `left`, `center`, `right`; constant-power pan values remain internal.

### v3 — bounded deterministic soundscape

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

P2 is deliberately bounded: one bed, at most two continuous layers, at most sixteen explicitly timed events. There is no random scheduling or arbitrary multitrack timeline.

Each component declares exactly one of a validated catalog `sound` id or a workspace-bounded local `file`. Catalog content is hash-verified before rendering.

See [`docs/CONTRACT.md`](docs/CONTRACT.md) for the full contract.

## Rendering architecture

Soundscape rendering does **not** turn the mixer into a DAW:

```text
bed + layers + events
        ↓
 deterministic environment.wav
        ↓
speech + environment.wav
        ↓
   subtle ducking
        ↓
    final loudnorm
        ↓
       master
```

Web access is never part of rendering.

## Stage-level content-addressed reuse

Voice synthesis is cached independently from scene placement and environment mixing. Changing only left/right placement, ambience level, layer gain or event timing should normally remix locally without calling the remote TTS provider again.

Legacy ambience and v3 soundscapes each have local content-addressed preparation caches. Internal caches live under `OUT/.cache/` and are not listening assets.

## Reusable GitHub workflow

```yaml
jobs:
  audio:
    uses: stefm78/audio-engine/.github/workflows/render.yml@PINNED_SHA
    with:
      source_glob: "series/**/audio/*.json"
      output_dir: "generated/audio"
      engine_ref: "PINNED_SHA"
      sounds_path: "assets/sounds.json" # optional
```

The consumer decides whether generated files go to a site, package, object storage or GitHub Release. For production, pin workflow and `engine_ref` to the same tested SHA.

## Provider and privacy

The current TTS provider is Edge TTS and processing is remote. Do not send content that must remain local. Provider choice is isolated from soundscape and mixing semantics.

## Design boundary

Audio Engine intentionally does **not** provide HRTF/binaural 3D, front/rear/height positioning, room simulation, reverb design, random event scheduling, plugin chains, arbitrary Web fetches during render, or a general-purpose DAW.

Read [`AGENTS.md`](AGENTS.md) before changing architecture. The core rule remains:

> Input contract → exact audio assets + manifest.
