# Voice Casting Lab — initial provider scan (2026-08-24)

## Purpose

Establish the first reproducible evidence set for French-language TTS voice casting without promoting unverified artistic scores.

## Provider scope

The Edge provider exposed 13 French-language voices across `fr-FR`, `fr-BE`, `fr-CH`, and `fr-CA` at campaign time.

## Campaign evidence

| Stage | Run | Candidates | Probes / candidate | Rendered | Failures | Artifact |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| fingerprint | `32705337262` | 13 | 3 | 39 | 0 | `voice-casting-provider-fingerprint` |
| expressive | `32705582534` | 13 | 11 | 143 | 0 | `voice-casting-provider-expressive` |
| age-lineage anchor | `32705905602` | 13 | 1 | 13 | 0 | `voice-casting-provider-age` |
| long-form | `32706158499` | 13 | 1 | 13 | 0 | `voice-casting-provider-long-form` |

Total: **208 rendered clips, 0 synthesis failures**.

## What this evidence proves

- current French provider voice discovery is reproducible;
- all discovered candidates can pass the current generation harness;
- identity, expressive, age-lineage and endurance probes are materialized separately;
- the same provider voice can now be evaluated across several narrative intentions;
- campaign artifacts are retained outside the repository rather than committing generated media.

## What this evidence does not prove

- it does not prove that a voice convincingly expresses the named emotion;
- it does not assign perceived age from pitch or provider metadata;
- it does not validate cross-voice age lineage;
- it does not rank naturalness, acting quality or character credibility automatically.

The current Edge adapter exposes `rate`, `pitch`, and `volume`, not a native emotion control. Expressive probes therefore test the delivery elicited by the text and punctuation with the provider voice held constant.

## Promotion rule

No new artistic voice profile or age-lineage relationship is promoted from this scan alone. Promotion requires listening evidence, preferably pairwise or ABX, with linguistic quality remaining an eliminatory gate.
