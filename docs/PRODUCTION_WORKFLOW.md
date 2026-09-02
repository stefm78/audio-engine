# Reusable Production workflow

`.github/workflows/production.yml` executes Production Manifest v1 on standard GitHub-hosted runners.

## Contract

The caller supplies one workspace-relative immutable manifest. The workflow reads the exact `engine_ref` from that manifest and checks out that commit for every render and fan-in job.

Pipeline:

```text
immutable manifest
  -> offline plan + hash verification
  -> READY units matrix
  -> render + manifest binding + automatic QA per unit
  -> complete assemblies only
  -> content-hashed assembly + automatic QA
  -> master only when the manifest declares every assembly ready
  -> optional GitHub Release only for a machine-qualified master
```

HOLD units are visible in the production plan and summary but do not prevent unrelated READY units from rendering.

A failed scene shard is recorded as evidence rather than deleting successful siblings. A block consumes only its own qualified units. Cache restores are optional acceleration and never an input authority.

## Provider behavior

The current Production runtime supports Edge. Every READY unit declares its provider explicitly.

If a manifest marks a READY unit with an unpromoted provider, the workflow fails that shard explicitly. It never substitutes Edge or any other provider.

A promoted local/ML provider must first satisfy the separate provider-package contract: model revision/integrity, runtime, voice-pack integrity, seed/parameters and explicit unavailable behavior.

## Caller example

```yaml
jobs:
  production:
    uses: stefm78/audio-engine/.github/workflows/production.yml@<exact-audio-engine-sha>
    with:
      manifest_path: series/example/production/PRODUCTION_MANIFEST.json
      artifact_prefix: example-production
      publish_release: false
```

The caller should pin the reusable workflow to the same exact Audio Engine commit stored in the manifest. This keeps orchestration and rendering code under one immutable authority.

## Evidence

Artifacts are split by retry boundary:

- `*-plan`: verified immutable plan and HOLD visibility;
- `*-unit-<id>`: scene audio/transcript/render manifest/QA + unit result;
- `*-block-<id>`: qualified block audio/assembly manifest/QA + block result;
- `*-master`: only when the entire manifest is master-ready;
- `*-summary`: consolidated machine-readable production state.

Cache entries are not evidence.

## Scene cache lifecycle

Production uses a ready-only `scene-v4` cache. `scene-v3` is intentionally quarantined and is never a restore or migration source because that generation may contain structurally READY but product-unqualified provenance. The cache is an acceleration layer; Program, voice-pack, provider-package and engine fingerprints remain the correctness authority.

On a cache miss, the workflow may migrate compatible `scene-v2` content. A caller can also opt into a pre-`scene-v2` legacy source. For recovery from a known historical source, the caller may force selected unit ids and bind that restore to an exact legacy engine commit, Program SHA-256 and historical voice-pack SHA-256.

A scene-v4 cache is saved only when the unit result is `ready`. Failed provider calls, failed QA and partial renders are never persisted as reusable scene-v4 caches.

Forced migration is a recovery mechanism, not a fallback: if the exact requested legacy source does not exist, the shard fails closed.

## Release

`publish_release: true` requires an explicit `release_tag`. Release publication is gated on a `ready` master result. A HOLD or failed unit can therefore never be silently published as a final master.


## Explicit performance providers

A character's casting identity and the provider used to perform a particular
segment are separate contracts.

Use `performance_provider` only when the product has explicitly qualified a
cross-provider performance path that preserves an already-frozen identity, for
example a local model conditioned on the frozen reference voice.

The base `provider` / preset still defines casting identity. The resolver:

- keeps one stable `casting_identity` per `character_id`;
- routes synthesis through `performance_provider` only on the declared segment;
- fingerprints both casting identity and performance-provider controls;
- still rejects any silent change of the base provider/voice identity;
- never falls back when the performance provider is unavailable.

This is not a recasting mechanism. It is an explicit, provenance-bound
performance implementation of an already-qualified identity.
