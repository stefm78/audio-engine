# Voice Casting Lab state

Date: 2026-08-28

Status: **CAPABILITY GAP / WATCH**

Production status: **ACTIVE / UNAFFECTED**

Production voice provider: **Edge TTS**

## Scientific diagnosis

Repeated experiments establish that:
- French can be preserved;
- speaker identity can be preserved;
- moderate expressivity can be produced;
- convincing high-arousal panic remains the missing independent degree of freedom.

Increasing speaker conditioning or generic low-dimensional affect control has not solved that gap reliably.

No currently qualified public/permissive model is authorized for another scientific cell solely by retuning an already-tested family.

## Current work

A local Intel NUC8i7HVK is being characterized as an optional Voice Lab executor:
- Core i7-8809G;
- 32 GB RAM;
- Radeon RX Vega M GH, 4 GB HBM2;
- Linux host under characterization.

This work may reopen candidates previously rejected **only for resource feasibility**.

Scientific rejects remain closed.

No NUC result may become a Production dependency.

## Runner security decision

The public `stefm78/audio-engine` repository must not directly expose a persistent self-hosted NUC runner to untrusted public PR/fork execution.

Current preference:
1. local/manual Lab execution as the safe baseline;
2. future private control-plane -> NUC -> exact `audio-engine` commit SHA;
3. direct public-repo self-hosted runner rejected by default.

Concrete NUC runner/backend implementation remains pending the final `NUC_VOICE_LAB_CAPABILITY_MANIFEST`.

## Authoritative evidence

See:
- `docs/evidence/voice-casting-capability-gap-2026-08-28.md`;
- closed-unmerged PRs referenced by that evidence file.

## Production rule

Audioguide, audiobook and learning-kit rendering must continue independently of Voice Lab progress or failure.
