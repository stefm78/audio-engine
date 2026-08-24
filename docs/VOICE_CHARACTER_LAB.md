# Frozen character packs — Voice Casting Lab

Status: experimental only. This contract does not alter the production renderer.

## Why this exists

The Qwen3 x-vector experiments established a useful separation between speaker identity and line performance. The practical requirement is therefore not “pick a voice for every line”; it is “freeze a character once, then render many lines without silently recasting that character.”

A character pack is the smallest durable object that represents that promise.

## Pack contents

A pack contains exactly two durable files:

- `character.json` — the identity contract;
- `anchor.wav` — one already approved identity anchor.

The pack does **not** generate its own anchor. `freeze_character_identity(...)` copies an existing approved WAV, computes its SHA-256 and records it. If the destination already contains a character pack, replacement is refused rather than performed silently.

Example shape:

```json
{
  "schema": "audio-engine-character-lab-v1",
  "character_id": "claire",
  "provider": "qwen3-xvector-lab",
  "identity_mode": "x_vector_only",
  "language": "French",
  "base_seed": 20260824,
  "anchor": {
    "file": "anchor.wav",
    "sha256": "...64 hex characters...",
    "regeneration": false
  },
  "source": {
    "qualification_issue": 65
  },
  "claims": {
    "stable_character": true,
    "age_lineage": false,
    "production_promoted": false
  }
}
```

## Fail-closed identity rules

Identity integrity is stricter than line-generation availability.

Before any heavy model is initialized:

1. schema and provider must be the qualified Lab values;
2. `identity_mode` must be exactly `x_vector_only`;
3. the anchor must remain inside the pack;
4. anchor regeneration must be explicitly `false`;
5. the anchor SHA-256 must match exactly;
6. the contract may not claim age-lineage or production promotion.

The hash is checked again after all line renders. If it changed, the render is rejected because its identity evidence is no longer trustworthy.

There is no fallback to another speaker, provider or anchor.

## Best-effort line rendering

Once identity has passed the fail-closed gate, individual synthesis failures are treated differently. A failed line is recorded in `manifest.json`, later lines continue, and the overall status becomes `partial` when at least one line succeeded.

This distinction is intentional:

- **identity uncertainty** can silently corrupt a character and therefore aborts;
- **one bad generated line** is visible and repairable and therefore must not erase an otherwise usable batch.

One reusable Qwen3 identity prompt is built per character render. Per-line seeds are deterministic from the character, line id and text unless an explicit seed is provided.

## What qualification currently supports

Evidence on 2026-08-24 supports the following Lab claim for Qwen3 Base x-vector-only:

- strong French acting signal on the tested hard intentions;
- no French veto in the qualified x-vector trials;
- identity result `3/4` in the initial killer followed by the predeclared independent high-arousal confirmation at `2/2`.

That is sufficient to experiment with frozen characters in the Lab.

It does **not** establish:

- production readiness;
- age continuity;
- arbitrary emotion coverage;
- long-form fatigue performance;
- a guarantee that every generated take is artistically acceptable.

## Storage direction

Generated audio and character anchors should stay out of the source repository. A later product integration can place character packs in a private/protected asset source or durable release artifact and refer to them by immutable digest. The source repository should retain contracts, code and qualification receipts rather than generated media.
