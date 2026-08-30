# Production Director integration

This document defines how an Audioguide or Audiobook production director should drive Audio Engine without becoming coupled to renderer internals.

## Boundary

Audio Engine does **not** own the director's high-level Production Plan.

A consumer may keep a richer plan containing story structure, editorial priorities, scene goals, optional material and fallback policy. Before rendering, the director/compiler reduces that plan to the public Audio Engine Program contract documented in [CONTRACT.md](CONTRACT.md).

```text
consumer story / chapter
        |
        v
Production Director
        |
        | consults
        +-------------------+-------------------+
        |                   |                   |
        v                   v                   v
audio-engine           audio-engine         audio-engine
capabilities             voices               sounds
        \                   |                   /
         \                  |                  /
          +-------- director/compiler --------+
                           |
                           v
                  Program schema v1..v6
                           |
                      validate / timing
                           |
                    targeted preview
                           |
                         render
                           |
                  manifest + audio assets
```

The Program schema is the executable contract. Product-specific authoring logic stays outside the engine.

## Discover before authoring

A director must discover the installed renderer rather than assume a larger palette:

```bash
audio-engine capabilities
audio-engine voices
audio-engine sounds
```

Use:

- `capabilities` for supported Program schema versions, acoustic spaces, sound roles, transition defaults, placement, ducking and hard limits;
- `voices` for validated voice presets and stable casting metadata;
- `sounds` for validated production-ready ambience/event resources. At the PROD-WP-001 baseline the built-in catalog is empty, so a director cannot assume any reusable sound id exists.

The machine-readable capability catalog remains `src/audio_engine/capabilities.json`. Do not create or hard-code a competing catalog in consumer applications.

## Compile the Production Plan

A consumer Production Plan may contain concepts that are useful to a director but are not Audio Engine fields, for example:

- narrative arc;
- scene objective;
- target episode duration;
- editorial priority;
- material that may be omitted;
- consumer-specific fallback policy;
- location or navigation metadata for an audioguide;
- chapter/book continuity metadata for an audiobook.

The compiler must resolve those concepts **before** calling Audio Engine.

Do not copy unknown director fields into the Program JSON. Audio Engine should receive only declared contract fields.

## Choose the lowest sufficient schema

Prefer the smallest schema version that expresses the intended production:

| Need | Minimum schema |
| --- | ---: |
| Narration | v1 |
| Actor placement / legacy ambience | v2 |
| Deterministic bed, layers, punctual events | v3 |
| Acoustic spaces / narration-free scene event | v4 |
| Bridge with fixed carry under speech | v5 |
| Bridge carried through measured spoken segment(s) | v6 |

Do not upgrade merely because a newer version exists.

## Fail cheap

Before expensive synthesis, use deterministic checks first:

```bash
audio-engine validate PROGRAM.json
audio-engine timing PROGRAM.json --out output
```

`validate` rejects invalid contract combinations.

`timing` gives measured cached durations when available and calibrated estimates otherwise. Estimates are design guidance, not final timing authority.

A director should stop before full rendering when the Program itself is invalid or requests a capability outside the installed catalog. Sound semantics can still be authored with consumer-owned local relative files, but those files must be present and governed by the consumer before render.

## Representative probe

For sound-directed programs, audition risky transitions before a full batch:

```bash
audio-engine preview PROGRAM.json --out output --event 1
```

The director should select the event(s) with the highest structural or artistic risk rather than mechanically previewing the first event.

Typical high-risk probes are:

- a `scene` event with a tight narration-free window;
- a `bridge` that must hand attention back to speech;
- a dense texture/event combination;
- a short acoustic accent;
- a transition whose source asset may be too short.

Preview reuses stage caches, so unchanged speech should not be synthesized again during later mixing changes.

## Commit late, finish robustly

The recommended production flow is:

```text
capability discovery
        |
director compile
        |
validate -------- FAIL -> stop cheaply
        |
timing / risk selection
        |
representative preview -- blocker -> stop cheaply
        |
======== commit to full render ========
        |
full render / batch
        |
manifest inspection / automatic QA
        |
human listening
```

After the commit point, non-essential product concerns should normally become warnings or consumer-side fallbacks rather than reasons to discard otherwise valid rendered units. Audio Engine batch rendering already preserves successful outputs when another unit fails.

## Timing authority

Before TTS exists, estimates help design.

After TTS exists, measured audio is authoritative.

For v6 bridges, the engine can carry an event through one to three actual rendered spoken segments using `carry_through_segments`, avoiding guessed speech durations.

Do not use MP3 tags as timing authority.

## Reproducibility

For durable production, record:

- exact Audio Engine commit/SHA;
- Program schema version;
- exact Program JSON;
- voice catalog/config used;
- sound catalog and materialized asset hashes;
- final manifest;
- render report for batches.

Reusable workflow consumers should pin `render.yml` and `engine_ref` to the same tested SHA.

## Product-specific directors

Audioguide and Audiobook directors may make different high-level decisions, but both compile to the same Audio Engine Program boundary.

Audioguide-specific concerns such as physical location, station duration, navigation and interrupted listening remain consumer metadata.

Audiobook-specific concerns such as book/chapter hierarchy, long-form continuity and chapter assembly remain consumer metadata.

Neither concern belongs in the renderer unless a future reusable audio-rendering need is demonstrated independently of one product.

## Unsupported requests

A director/compiler must not silently translate unsupported wishes into misleading Program fields.

Current explicit non-goals include:

- overlapping-dialogue authoring;
- random event scheduling;
- arbitrary multitrack/DAW automation;
- HRTF/binaural or front/rear/height positioning;
- arbitrary public reverb/plugin parameters;
- automatic music time-stretch;
- automatic event looping without catalog permission;
- authentic acoustics claims for named places;
- network asset resolution during rendering.

If a requested artistic instruction cannot be represented by the installed catalog and Program schema, report it as unsupported before expensive rendering.
