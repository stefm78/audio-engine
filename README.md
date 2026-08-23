# Audio Engine

Small, reusable spoken-audio renderer.

`audio-engine` turns a declared JSON audio program into publication-ready audio assets. Consumers own content, storage, publication and playback.

```text
text ──► dry voice ──► bounded acoustic space ──┐
                                                ├──► mix ──► master
validated/local sounds ──► soundscape ──────────┘
```

Consumers use **one CLI, one program contract and one reusable workflow**.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e .
audio-engine capabilities
audio-engine voices
audio-engine sounds
audio-engine validate examples/minimal.json
audio-engine render examples/minimal.json --out output
```

Default `speech` output is MP3 mono, 24 kHz, 80 kbit/s. Scene/soundscape features render stereo at least 96 kbit/s.

## Capability catalog

```bash
audio-engine capabilities
audio-engine capabilities --category acoustic_spaces
```

`capabilities` is the machine-readable source of truth for effects and narrative sound-direction features applications may offer. The catalog exposes only behavior the installed engine actually renders.

The sound catalog answers which validated audio assets exist; the capability catalog answers what the renderer can do with them.

See [`docs/EFFECTS.md`](docs/EFFECTS.md), [`docs/CONTRACT.md`](docs/CONTRACT.md), [`docs/SOUNDS.md`](docs/SOUNDS.md), and [`docs/VOICES.md`](docs/VOICES.md).

## Program schemas

- **v1** — narration.
- **v2** — semantic stereo placement and optional legacy ambience.
- **v3** — bounded deterministic soundscape.
- **v4** — semantic acoustic spaces, safe fades and foreground-only `scene` events.
- **v5** — `bridge`: a sound owns real foreground time, then continues under the next spoken segment.

### v4 scene

```json
{
  "schema_version": 4,
  "soundscape": {
    "events": [
      {
        "sound": "historic-horse-hooves",
        "role": "scene",
        "after_segment": 1,
        "space_ms": 3200
      }
    ]
  },
  "segments": [
    {"preset": "narrateur-vif", "text": "Le son prend brièvement la scène."},
    {"preset": "narrateur-vif", "text": "Puis la voix reprend."}
  ]
}
```

V4 scene semantics remain unchanged for compatibility: `space_ms` is the whole narration-free window and includes small engine-owned transition margins.

### v5 bridge — foreground then carry

```json
{
  "schema_version": 5,
  "soundscape": {
    "events": [
      {
        "sound": "historic-horse-hooves",
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
    {"preset": "narrateur-vif", "text": "Jeanne entre dans la ville."},
    {"preset": "narrateur-vif", "text": "La narration revient pendant que les sabots s'éloignent."}
  ]
}
```

After a small pre-roll, `foreground_ms` is the **actual duration for which the sound is alone before narration restarts**. The sound then carries under the next segment for `carry_under_speech_ms`; speech ducking lowers it automatically and the bridge fades out smoothly.

V4 rejects bridge fields, so an older Audio Engine cannot silently ignore this intent.

## Acoustic spaces and accents

The bounded public spaces are `dry`, `outdoor-open`, `small-stone-room`, `large-stone-interior`, and `confined-stone`. They are synthetic evocations, never claims to reproduce a named place's authentic acoustics.

An **acoustic accent** is authored by splitting a short meaningful phrase into its own segment and applying `acoustic_space` only there. The catalog recommends no more than roughly 2500 ms rendered duration. Audio Engine intentionally does not expose arbitrary millisecond-level reverb automation inside speech.

The TTS cache always stores dry voice. Changing acoustic treatment or sound direction remixes locally without a new TTS call for unchanged text/voice parameters.

## Rendering architecture

```text
dry TTS clips
   ↓ optional bounded acoustic treatment
speech.wav

texture + punctuation + scene + bridge
               ↓
 deterministic environment.wav
               ↓
        speech + environment
               ↓
             ducking
               ↓
          final loudnorm
```

Web access is never part of rendering.

## Stage-level reuse

Voice synthesis is content-addressed independently from placement, acoustic-space processing and soundscape mixing. Changing only placement, acoustic space, gains, fades or scene/bridge timing should normally remix locally.

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

The consumer decides whether outputs go to a site, package, object storage or GitHub Release. Production callers should pin workflow and `engine_ref` to the same tested SHA.

## Provider and privacy

The current TTS provider is Edge TTS and processing is remote. Do not send content that must remain local. Provider choice is isolated from soundscape and mixing semantics.

## Design boundary

Audio Engine intentionally does **not** provide HRTF/binaural 3D, front/rear/height positioning, arbitrary user-defined reverb parameters, plugin chains, random event scheduling, arbitrary Web fetches during render, or a general-purpose DAW.

Read [`AGENTS.md`](AGENTS.md) before changing architecture. The core rule remains:

> Input contract → exact audio assets + manifest.
