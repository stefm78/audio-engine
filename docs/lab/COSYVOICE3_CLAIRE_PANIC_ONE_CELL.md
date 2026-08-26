# CosyVoice3 Claire panic one-cell

Lab-only scientific killer. No Production, Edge or Pages change.

## Frozen cell

- Architecture: `Fun-CosyVoice3-0.5B-2512`, `inference_instruct2`.
- Code: `074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc`.
- Model: `29e01c4e8d000f4bcd70751be16fa94bf3d85a18`.
- Preflight model-manifest SHA-256: `7869bdfc4d50036c6a9a87dcd16fc979e1f37b9ffc007172264cea9c102282e8`.
- Target identity: Claire.
- Prompt WAV: immutable `reference-claire.wav`, SHA-256 `3366f993d108f42525627f1be03e71fdec312b559e067616d2019b69da35cafe`.
- Text: `Vite ! Ils arrivent ! Fermez la porte !`.
- Instruction: `You are a helpful assistant. Please say this sentence with intense, urgent panic and fear.<|endofprompt|>`.
- Seed: `0`.
- Speed: `1.0`.
- Stream: `false`.
- Text frontend: `false`.
- CPU, fp16 false.
- Exactly one render.
- No training, finetuning, retry, substitution, alternate reference, reference search, parameter search or tuning.

## Fixed gates

1. Technical: native 24 kHz, finite, non-silent, duration ratio 0.5–1.5 against immutable source.
2. Independent WeSpeaker ResNet34 ONNX: Claire similarity must exceed Lucie similarity; no absolute threshold.
3. Whisper Small French: WER must be no worse than immutable source WER 0.5.
4. Source-relative SUPERB: output must be closer to immutable panic than immutable contained sadness.

Any semantic FAIL retires this direct architecture without rescue. Only a full machine PASS authorizes a separate blind human gate. This documentation commit also causes a PR synchronization event after the new workflow already exists on the branch; it does not change the frozen scientific cell.
