# Voice Casting Lab

The Voice Casting Lab is the research lane for improving character voices without putting Production audio rendering at risk.

## Boundary

Production and Lab share this repository because eventual promotion must stay compatible with the same Audio Engine contracts, manifests and rendering semantics.

They do **not** share runtime availability requirements.

Production:
- authority: `main` or an explicitly pinned Production tag/SHA;
- current TTS provider: Edge;
- consumers: audioguides, audiobooks and learning kits;
- must remain usable when every Lab machine, model and cache is offline.

Lab:
- research only;
- may use GitHub-hosted CPU, local/manual execution or a separately governed private control-plane;
- may install heavy experimental ML dependencies outside the Production dependency graph;
- may keep model caches outside disposable experiment workspaces;
- produces evidence, never an automatic provider promotion.

## Current scientific state

See [`STATE.md`](STATE.md).

The current unresolved target is:

> French + immediately recognizable character identity + convincing high-arousal fear/panic, with speaker identity and emotion independently controllable.

The frozen one-cell protocol and the current capability-gap evidence are recorded in
[`docs/evidence/voice-casting-capability-gap-2026-08-28.md`](../../docs/evidence/voice-casting-capability-gap-2026-08-28.md).

## Execution policy

A new candidate is admitted only after a cheap resource/API preflight.

Scientific experiments remain frozen:
- exact model/code/weights;
- exact references and text;
- exact seed/settings;
- one render;
- no best-of-N;
- no seed search;
- no post-result tuning or rescue.

The NUC is being characterized as an **optional Lab executor**. Its final backend/runtime configuration is not part of Production and must not be assumed until the separate capability manifest is complete.

Because this repository is public, the NUC must not be attached as an unrestricted persistent self-hosted runner. Preferred future topology is local/manual execution or a private Lab control-plane that checks out an exact immutable `audio-engine` SHA.

## Evidence lifecycle

Historical experiment branches and specialized workflows are not the scientific archive.

Before branch/workflow deletion:
1. preserve the authoritative verdict;
2. preserve exact PR/HEAD/run/artifact identifiers and cryptographic hashes where relevant;
3. preserve immutable reference hashes;
4. record the reopen condition;
5. only then remove obsolete execution scaffolding.

Closed-unmerged PRs and durable evidence records remain traceability anchors.

## Promotion

A Lab result cannot modify Production implicitly.

Promotion requires an explicit decision demonstrating at minimum:
- natural French;
- character identity continuity;
- acting quality;
- reproducibility;
- acceptable licensing;
- acceptable operational behavior;
- compatibility with the reusable Audio Engine contract.

Until that gate is passed, Edge remains Production.
