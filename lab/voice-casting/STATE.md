# Voice Casting Lab state

Date: 2026-08-28

Status: **CAPABILITY GAP / WATCH**

Production status: **ACTIVE / UNAFFECTED**

Production voice provider: **Edge TTS**

NUC capability status: **CHARACTERIZED**

NUC real TTS integration smoke: **PASS**

## Scientific diagnosis

Repeated experiments establish that:
- French can be preserved;
- speaker identity can be preserved;
- moderate expressivity can be produced;
- convincing high-arousal panic remains the missing independent degree of freedom.

Increasing speaker conditioning or generic low-dimensional affect control has not solved that gap reliably.

No currently qualified public/permissive model is authorized for another scientific cell solely by retuning an already-tested family.

## Current work

The Intel NUC8i7HVK characterization is complete.

Verified Lab execution envelope includes:
- Core i7-8809G, 32 GB RAM;
- Radeon RX Vega M GH, 4 GB HBM2;
- Windows native as the preferred host;
- PyTorch CPU PASS;
- ONNX Runtime CPU PASS;
- strict DirectML PASS;
- OpenVINO CPU and Intel iGPU PASS;
- Vulkan/GGUF on Vega PASS, with full offload proven through a 3.40B Q4 model;
- real French voice-cloning TTS smoke PASS through MOSS-TTS-Nano ONNX Runtime CPU.

See:
- `docs/evidence/nuc-voice-lab-capability-2026-08-28.md`.

The NUC changes resource feasibility only.

Scientific rejects remain closed.

A previous resource reject may be reconsidered only when its actual upstream stack maps to a proven NUC backend and still satisfies the Lab's French, arbitrary-speaker, independent-emotion and licensing gates.

No NUC result may become a Production dependency.

## Immutable references

The four frozen Voice Lab WAV references are cached locally on the NUC in a persistent read-mostly area and were verified byte-for-byte against their expected SHA-256 values.

The NUC is not the sole canonical archive.

Issue #174 remains open until an independent durable archive is recorded.

## Runner security decision

The public `stefm78/audio-engine` repository must not directly expose a persistent self-hosted NUC runner to untrusted public PR/fork execution.

Current preference:
1. local/manual Lab execution as the safe baseline;
2. future private control-plane -> NUC -> exact `audio-engine` commit SHA;
3. direct public-repo self-hosted runner rejected by default.

No runner implementation is required for the completed capability characterization.

## Authoritative evidence

See:
- `docs/evidence/voice-casting-capability-gap-2026-08-28.md`;
- `docs/evidence/nuc-voice-lab-capability-2026-08-28.md`;
- closed-unmerged PRs referenced by the capability-gap evidence file.

## Next action

Do not run more generic NUC benchmarks.

Perform a read-only reassessment of previous **resource rejects** against the proven NUC backend envelope.

Only if a candidate now has a concrete supported runtime path and still passes the scientific admission gates should one cheap resource/API preflight be opened.

## Production rule

Audioguide, audiobook and learning-kit rendering must continue independently of Voice Lab progress or failure.
