# Contract

Audio Engine accepts five program schema versions plus assembly schema v1.

- **Program v1** — stable narration.
- **Program v2** — semantic stereo placement and one optional legacy ambience bed.
- **Program v3** — bounded deterministic `soundscape` with explicitly timed events.
- **Program v4** — semantic acoustic spaces, safe event fades and narration-free `scene` windows anchored after segments.
- **Program v5** — v4 plus `bridge`: sound foreground that carries under the following spoken segment.
- **Assembly v1** — joins already-rendered listening units.

Older contracts remain valid unchanged. Newer-only fields are rejected rather than silently ignored.

## Shared program fields

Every program requires `schema_version`, `id`, `title`, and non-empty `segments`. Each segment requires `text` plus one of `voice`, `preset`, or `target`.

V2+ may use `actors`; v3+ may use `soundscape`; v4/v5 may use `acoustic_space` on program, actor or segment. Resolution order is segment → actor → program → `dry`.

## V1 and V2

V1 is narration only. V2 adds semantic `left`, `center`, `right` placement and one optional legacy ambience. Numeric panning remains internal.

## V3 — deterministic soundscape

A v3+ soundscape supports zero or one `bed`, at most **2** continuous `layers`, at most **16** `events`, and global ducking `speech` or `off`.

Every component declares exactly one validated catalog `sound` id or workspace-bounded local `file`. Catalog contents are SHA-256 verified before render. Bed and layers carry the narrative role `texture`.

V3 events use explicit `at_ms` timing plus optional gain and placement.

## V4 — narrative scene and acoustic space

### Acoustic space

```json
{
  "schema_version": 4,
  "segments": [
    {
      "preset": "narrateur-vif",
      "acoustic_space": "large-stone-interior",
      "text": "Une courte phrase placée dans un grand volume de pierre."
    }
  ]
}
```

Public ids are `dry`, `outdoor-open`, `small-stone-room`, `large-stone-interior`, and `confined-stone`. These are restrained synthetic evocations, not authentic impulse responses of named places. TTS clips remain dry in cache and acoustic processing is local.

For an **acoustic accent**, author a deliberately short semantic segment and apply the space only there. The capability catalog recommends a rendered duration of no more than 2500 ms. Audio Engine does not expose arbitrary millisecond slicing inside a phrase.

### Punctuation

```json
{
  "sound": "church-bell-distant",
  "role": "punctuation",
  "at_ms": 42000,
  "gain_db": -24
}
```

V4+ punctuation defaults to 0 ms fade-in and 250 ms fade-out.

### Scene

```json
{
  "sound": "historic-horse-hooves",
  "role": "scene",
  "after_segment": 3,
  "space_ms": 3200,
  "gain_db": -18
}
```

`scene` is foreground-only: Audio Engine reserves at least `space_ms` after the referenced segment, starts the sound after a short pre-roll and keeps a short post-roll before narration resumes. Long audio is trimmed to the available window with safe fades. V4 semantics remain unchanged for compatibility.

## V5 — bridge: foreground then carry

V5 adds the missing hand-off from sound back to narration:

```json
{
  "schema_version": 5,
  "soundscape": {
    "events": [
      {
        "sound": "historic-horse-hooves",
        "role": "bridge",
        "after_segment": 3,
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
    {"preset": "narrateur-vif", "text": "Le récit reprend pendant que les sabots s'éloignent."}
  ]
}
```

Rules:

- `after_segment` must reference an existing segment **with a following segment**;
- `foreground_ms` is bounded from **1000** to **10000** ms;
- `carry_under_speech_ms` is bounded from **250** to **10000** ms;
- `bridge` may not declare `at_ms` or `space_ms`;
- after a short engine-owned pre-roll, the event receives the full declared `foreground_ms` before the next voice starts;
- the same event continues under the next speech for `carry_under_speech_ms` when source/master duration permits;
- with `ducking: speech`, sidechain compression automatically lowers the bridge under narration;
- bridge defaults are 500 ms fade-in and 1200 ms fade-out;
- manifests expose requested/rendered event duration and clipping diagnostics.

This distinction is intentional: `scene` means **sound then speech**; `bridge` means **sound → sound under speech → speech**.

V4 rejects bridge fields so an Audio Engine 0.7 installation cannot silently ignore them.

## Capability catalog

`audio-engine capabilities` is the machine-readable source of truth for supported schema versions, acoustic spaces, acoustic usage patterns, sound roles, transition defaults, placement/ducking vocabularies and hard limits.

The capability catalog answers **what can the engine do?** The sound catalog answers **which validated sound assets are available?**

## Rendering model

```text
dry TTS cache
      ↓
semantic acoustic-space processing
      ↓
  speech.wav

bed + layers + punctuation + scene + bridge
                    ↓
        deterministic environment.wav
                    ↓
             speech + environment
                    ↓
                  ducking
                    ↓
               final loudnorm
```

Voice synthesis is cached independently from sound direction. Changing placement, acoustic space, fades, scene/bridge timings or gains should normally remix locally without synthesizing unchanged speech again.

## Output and graceful batch behavior

Each program produces `audio.mp3`, `manifest.json`, and `transcript.json`. `audio-engine batch` renders members independently and writes `render-report.json`; one failed program does not erase successful outputs.

## Explicit non-goals

The public contract does not define HRTF/binaural 3D, front/rear/height placement, arbitrary user-defined reverb/plugin parameters, authentic named-room claims from synthetic presets, overlapping-dialogue authoring, random scheduling, unlimited tracks, arbitrary automation, or Internet access during render.
