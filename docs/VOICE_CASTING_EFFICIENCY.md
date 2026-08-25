# Voice Casting Lab — efficiency funnel

Goal: spend expensive TTS generation and human listening only on character voices that are already plausibly distinguishable.

## Governing principle

Speaker recognizability is a casting constraint, not merely a synthesis-quality metric. A character candidate that is acoustically too close to another cast member should be rejected before broad emotion or long-form testing.

## Funnel

1. **Designed contrast** — candidate descriptions deliberately separate pitch range, resonance, grain, articulation, pace and energy while remaining natural.
2. **Cheap acoustic pre-filter** — `voice_casting_distance.py` compares anchor WAVs using F0, duration, energy, zero-crossing rate and a lightweight spectral-shape proxy. It adds no model or runtime dependency.
3. **Tiny blind human identity gate** — only survivors are compared by ear. Human listening remains authoritative.
4. **Expressive campaign** — only identity-qualified pairs proceed to emotion breadth, endurance and eventually age-lineage experiments.

## Relative gate, not universal threshold

The current Claire/Lucie pair is a known-confusable baseline. New casting pairs should be materially farther apart than that baseline rather than relying on an invented universal numerical identity threshold.

Default pre-filter requirement:

- candidate distance >= 1.35 × known-confusable baseline, and
- candidate distance >= baseline + 8 score points.

These values are screening policy, not claims about speaker-recognition accuracy. They can be recalibrated from accumulated human ABX evidence without changing production audio behavior.

## Non-claims

The acoustic score does **not** qualify speaker identity, French quality, acting, age lineage or production readiness. It may only reject candidates early. Production Edge remains unchanged.
