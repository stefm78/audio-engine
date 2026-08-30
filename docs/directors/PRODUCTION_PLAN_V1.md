# Production Plan v1 — consumer authoring contract

Production Plan v1 is the common **consumer-side** authoring shape for Audioguide and Audiobook Production Directors.

It is not an Audio Engine runtime schema and it is never passed directly to `audio-engine render`.

The flow is:

```text
Production Plan v1
       |
consumer/director compilation
       |
Audio Engine Program v1..v6
       |
validate -> preflight -> probe if needed -> render
```

## Design rule

Store a decision in the Production Plan only when the production director needs to preserve or reason about it.

Do not mirror low-level Audio Engine fields merely because they exist.

## Content binding

Production Plan v1 supports two consumer-side content binding modes.

### `inline` — default and backward-compatible

If `content_binding` is absent, the plan is `inline`.

The Production Plan owns the authored spoken content. Its `beats` contain exact speaker/text and a deterministic consumer adapter may compile them into a Program.

This is appropriate for small or newly authored units.

### `program-ref` — existing or long-form canonical content

Use an explicit binding:

```json
{
  "content_binding": {
    "mode": "program-ref",
    "program": "relative/path/to/program.json",
    "git_blob_sha1": "<exact Git blob SHA>",
    "content_authority": "program"
  }
}
```

The referenced Program is the single text/audio-execution authority.

A `program-ref` plan:

- **must not duplicate spoken text**;
- may use `overlays` anchored to one-based Program segment ranges;
- preserves exact Program voice, timing, acoustic-space and soundscape decisions unless an explicit later production decision changes them;
- may identify casting continuity with a consumer `program_selector` such as a Program preset or character id rather than forcing one new preset over all referenced segments;
- records importance, performance intent, fallback and risk policy without becoming a second Program.

This is the preferred mode for migration and long-form work.

The Git blob SHA is a cheap drift guard. If the referenced Program bytes change, the plan must be deliberately reviewed/rebound rather than silently following different content.

## Common shape

Required top-level fields:

| Field | Meaning |
| --- | --- |
| `production_plan_version` | exactly `1` |
| `product` | `audioguide` or `audiobook` |
| `id` | stable consumer production-unit id |
| `title` | human-readable unit title |
| `language` | content language, currently `fr-FR` for these fixtures |
| `objective` | what the unit must make the listener understand or feel |
| `casting` | role continuity plus either inline preset choice or program-ref selector |
| `beats` / `overlays` | `beats` for inline authored speech; `overlays` for program-ref production annotations |
| `fallback_policy` | what to do when essential/supportive/optional material cannot be produced |
| `risk_hints` | explicit hints used by the director to select a representative probe |
| `product_context` | profile-specific metadata that remains outside Audio Engine |

In `inline` mode, a beat contains:

- `id`;
- `speaker`, resolved through `casting`;
- exact `text`;
- `importance`: `essential`, `important`, `supportive`, or `optional`;
- `performance_intent`: semantic direction retained by the consumer;
- `sound_recipe`: a recipe id from `docs/PRODUCTION_RECIPES.md`;
- optional `recipe_params` when that recipe requires an explicit installed capability id.

## Casting

In `inline` mode, `casting.<role>.preset` is allowed because voice presets are part of the published Audio Engine capability surface.

In `program-ref` mode, casting may instead carry a `program_selector` that identifies already-authored Program voice/character material. The Production Plan must not normalize away deliberate per-segment voice/rate/pitch differences merely to fit one preset.

`continuity_key` is consumer metadata. It lets a director preserve the same role across stations/chapters without teaching the renderer about books, routes, or characters outside the current Program.

## Fallback policy

The common vocabulary is deliberately small:

- `fail`;
- `omit-and-warn`;
- `continue-without`.

The accepted reference principle remains:

> fail cheap before commitment; after commitment, finish robustly when the missing element is non-essential.

## Product context

`product_context` is intentionally profile-owned.

Audioguide context is documented in [AUDIOGUIDE_PROFILE.md](AUDIOGUIDE_PROFILE.md).

Audiobook context is documented in [AUDIOBOOK_PROFILE.md](AUDIOBOOK_PROFILE.md).

Product context must not be copied into the Audio Engine Program unless a reusable audio-rendering capability independently requires it.

## No silent field loss

Every worked fixture has a `*.disposition.json` companion.

Every leaf field in the Production Plan must be classified exactly once as:

- `program` — compiled into a Program field or deterministic Program-shape decision;
- `consumer_metadata` — intentionally retained outside Audio Engine;
- `unsupported` — explicitly rejected with a reason.

The repository test suite verifies exact leaf coverage.

For inline fixtures it also checks the compiled Programs with both `validate_program()` and offline `preflight_program()`.

For program-ref fixtures it verifies the exact referenced Program Git blob, validates/preflights that Program offline, verifies overlay bounds/selectors, and proves that no spoken `text` is duplicated in the plan.

## Compiler decision

For v1, **no common runtime compiler is introduced**.

Reason:

- the shared inline mechanical mapping (id/title/language, beat text, speaker -> preset) is trivial;
- program-ref deliberately preserves an existing Program rather than asking a generic compiler to rewrite it;
- the useful differences are product-side policy and metadata;
- performance intent and recipe selection are authorial/director decisions, not renderer inference;
- encoding those policies in a generic compiler now would create an unnecessary second orchestration layer.

Consumers may implement small deterministic adapters using these fixtures as executable examples. A shared compiler can be reconsidered only after at least one real Audioguide and one real Audiobook production expose duplicated deterministic logic worth centralizing.

Status:

```text
PRODUCTION_PLAN_CORE_DEFINED
COMPILER_DECISION_RECORDED = NO_COMMON_COMPILER_YET
```
