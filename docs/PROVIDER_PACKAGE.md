# Promoted local-provider package v1

A local or ML TTS provider is not a Production capability merely because a laboratory probe rendered successfully.

Before Production may select it, a consumer must provide an immutable provider package containing:

- provider id and implementation version;
- exact Python/runtime dependency contract;
- exact upstream Git revisions where dependencies are revision-pinned;
- model identity and revision;
- SHA-256 integrity records for model material;
- the exact Production voice-pack SHA-256;
- deterministic seed and synthesis parameters;
- SHA-256 for every conditioning/reference asset;
- `fallback: "fail"`.

No silent fallback is representable.

The package validator is generic and does not download models. Cache/model acquisition is an execution concern; correctness is established by the declared revision/integrity contract and verified material when available.

```bash
audio-engine provider-package validate provider-package.json
audio-engine provider-package validate provider-package.json \
  --verify-files --workspace-root . --voice-pack voices/production.json
```

A future provider adapter may consume this package only after its runtime implementation is promoted. Passing this contract does not itself constitute artistic or human approval.

## Hydration is separate from synthesis

Production execution is deliberately split into observable phases:

1. install the exact promoted runtime;
2. hydrate the exact model revision;
3. verify every declared model SHA-256;
4. hydrate conditioning/reference assets;
5. verify every reference SHA-256;
6. instantiate the local provider;
7. synthesize with network model resolution disabled.

A cache may avoid repeating hydration, but it never relaxes integrity checks and is never required for correctness.

```bash
audio-engine provider-package hydrate-model provider-package.json \
  --cache-root generated/provider-models
audio-engine provider-package hydrate-references provider-package.json \
  --workspace-root .
audio-engine provider-package validate provider-package.json \
  --verify-files --workspace-root . --voice-pack voices/production.json
```

Reference sources may be:

- `github_release`: one Release asset whose SHA-256 is the reference SHA;
- `github_release_archive`: a hash-locked Release archive plus an exact member basename.

For archive references, Production verifies the archive SHA-256 first, requires the requested regular-file basename to resolve exactly once, extracts only that member, and then verifies the reference SHA-256. This permits reuse of immutable reference packs without republishing or duplicating individual reference assets.

## Promoted adapter boundary

The provider package is data. An id is executable only when `audio-engine` also contains a promoted adapter and runtime installer for that exact provider family.

Current generic local-provider adapters include:

- `chatterbox-multilingual-v3`;
- `voxcpm2`.

Both are fail-closed, local-assets-only adapters. Neither performs provider/model fallback, implicit model download, or artistic voice selection.

A consumer may use these adapters only with its own product-owned human/artistic acceptance package. Provider promotion in the generic engine is not global artistic approval of any voice or work.
