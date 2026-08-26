# OpenVoice V2 CPU one-cell smoke — frozen protocol

Active resource-safe successor after the RVC path reached an unavailable CUDA boundary.

## Scope

Exactly one direct tone-color conversion on GitHub-hosted CPU:

- expressive source: immutable Claire panic WAV;
- target identity reference: immutable Lucie neutral reference;
- OpenVoice code revision: `74a1d147b17a8c3092dd5430504bd83ef6c7eb23`;
- OpenVoice V2 converter revision: `fd981100305a0e4291f93a9ad169c6d9f7bed54a`;
- converter checkpoint SHA-256: `9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e`;
- direct whole-WAV speaker embedding extraction; no VAD;
- upstream default `tau=0.3`;
- fixed torch seed `0`;
- watermark disabled;
- no new TTS, no training, no retry, no substitution, no parameter/reference search.

## Staged killer

1. Technical integrity.
2. Independent WeSpeaker target identity: Lucie must rank above Claire, no absolute threshold.
3. French/content: exact pinned Whisper Small output WER must be no worse than the immutable source baseline WER `0.5`.
4. Source-relative emotion: exact pinned source-valid SUPERB output profile must be closer to the immutable panic-source profile than to the immutable contained-sadness profile.

Any scientific failure retires this direct OpenVoice path without `tau`, seed, VAD, source, target-reference, or checkpoint tuning.

Only a full one-cell PASS authorizes the exact same fixed transform on the four-cell panic/sadness × Claire/Lucie matrix. Human listening remains unauthorized until the matrix passes.
