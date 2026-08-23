# Audio Engine

Small, reusable spoken-audio renderer.

`audio-engine` turns a declared JSON audio program into published-ready audio assets. It is deliberately product-agnostic: it does not know about audioguides, learning kits, websites, releases, or storage.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e .
audio-engine validate examples/minimal.json
audio-engine render examples/minimal.json --out output
```

Output:

```text
output/
  demo-minimal/
    audio.mp3
    manifest.json
    transcript.json
```

Default `speech` output is MP3, mono, 24 kHz, 80 kbit/s, normalized for spoken-word listening.

## Commands

```bash
audio-engine render PROGRAM.json --out output/
audio-engine batch "content/**/*.json" --out output/
audio-engine assemble ASSEMBLY.json --out output/
audio-engine validate PROGRAM.json
```

`batch` is best effort: one failed program is reported in `render-report.json` and does not delete successful outputs.

## Input

See [`docs/CONTRACT.md`](docs/CONTRACT.md). A minimal program is:

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

Segments may use an explicit provider voice or a preset from the bundled voice palette.

## Profiles

- `speech`: 80 kbit/s, mono, 24 kHz — default for narration.
- `speech-high`: 96 kbit/s, mono, 24 kHz — extra margin for demanding spoken material.

The engine normalizes the final assembled asset. Segment files are temporary and are never part of the published output.

## Provider and privacy

The current provider is Edge TTS. Processing is **remote**: text sent for synthesis leaves the runner. Do not use the remote provider for content that must not be sent to an external TTS service.

Provider choice is isolated from the rendering contract so a local or different remote provider can be added later without changing consumer data.

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

## Design boundaries

Read [`AGENTS.md`](AGENTS.md) before changing architecture. The core rule is:

> Input contract → audio assets + manifest.

No backend, database, content catalog, publication logic, product-specific concepts, or permanent audio storage belong here.
