# Audio Engine

Small, reusable spoken-audio renderer.

`audio-engine` turns a declared JSON audio program into publication-ready audio assets. It is deliberately product-agnostic: it does not know about audioguides, learning kits, websites, releases, or storage.

Internally, the pipeline is deliberately split into three responsibilities:

```text
text ──► voice ──┐
                 ├──► mix ──► master
asset ─► ambience┘
```

Consumers still use **one CLI, one JSON contract, and one GitHub workflow**.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e .
audio-engine validate examples/minimal.json
audio-engine voices
audio-engine render examples/minimal.json --out output
audio-engine render examples/dialogue.json --out output
```

Output:

```text
output/
  demo-minimal/
    audio.mp3
    manifest.json
    transcript.json
```

Default `speech` output is MP3, mono, 24 kHz, 80 kbit/s, normalized for spoken-word listening. A v2 program that declares stereo placement or ambience automatically renders stereo at at least 96 kbit/s.

## Commands

```bash
audio-engine voices
audio-engine recommend --target '{"gender":"male","age":"adult","energy":5,"tags":["narrateur","vif"]}'
audio-engine render PROGRAM.json --out output/
audio-engine batch "content/**/*.json" --out output/
audio-engine assemble ASSEMBLY.json --out output/
audio-engine validate PROGRAM.json
```

`voices` publishes the human-validated French palette, the quality criteria inherited from the initial blind benchmark, and the casting rules. `recommend` ranks suitable presets for a requested vocal profile without synthesizing anything. See [`docs/VOICES.md`](docs/VOICES.md).

`batch` is best effort: one failed program is reported in `render-report.json` and does not delete successful outputs.

## Contracts

See [`docs/CONTRACT.md`](docs/CONTRACT.md).

### Schema v1 — narration

```json
{
  "schema_version": 1,
  "id": "demo",
  "title": "Demo",
  "language": "fr-FR",
  "profile": "speech",
  "segments": [
    {
      "speaker": "Narrateur",
      "voice": "fr-FR-RemyMultilingualNeural",
      "text": "Bonjour.",
      "pause_after_ms": 400
    }
  ]
}
```

### Schema v2 — dialogue stéréo

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

Clients describe the scene. Audio Engine owns constant-power channel gains and output encoding.

### Schema v2 — optional ambience

```json
{
  "schema_version": 2,
  "id": "cathedral-scene",
  "title": "Cathedral scene",
  "ambience": {
    "file": "assets/cathedral-roomtone.flac",
    "gain_db": -22,
    "loop": true,
    "fade_in_ms": 1000,
    "fade_out_ms": 1500,
    "ducking": "speech"
  },
  "segments": [
    {"preset": "narrateur-vif", "text": "Bienvenue."}
  ]
}
```

The ambience is a local/snapshotted production asset relative to the JSON program. Arbitrary Web URLs are rejected. Use the Web to discover candidates; qualify licence/quality once, then render from a locked asset.

## Profiles

- `speech`: 80 kbit/s mono by default; 96 kbit/s minimum when stereo is required; 24 kHz.
- `speech-high`: 96 kbit/s mono or stereo; 24 kHz.

The engine normalizes only the final master.

## Stage-level content-addressed reuse

A completed master is reusable only when its render fingerprint still matches. In addition, expensive TTS clips have their own content-addressed cache keyed by text, resolved voice settings, provider, and provider code.

That means changing only:

- `left` → `right`;
- ambience level;
- fades;
- ducking;

normally remixes locally without calling the remote TTS provider again.

Ambience preparation has its own cache keyed by source content hash and processing settings.

Internal stage caches live below `OUT/.cache/`; they are not listening assets and should not be published as product content.

## Provider and privacy

The current provider is Edge TTS. Processing is **remote**: text sent for synthesis leaves the runner. Do not use the remote provider for content that must not be sent to an external TTS service.

Provider choice is isolated from placement, ambience, and mixing so a local or different remote voice provider can be added later without changing client scene data.

## Reusable GitHub workflow

A consumer repository can call:

```yaml
jobs:
  audio:
    uses: stefm78/audio-engine/.github/workflows/render.yml@main
    with:
      source_glob: "series/**/audio/*.json"
      output_dir: "generated/audio"
      engine_ref: "main"
```

The called workflow uploads the generated directory as an Actions artifact. The **consumer** decides whether those files go to a GitHub Release, a site build, a package, or somewhere else.

For production, pin both the called workflow and `engine_ref` to the same tested tag or SHA.

## Current design boundary

P1 intentionally supports:

- mono narration;
- stable left/center/right dialogue placement;
- numeric pan as an advanced override;
- one optional background ambience;
- gain, loop, fades, and simple speech ducking;
- automatic mono/stereo output;
- final normalization and encoding.

P1 intentionally does **not** implement HRTF/binaural 3D, front/rear/height positioning, room simulation, reverb design, effects timelines, or a general-purpose multitrack workstation.

Read [`AGENTS.md`](AGENTS.md) before changing architecture. The core rule remains:

> Input contract → audio assets + manifest.
