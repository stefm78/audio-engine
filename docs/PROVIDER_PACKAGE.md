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
