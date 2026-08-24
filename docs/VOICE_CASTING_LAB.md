# Voice Casting Lab

Voice Casting Lab is the experimental qualification layer for synthetic voices. It belongs to Audio Engine because voice discovery, qualification and recommendation are reusable rendering capabilities. It is intentionally outside the normal production render path.

## Product invariant

A story casts a **character**, not an isolated line.

For one declared `character_id`, Audio Engine treats the provider voice as the identity anchor. Rate, pitch, volume and validated presets may vary with performance, but changing the underlying provider voice is a recast and is rejected rather than performed silently.

This gives a hard engineering guarantee: changing emotion or target metadata cannot silently replace the actor voice.

It does **not** claim that every provider voice can perform every emotion convincingly. The lab measures that expressive envelope.

## Age is a lineage problem

Age must not be simulated by a naive pitch rule. A believable age change can affect perceived pitch, stability, breath, rhythm, articulation, resonance and energy.

The lab therefore evaluates seven descriptive age stages:

- `child`
- `teen`
- `young_adult`
- `adult`
- `mature`
- `older`
- `very_old`

The current production renderer does not silently switch provider voices when a character ages. Until a lineage is explicitly qualified, a materially different age incarnation should be treated as a distinct casting decision.

Future production lineage support must be evidence-backed. A pair of voices may only be published as a validated age lineage after listening evidence supports the proposition that listeners can plausibly perceive them as the same character at different ages.

## Campaign stages

The campaign is deliberately progressive rather than a Cartesian explosion.

### 1. Fingerprint

All candidate voices read the same neutral, confidential and authoritative anchors.

Purpose:

- eliminate poor French pronunciation;
- capture baseline identity;
- detect redundant candidates;
- identify promising narrative voices.

### 2. Expressive range

Promising voices are tested against deliberately different dramatic intentions, including joy, tenderness, contained sadness, contained fear, panic, contained anger, polite threat, irony, mystery, fatigue with determination and wonder.

Purpose:

- measure what the voice can actually perform;
- identify useful limitations;
- distinguish bad artifacts from useful imperfections;
- ensure emotion does not destroy recognizability.

### 3. Age / lineage

Candidates use one age-neutral autobiographical anchor. Age suitability and cross-voice continuity are evaluated separately.

Purpose:

- estimate perceived age stage;
- identify plausible transformations of one provider voice;
- identify candidate cross-voice lineages for large time jumps.

### 4. Long form

Promising narration voices are tested on sustained prose.

Purpose:

- detect fatigue;
- detect monotony;
- measure pronunciation stability and long-form naturalness.

## Candidate discovery

Two provider discovery sets are supported.

`fr` is the conservative baseline: only voices whose provider locale starts with `fr-`.

`fr-plus-multilingual` expands the laboratory search space with every provider voice whose name contains `Multilingual`, even when its native provider locale is not French. These extra voices are **candidates only**. The engine does not assume that a multilingual model speaks French well merely because the provider labels it multilingual; French pronunciation remains an eliminatory listening gate.

This lets the lab search a much broader actor palette without weakening production quality policy.

## Evaluation dimensions

Campaign evidence may contain these dimensions:

- `french_pronunciation`
- `naturalness`
- `identity_stability`
- `acting_fit`
- `age_plausibility`
- `lineage_continuity`
- `long_form_fatigue`

Do not manufacture scores for dimensions that were not evaluated.

Human comparison should prefer pairwise or ABX judgments over arbitrary absolute scores. Examples:

- A/B: which performance better conveys contained fear?
- ABX identity: after hearing the neutral reference, does the emotional performance still sound like the same character?
- ABX lineage: is it plausible that the older voice is the same character decades later?

Automatic speaker embeddings or acoustic features may be used as laboratory pre-screen evidence, but they must not become a required runtime dependency without demonstrated product value. Objective pre-screening is never promoted as an artistic score.

## Commands

Publish the probe catalog:

```bash
audio-engine voice-lab catalog
```

Build a plan over the already validated preset palette without synthesizing audio:

```bash
audio-engine voice-lab plan --scope presets --stage fingerprint
```

Discover the French voices exposed by the current provider:

```bash
audio-engine voice-lab plan --scope provider --stage fingerprint --candidate-set fr
```

Expand discovery to French-locale plus multilingual provider voices:

```bash
audio-engine voice-lab plan --scope provider --stage fingerprint --candidate-set fr-plus-multilingual
```

Render a best-effort campaign:

```bash
audio-engine voice-lab render --scope provider --stage fingerprint --candidate-set fr-plus-multilingual --out voice-lab-output
```

The output contains `campaign.json` plus generated clips. Failures are recorded per job and do not erase successful clips.

Generate a static pairwise listening bundle from one rendered campaign:

```bash
audio-engine voice-lab pairwise voice-lab-output/campaign.json \
  --probe identity-neutral \
  --dimension french_pronunciation \
  --rounds 4 \
  --out voice-pairwise
```

The bundle contains:

- the minimal set of audio clips used by the comparisons;
- `pairwise-plan.json` with the deterministic comparison schedule;
- `index.html`, a dependency-free local player that exports `pairwise-results.json`.

By default comparisons are stratified by perceived provider gender when metadata exists, limiting an obvious source of comparison bias. `--cross-gender` disables this stratification when a global comparison is intentionally desired.

The planner does not contain a hidden winner and never converts provider metadata or acoustic pre-screening into an artistic decision.

## Provider truthfulness

The current Edge provider exposes only these performance controls through Audio Engine:

- `rate`
- `pitch`
- `volume`

The lab must not pretend that it has a native `fear`, `anger`, `sadness` or `age` control when the provider does not expose one. Dramatic probe text and tested presets are evidence-gathering mechanisms, not guarantees of acting support.

## Promotion to the production catalog

Lab candidates are not production voices merely because audio was generated.

Promotion requires, at minimum:

1. acceptable French pronunciation;
2. acceptable naturalness;
3. explicit evidence for each published character/performance claim;
4. identity-stability evidence when multiple presets are promoted for one actor voice;
5. lineage evidence before cross-voice age continuity is published.

The production `voices` catalog remains smaller than the laboratory search space by design.
