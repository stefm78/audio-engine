# Voice catalog and recommendation policy

Audio Engine separates two questions that must not be confused:

1. **Is the voice linguistically good enough?**
2. **Is the voice/preset a good fit for the requested role?**

The first question comes from the initial blind French benchmark. The second comes from the subsequent casting experiments.

## Quality gate

The initial benchmark compared French voices reading the same difficult French text before their identity was revealed. The review order was:

1. French pronunciation — eliminatory;
2. fluency and prosody;
3. naturalness / absence of synthetic effect;
4. narrative or storyteller potential.

A voice that sounds attractive but deforms French should not be promoted merely because it matches a character archetype.

The engine deliberately does **not** publish invented historical aggregate scores. It publishes the tested criteria and the presets that were retained through human listening.

## Casting model

After the linguistic-quality gate, presets can be ranked against a target profile. The current target dimensions are:

- `gender`;
- `age` (`child`, `young_adult`, `adult`, `older`);
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

The result includes the target, quality-validation policy, scoring rules, and the top presets with their provider voice, rate, pitch, volume, traits, tags, and score.

A recommendation is advisory. A consumer may still specify an explicit `preset` or provider `voice` in its program.

## Why this belongs in Audio Engine

Voice selection is part of the reusable audio-rendering capability, not a property of Audioguide or Learn-it. Consumers describe the desired vocal role; Audio Engine publishes the available validated palette and proposes candidates consistently.
