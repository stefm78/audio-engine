# Voice catalog and recommendation policy

Audio Engine separates questions that must not be confused:

1. **Is the voice linguistically good enough?**
2. **Is the voice/preset a good fit for the requested role?**
3. **Does a character remain recognizably the same across performances?**
4. **Can two age incarnations plausibly belong to the same character?**

The first question comes from the initial blind French benchmark. The second comes from casting experiments. The last two belong to Voice Casting Lab evidence and must not be inferred from labels alone.

## Quality gate

The initial benchmark compared French voices reading the same difficult French text before their identity was revealed. The review order was:

1. French pronunciation — eliminatory;
2. fluency and prosody;
3. naturalness / absence of synthetic effect;
4. narrative or storyteller potential.

A voice that sounds attractive but deforms French should not be promoted merely because it matches a character archetype.

The engine deliberately does **not** publish invented historical aggregate scores. It publishes the tested criteria and the presets that were retained through human listening.

## Identity-first casting

A declared `character_id` is cast as a character, not as a sequence of unrelated lines.

The underlying provider voice is the current identity anchor. Once a character has spoken, later segments may change rate, pitch, volume or use another validated preset based on the **same provider voice**, but Audio Engine rejects a silent switch to a different provider voice.

This gives a deterministic engineering guarantee that an emotion or a changed target cannot silently recast the character.

It does not guarantee that the provider voice performs every requested emotion well. Voice Casting Lab measures that expressive envelope.

## Age

The descriptive age vocabulary is:

- `child`;
- `teen`;
- `young_adult`;
- `adult`;
- `mature`;
- `older`;
- `very_old`.

Age suitability and character continuity are separate properties. A voice may be an excellent older voice but a poor older incarnation of a particular younger character.

Audio Engine therefore does not implement automatic cross-voice ageing. Cross-voice age lineages require explicit laboratory evidence before they may become production catalog relationships. See [`VOICE_CASTING_LAB.md`](VOICE_CASTING_LAB.md).

## Casting model

After the linguistic-quality gate, presets can be ranked against a target profile. The current target dimensions are:

- `gender`;
- `age`;
- `energy` 1–5;
- `authority` 1–5;
- `warmth` 1–5;
- `darkness` 1–5;
- `proximity` 1–5;
- free-form `tags`.

The scoring rules are published by the engine itself:

```bash
audio-engine voices
```

Lower scores are better. A gender mismatch receives a strong penalty; age distance receives a class-based penalty; numeric traits use weighted squared distance; matching tags reduce the score.

## Recommendations

Example:

```bash
audio-engine recommend --target '{"gender":"male","age":"adult","energy":5,"authority":3,"warmth":4,"tags":["narrateur","vif"]}'
```

The result includes the target, quality-validation policy, identity-first casting policy, scoring rules, and the top presets with their provider voice, rate, pitch, volume, traits, tags, and score.

A recommendation is advisory. A consumer may still specify an explicit `preset` or provider `voice` in its program, subject to character identity continuity when the same `character_id` is reused.

## Voice Casting Lab

The lab can inspect the validated preset palette or discover the French voices exposed by the current provider, then plan or render reproducible audition campaigns:

```bash
audio-engine voice-lab catalog
audio-engine voice-lab plan --scope provider --stage fingerprint
audio-engine voice-lab render --scope presets --stage expressive --out voice-lab-output
```

The lab is evidence gathering, not the production catalog. A generated clip is not automatically a validated voice capability.

## Why this belongs in Audio Engine

Voice selection, identity continuity and voice qualification are reusable audio-rendering capabilities, not properties of Audioguide or Learn-it. Consumers describe the desired vocal role and stable character identity; Audio Engine publishes the available validated palette and proposes candidates consistently.
