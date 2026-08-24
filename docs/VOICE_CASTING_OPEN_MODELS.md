# Open/local expressive TTS challengers

Status: Voice Casting Lab research only.

## Arbitration — 2026-08-24

The current Edge path remains the production reference because it is simple, reliable and already validated for narration/identity. Human listening showed that rate/pitch/volume alone does not reliably produce acting on hard intentions, so open/local expressive models are evaluated as challengers.

### 1. Chatterbox Multilingual V3 — first killer test

Why first:

- MIT code/model distribution;
- current multilingual V3 explicitly supports French;
- 0.5B multilingual T3 family;
- zero-shot voice cloning from a reference clip;
- local CPU path exists, although GPU is preferable;
- simpler experimental integration than CosyVoice;
- no cloud credentials or per-character pricing.

Important limitation: `exaggeration` is an intensity-style scalar, not a semantic acting instruction such as fear, restrained anger or mystery. Earlier multilingual Chatterbox versions also had community reports that exaggeration produced little perceptual effect. V3 claims improved expressive generation, so this must be measured rather than assumed.

The first experiment is intentionally tiny: one synthetic French reference identity (Edge Vivienne), two hard intentions (panic and mystery), and four blind options per intention: Edge baseline plus three Chatterbox V3 configurations. Chatterbox remains an optional lab dependency and is not added to `pyproject.toml`.

### 2. CosyVoice 3 — semantic challenger if needed

CosyVoice 3 remains the strongest next candidate when semantic instruction following is required. The public 0.5B model is Apache-2.0 and the family supports multilingual / zero-shot / instruction-oriented inference. It is not first because its installation/deployment surface is significantly heavier (repository/submodules, normalization/runtime tooling and a larger operational envelope).

### 3. Parler-TTS Multilingual — descriptive-style challenger

Parler-TTS Multilingual remains useful because speaking style is described in natural language and the model/code are permissively licensed. The current multilingual mini checkpoint is ~0.9B / ~3.75 GB and older than the other two candidates, so it is a second-line research option rather than the first integration.

## Governance

No open model is promoted by benchmark generation alone. Promotion requires human listening evidence for:

1. French pronunciation;
2. naturalness;
3. identity continuity;
4. acting fit on difficult intentions;
5. long-form fatigue;
6. operational simplicity/reliability;
7. reproducible provenance and graceful fallback.

Heavy ML dependencies stay outside the production Audio Engine dependency graph unless a later promotion decision explicitly changes that boundary.
