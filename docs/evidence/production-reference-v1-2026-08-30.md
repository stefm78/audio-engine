# Production Reference v1 — machine closeout

Date: 2026-08-30

Authority: issue #179 — PROD-WP-001

## Scope

This receipt records the autonomous, machine-verifiable closeout of the first Production Reference Render workflow.

It does **not** record a human artistic acceptance.

Production invariants remained unchanged throughout this work:

- Production TTS remains Edge.
- Production does not depend on Voice Lab.
- No new model, provider, NUC lane, or Lab experiment was introduced.
- Audioguide/Audiobook-specific authoring remains outside Audio Engine.
- The executable Audio Engine boundary remains Program schema v1..v6.

## Exact branch evidence

Exact implementation/reference HEAD:

```text
4b8d577c302d5fc491ee12fe7d961b346faf05d0
```

Production Reference workflow:

```text
run: 33298721488
conclusion: SUCCESS
artifact id: 9728231085
artifact name: production-reference-v1-4b8d577c302d5fc491ee12fe7d961b346faf05d0
artifact digest: sha256:deb43255146e2f64d87423110170913795549feb54a89bbc3b76b47514e15a87
```

Repository CI on the same HEAD:

```text
run: 33298721496
conclusion: SUCCESS
```

## Gate results

```text
DIRECTOR_INTERFACE_DOCUMENTED      PASS
CHEAP_PREFLIGHT_PASS               PASS
REFERENCE_PROGRAM_VALID            PASS
REPRESENTATIVE_PROBE_PASS          PASS
FULL_REFERENCE_RENDER              PASS
AUTOMATIC_STRUCTURAL_QA            PASS
LISTENING_WINDOWS_GENERATED         PASS
REFERENCE_RENDER_V0_READY_FOR_HUMAN PASS
```

The following gate is intentionally **not** claimed:

```text
PRODUCTION_REFERENCE_RENDER_PASS    NOT YET
```

Reason: no human listening / artistic scorecard has been completed for this V0.

## Durable sound seed

Release:

```text
tag: production-reference-sounds-v1
release id: 379206877
```

Exact promoted audio bytes used by the reference package:

| Asset | SHA-256 |
| --- | --- |
| reference-square-ambience.ogg | `58f07b0c0878b566160b20067c3dfdb6a9eb4f12303b370b63a815866224f00f` |
| reference-bell-punctuation.ogg | `f57283d08a0ecb052425af1ac1457f827fa27f423d49158963b3370c89fc942d` |
| reference-bell.ogg | `f8ccd337ee70f4e65a90aea288c1fc2a6649eab362b9bf9e0bee795bb9b96b16` |
| reference-horse-hooves.ogg | `5c0e7b589f2c3cdcf4613702c628501ddfb4a4a31a8582a79cc7eb92d64eeb85` |

Supporting machine catalog:

```text
sounds.json sha256:
ca57725a5668df9ae41f3a3aa6774b75502b6b8809444cbc81054a72a2d4474b
```

The Release also carries catalog and selection receipts for licence/provenance and exact source choice.

## Fail-cheap evidence

The implementation was intentionally challenged through actual failure modes before full render.

### 1. Asset discovery failed before TTS

Initial hydration could resolve two of three required sounds but not the horse-hooves event.

The workflow stopped before any TTS or full render.

The requirement was narrowed to an exact qualified source rather than weakening the gate.

### 2. Representative probe is a separate Program

Audit found that `audio-engine preview` first renders the supplied Program and only then extracts an audition window.

Therefore it cannot serve as a cheap pre-render probe for a full episode.

The final flow uses a separate bounded `probe.json`, preserving only the risky interaction.

### 3. Final bridge tail needs master headroom

The first bridge probe correctly reported master clipping because a measured relative carry reached the final spoken segment without enough final pause for the requested tail.

The reference Program was corrected to reserve final time.

The engine was not changed to hide the clipping.

### 4. Ingredients are role-sensitive

A technically valid long bell was initially used as a punctuation event.

Because punctuation uses the source naturally rather than an authored play-duration field, it remained active far too long for that narrative role.

The reference now uses a dedicated short punctuation one-shot while retaining the long bell for the scene event.

This is a Production Director / recipe decision, not a new renderer feature.

## Final machine flow

```text
capability discovery
        |
director compile
        |
full Program preflight
        |
small probe Program preflight
        |
small probe render
        |
structural probe PASS
        |
======== COMMIT ========
        |
full Reference Render
        |
automatic structural QA
        |
post-render listening windows
        |
human listening gate
```

## Status

```text
REFERENCE_RENDER_V0_READY_FOR_HUMAN
```

This status may be promoted to `PRODUCTION_REFERENCE_RENDER_PASS` only after the human listening / artistic evaluation accepts the reference or after any required bounded V1 correction is accepted.
