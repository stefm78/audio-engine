# Mixing guidance

Audio Engine schema v2 intentionally exposes **scene intent**, not a mixing console.

## Client-facing model

Clients should normally use:

```json
{
  "actors": {
    "narrator": {"placement": "center"},
    "speaker-a": {"placement": "left"},
    "speaker-b": {"placement": "right"}
  }
}
```

and optionally one ambience bed:

```json
{
  "ambience": {
    "file": "assets/roomtone.flac",
    "gain_db": -22,
    "loop": true,
    "ducking": "speech"
  }
}
```

Consumers should not calculate left/right gains. Numeric `pan` exists for advanced authoring but is not the recommended application UI.

## Product guidance

### Narration

Keep the narrator centered and mono unless another element genuinely requires stereo.

### Dialogue

Use stable moderate separation:

```text
speaker A        narrator        speaker B
   left           center           right
```

Do not alternate positions merely to make audio feel active.

### Ambience

Ambience supports comprehension and presence; it must not compete with speech. Start near `-22 dB` and prefer `ducking: speech` when the bed contains meaningful midrange energy.

### Client applications

A client can expose a very small UI:

```text
Speaker position: Left / Center / Right
Ambience: None / selected asset
Ambience level: Subtle / Normal / Present
```

The client maps those choices to schema v2. Audio Engine remains responsible for panning law, stereo activation, bitrate, ducking, normalization, and encoding.

## Asset rule

The Web is for discovery. Production rendering accepts a local locked file only.

Before durable publication, a reusable or product-specific ambience should have:

- known provenance;
- verified licence;
- content hash;
- a durable snapshot owned by the relevant product or shared asset pack.

Do not make playback or production depend on a third-party hotlink.

## Current scope

Supported now:
- left / center / right;
- numeric pan override;
- one ambience bed;
- loop;
- gain;
- fade in/out;
- simple speech ducking.

Not supported now:
- front/rear/height;
- HRTF/binaural 3D;
- distance simulation;
- reverb design;
- overlapping effects timelines;
- arbitrary multitrack mixing.
