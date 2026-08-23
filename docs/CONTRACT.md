# Contract

Audio Engine accepts six program schema versions plus assembly schema v1.

- **Program v1** — stable narration.
- **Program v2** — semantic stereo placement and one optional legacy ambience bed.
- **Program v3** — bounded deterministic `soundscape` with explicitly timed events.
- **Program v4** — semantic acoustic spaces, safe event fades and narration-free `scene` windows anchored after segments.
- **Program v5** — v4 plus `bridge`: sound foreground that carries under following speech for an explicit millisecond duration.
- **Program v6** — v5 plus measured relative bridge timing: carry through rendered spoken segment(s) rather than guessed milliseconds.
- **Assembly v1** — joins already-rendered listening units.

Older contracts remain valid unchanged. Newer-only fields are rejected rather than silently ignored.

## Shared program fields

Every program requires `schema_version`, `id`, `title`, and non-empty `segments`. Each segment requires `text` plus one of `voice`, `preset`, or `target`.

V2+ may use `actors`; v3+ may use `soundscape`; v4+ may use `acoustic_space` on program, actor or segment. Resolution order is segment → actor → program → `dry`.

## V1 and V2

V1 is narration only. V2 adds semantic `left`, `center`, `right` placement and one optional legacy ambience. Numeric panning remains internal.

## V3 — deterministic soundscape

A v3+ soundscape supports zero or one `bed`, at most **2** continuous `layers`, at most **16** `events`, and global ducking `speech` or `off`.

Every component declares exactly one validated catalog `sound` id or workspace-bounded local `file`. Catalog contents are SHA-256 verified before render. Bed and layers carry the narrative role `texture`.

V3 events use explicit `at_ms` timing plus optional gain and placement.

## V4 — narrative scene and acoustic space

Public acoustic-space ids are `dry`, `outdoor-open`, `small-stone-room`, `large-stone-interior`, and `confined-stone`. These are restrained synthetic evocations, not authentic impulse responses of named places. TTS clips remain dry in cache and acoustic processing is local.

For an **acoustic accent**, author a deliberately short semantic segment and apply the space only there. The capability catalog recommends a rendered duration of no more than 2500 ms. Audio Engine does not expose arbitrary millisecond slicing inside a phrase.

A `punctuation` event uses `at_ms`. A `scene` event uses `after_segment` + `space_ms` and gives the sound narration-free foreground time. V4 semantics remain unchanged for compatibility.

## V5 — bridge: foreground then fixed carry

```json
{
  "schema_version": 5,
  "soundscape": {
    "events": [{
      "sound": "historic-horse-hooves",
      "role": "bridge",
      "after_segment": 3,
      "foreground_ms": 3500,
      "carry_under_speech_ms": 2500,
      "gain_db": -23
    }],
    "ducking": "speech"
  }
}
```

Rules:

- `after_segment` references a segment with a following segment;
- `foreground_ms` is the real sound-only interval before the next voice begins;
- `carry_under_speech_ms` is the requested overlap under resumed narration;
- `bridge` defaults to 500 ms fade-in and 1200 ms fade-out;
- speech ducking automatically lowers the bridge when narration resumes;
- the manifest reports requested/rendered duration and clipping diagnostics.

Use fixed milliseconds when the absolute overlap duration is itself the artistic intent.

## V6 — measured relative carry

V6 keeps the v5 fixed mode and adds a second, mutually exclusive bridge carry mode:

```json
{
  "schema_version": 6,
  "soundscape": {
    "events": [{
      "sound": "historic-pipe-organ",
      "role": "bridge",
      "after_segment": 5,
      "foreground_ms": 5200,
      "carry_through_segments": 1,
      "tail_ms": 900,
      "gain_db": -24
    }],
    "ducking": "speech"
  }
}
```

Meaning:

> Give the organ 5.2 seconds alone, keep it under the complete next spoken segment using that segment's **measured rendered duration**, then keep a 0.9 second tail.

V6 bridge rules:

- exactly one carry mode is declared: `carry_under_speech_ms` **or** `carry_through_segments`;
- `carry_through_segments` is 1..3 and may not run past the program's final segment;
- `tail_ms` is 0..3000 and is valid only with relative carry;
- the dry TTS clips are rendered/cached first;
- the speech track is probed and its actual segment timeline becomes the authority;
- the relative intent is then resolved to an exact local millisecond carry for the mixer;
- `mix.resolved_sound_intent` records the measured resolution, including target segment and resolved carry duration;
- MP3 tags are not used as timing authority.

This prevents a designer from guessing that a phrase lasts 2.2 seconds when the selected voice/rate actually renders it at 4.1 seconds.

## Diction timing metadata

Every cached voice clip has a sidecar JSON containing its measured duration, voice, rate, pitch, character/word counts and fingerprint. Existing cached clips are backfilled when reused.

```bash
audio-engine timing PROGRAM.json --out output
```

The timing report uses, in priority order:

1. exact measured duration for the matching cached clip;
2. median history for the same voice + rate;
3. median history for the same voice, rate-adjusted;
4. a conservative generic rate-adjusted estimate.

Estimates are **design guidance only**. Once TTS exists, measured audio is authoritative.

## Targeted preview

```bash
audio-engine preview PROGRAM.json --out output --sounds sounds.json --event 1
```

`preview` renders only the requested program, reusing all stage caches, then extracts a short MP3 window around one sound event. Omit `--event` to create a preview for every event in that program. Default context is 2500 ms before and after the event.

This command is the creative-loop tool. Full batch rendering remains the final QA/publication gate, not the first way to audition a five-second transition.

## Sound adaptation policy

The current engine uses source audio at natural speed. Events may be trimmed to the required window and receive bounded fades. It does **not** automatically time-stretch music or loop an event merely because more duration was requested. If the source/master is too short, the manifest reports clipping.

Automatic looping/crossfade should only be added later for assets explicitly declared loopable in the sound catalog. Silence remains preferable to musically invalid automatic repair.

## Capability catalog

`audio-engine capabilities` is the machine-readable source of truth for supported schema versions, acoustic spaces, sound roles, carry modes, transition defaults, placement/ducking vocabularies and hard limits.

The capability catalog answers **what can the engine do?** The sound catalog answers **which validated sound assets are available?**

## Rendering model

```text
dry TTS cache + timing sidecars
          ↓
measured speech timeline
          ↓
resolve semantic timing intent
          ↓
acoustic-space processing + soundscape
          ↓
       ducking / fades
          ↓
       final loudnorm
```

Voice synthesis is cached independently from sound direction. Changing relative carry, fades, placement or acoustic space should normally remix locally without synthesizing unchanged speech again.

## Output and graceful batch behavior

Each program produces `audio.mp3`, `manifest.json`, and `transcript.json`. `audio-engine batch` renders members independently and writes `render-report.json`; one failed program does not erase successful outputs.

## Explicit non-goals

The public contract does not define HRTF/binaural 3D, front/rear/height placement, arbitrary user-defined reverb/plugin parameters, authentic named-room claims from synthetic presets, overlapping-dialogue authoring, random scheduling, unlimited tracks, arbitrary automation, automatic music time-stretch, or Internet access during render.
