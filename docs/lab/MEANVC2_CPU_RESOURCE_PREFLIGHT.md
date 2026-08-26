# MeanVC2 CPU resource preflight

Status: Lab-only infrastructure/resource gate. This document does not authorize a scientific voice-conversion result, human listening, Production, Edge, or Pages changes.

## Why this gate exists

The previous RVC path reached a CUDA boundary that was not checked early enough. MeanVC2 is therefore not allowed to enter a scientific killer until the exact next experiment is proven executable using project-accessible resources.

## Frozen upstream

- code repository: `ASLP-lab/MeanVC2`
- Git revision: `0d39c8ae416a37edb9884db67334e4b9d0c3e308`
- upstream declares Apache-2.0 in the pinned README and model card; the Git repository does not contain a standalone LICENSE file, so this remains Lab-only provenance until clarified.
- Hugging Face model repository: `ASLP-lab/MeanVC2`
- pinned model snapshot: `4a73815c6b392bcb435769f69d7f5fdeccbc39dd`
- quality model: `meanvc2_120ms_40ms.safetensors`
- published model SHA-256: `04ea21a4fb55400469e6004ae842c3e7f059f759e92946fb95123418cad5d818`
- published model size: `70839448` bytes
- published vocoder SHA-256: `df1f2ba9f7ac35c96832579421ee1ed913a68c3a1d2f8a6536739f902f194a93`
- published vocoder size: `33223674` bytes
- ASR asset: `fastu2pp_160ms.pt`; exact SHA is frozen from the first successful resource preflight before any scientific render.
- WavLM base: Microsoft public `WavLM-Large.pt`; exact SHA is frozen from the first successful resource preflight.
- WavLM ECAPA fine-tune public Google Drive file id: `1-aE1NfzpRCLxA4GUxX9ITI3F9LlbtEGP`; exact SHA is frozen from the first successful resource preflight.

## Resource contract

The resource preflight must run on a standard GitHub-hosted CPU runner. It may download public artifacts but may not require:

- CUDA or another accelerator;
- a paid GPU service;
- a private Hugging Face token;
- a Google account;
- a user-supplied file;
- manual browser interaction.

It must prove all of the following before scientific work:

1. the exact Git revision is available;
2. the exact pinned Hugging Face VC model and vocoder are downloadable and match the published hashes;
3. the 160 ms Fast-U2++ asset is downloadable and hashed;
4. WavLM-Large is downloadable from Microsoft's public release and hashed;
5. the WavLM fine-tuned speaker checkpoint is downloadable non-interactively and hashed;
6. the CPU PyTorch runtime and MeanVC2 E2E imports load successfully;
7. the JIT ASR and Vocos files load on CPU;
8. the speaker encoder can be instantiated on CPU with the downloaded WavLM assets;
9. peak disk/RAM/runtime evidence is retained.

Any failure here is infrastructure/resource evidence only. It cannot be interpreted as a voice-quality failure and cannot trigger parameter tuning.

## Scientific contract reserved for the next gate

Only a successful resource preflight may authorize one immutable killer cell:

- source: existing Claire panic WAV, SHA-256 `ac92fd1f8346b981ac7518e1e698cf8b1c31a96dff069ad60a2d017a17ff9d7f`;
- target: existing Lucie reference WAV, SHA-256 `9e5ff59c1b2993b249851bfd3a9f8e78047fd5afd93b034392df1977ae54c822`;
- MeanVC2 quality preset `120ms`, upstream chunk size `12`, `steps=3`;
- device `cpu`;
- seed `0`, fixed before rendering;
- no training, finetuning, retries, alternative references, substitutions, or parameter search;
- gate order: technical -> independent WeSpeaker target identity -> exact Whisper French no-worse-than immutable source -> source-relative SUPERB panic preservation.

If that future one-cell smoke fails any scientific gate, direct zero-shot MeanVC2 is retired without tuning. If it passes all gates, only the exact four-cell matrix is authorized next.