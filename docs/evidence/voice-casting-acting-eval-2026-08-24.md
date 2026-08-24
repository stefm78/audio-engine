# Voice casting acting evidence — 2026-08-24

This record summarizes one complete blind human evaluation of the 15-voice acting shortlist. It is evidence from one evaluator, not production truth.

## Result

- 56 acting comparisons were completed.
- 37/56 comparisons (66.1%) were `reject-both`.
- Only 19/56 comparisons produced a usable winner or tie.
- Long-form narration was materially stronger: 5/7 comparisons produced an accepted winner.
- The previous identity ABX experiment was 46/46 correct across panic and tenderness, so recognizability is not the observed bottleneck.

## Expressive envelope observed

| Intention | Accepted comparisons | Evidence |
| --- | ---: | --- |
| Tenderness | 5/7 | Eloise, Thalita and Henri won comparisons |
| Panic | 1/7 | Fabrice only |
| Contained anger | 3/7 | Ava and Fabrice won; one tie |
| Mystery | 1/7 | Thalita only |
| Joy | 3/7 | Vivienne and Giuseppe won; one tie |
| Polite threat | 2/7 | two ties, no winner |
| Fatigue + determination | 3/7 | Vivienne, Eloise and Giuseppe |
| Wonder | 1/7 | Fabrice only |
| Long-form narration | 5/7 | Vivienne, Ariane, Charline, William and Remy |

## Engineering interpretation

The experiment falsifies a tempting assumption: a large voice catalog plus emotional text does not by itself create a convincing synthetic acting system.

For the current Edge path, the limiting factor is now **direction capability**, not character identity. Edge remains useful for neutral narration and some voice-specific intentions, but we must not publish a broad emotional capability map from the current probes.

## Next experiment

Before introducing another production dependency, run a small direction-treatment experiment on a representative set of voices:

- keep provider voice identity fixed;
- keep the semantic text fixed;
- vary only currently supported controls (`rate`, `pitch`, `volume`);
- target the weakest intentions first: panic, mystery, polite threat and wonder;
- compare every treatment against the current baseline and allow `none acceptable`.

If those controls do not materially improve acceptance, the laboratory should benchmark a provider with **native expressive controls**. Microsoft Azure Speech is one candidate because its supported voice subsets can expose `mstts:express-as` speaking styles, style degree and roles; that capability must be benchmarked rather than assumed and must remain optional until it demonstrates material product value.

## Promotion rule

No generic claim such as `voice X supports panic` may enter the production catalog from this evidence alone. Only the tested winning cases are positive evidence, and the high `reject-both` rate must remain visible to future casting decisions.
